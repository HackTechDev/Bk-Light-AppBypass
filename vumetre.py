import asyncio
import threading
import numpy as np
import pyaudio
from pydub import AudioSegment
from io import BytesIO
from PIL import Image
from bk_light.display_session import BleDisplaySession

MAC_ADDRESS = "6F:E3:D9:1A:19:CA"
W, H = 32, 32

# ─────────────────────────────────────────────
# CONFIG VU-MÈTRE
# ─────────────────────────────────────────────

NB_BARS    = 16    # nombre de barres verticales
BAR_W      = W // NB_BARS   # largeur d'une barre en pixels (= 2)
SAMPLE_RATE = 44100
CHUNK_SIZE  = 1024  # samples par bloc audio (~23ms à 44100Hz)

# Palette de couleurs : vert → jaune → rouge (du bas vers le haut)
def bar_color(row, total_rows):
    """row=0 = bas, row=total_rows-1 = haut"""
    t = row / max(1, total_rows - 1)
    if t < 0.6:
        return (0, int(255 * (1 - t * 0.5)), 0)       # vert
    elif t < 0.8:
        f = (t - 0.6) / 0.2
        return (int(255 * f), int(180 * (1 - f * 0.5)), 0)  # jaune
    else:
        f = (t - 0.8) / 0.2
        return (255, int(60 * (1 - f)), 0)              # rouge


# ─────────────────────────────────────────────
# ÉTAT PARTAGÉ AUDIO ↔ RENDU
# ─────────────────────────────────────────────

class AudioState:
    def __init__(self):
        self.levels   = np.zeros(NB_BARS)   # niveau 0.0–1.0 par bande
        self.peak     = np.zeros(NB_BARS)   # pic par bande (tombée lente)
        self.lock     = threading.Lock()
        self.finished = False
        self.PEAK_DECAY = 0.92              # décroissance des pics


# ─────────────────────────────────────────────
# ANALYSE FFT → BANDES DE FRÉQUENCES
# ─────────────────────────────────────────────

def compute_bands(pcm_chunk: np.ndarray, sample_rate: int, nb_bands: int) -> np.ndarray:
    """
    Découpe le spectre en nb_bands bandes logarithmiques et retourne
    l'énergie normalisée (0.0–1.0) de chaque bande.
    """
    n = len(pcm_chunk)
    if n == 0:
        return np.zeros(nb_bands)

    # FFT → magnitude
    window = np.hanning(n)
    fft = np.abs(np.fft.rfft(pcm_chunk * window))
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

    # Bandes logarithmiques entre 20 Hz et 20 kHz
    f_min, f_max = 20.0, 20000.0
    bands = np.zeros(nb_bands)
    for i in range(nb_bands):
        f_lo = f_min * (f_max / f_min) ** (i / nb_bands)
        f_hi = f_min * (f_max / f_min) ** ((i + 1) / nb_bands)
        mask = (freqs >= f_lo) & (freqs < f_hi)
        if mask.any():
            bands[i] = np.mean(fft[mask])

    # Normalisation log
    bands = np.log1p(bands)
    max_v = bands.max()
    if max_v > 0:
        bands /= max_v

    return bands


# ─────────────────────────────────────────────
# THREAD AUDIO : lecture + analyse en temps réel
# ─────────────────────────────────────────────

def audio_thread(mp3_path: str, audio_state: AudioState):
    """
    Charge le MP3, le joue via PyAudio chunk par chunk,
    et met à jour audio_state.levels en temps réel.
    """
    print(f"Chargement de {mp3_path}...")
    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE).set_sample_width(2)
    raw_data = np.frombuffer(audio.raw_data, dtype=np.int16).astype(np.float32) / 32768.0

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=SAMPLE_RATE,
        output=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    print("Lecture audio démarrée.")
    pos = 0
    while pos < len(raw_data):
        chunk = raw_data[pos:pos + CHUNK_SIZE]
        if len(chunk) < CHUNK_SIZE:
            chunk = np.pad(chunk, (0, CHUNK_SIZE - len(chunk)))

        # Lecture audio
        stream.write(chunk.astype(np.float32).tobytes())

        # Analyse spectrale
        bands = compute_bands(chunk, SAMPLE_RATE, NB_BARS)

        with audio_state.lock:
            audio_state.levels = bands
            # Pics avec décroissance lente
            audio_state.peak = np.maximum(
                audio_state.peak * audio_state.PEAK_DECAY,
                bands
            )

        pos += CHUNK_SIZE

    stream.stop_stream()
    stream.close()
    pa.terminate()

    with audio_state.lock:
        audio_state.finished = True
    print("\nLecture terminée.")


# ─────────────────────────────────────────────
# RENDU VU-MÈTRE → PNG
# ─────────────────────────────────────────────

def render_vumeter(levels: np.ndarray, peaks: np.ndarray) -> bytes:
    pixels = [(0, 0, 0)] * (W * H)

    for bar in range(NB_BARS):
        level = levels[bar]
        peak  = peaks[bar]
        height = int(level * H)          # hauteur active en pixels
        peak_y = H - 1 - int(peak * (H - 1))  # ligne du pic

        x_start = bar * BAR_W
        x_end   = x_start + BAR_W - 1   # 1px de séparation entre barres

        for row in range(H):
            y = H - 1 - row  # row=0 = bas du panneau
            filled = row < height

            for x in range(x_start, x_end):
                if filled:
                    color = bar_color(row, H)
                    # Légère atténuation des bords de barre
                    if x == x_start or x == x_end - 1:
                        color = tuple(c // 2 for c in color)
                    pixels[y * W + x] = color
                elif row == H - 1 - peak_y:
                    # Point de pic (blanc brillant)
                    pixels[y * W + x] = (200, 200, 200)

    img = Image.new("RGB", (W, H))
    img.putdata(pixels)
    out = BytesIO()
    img.save(out, format="PNG", optimize=False)
    return out.getvalue()


# ─────────────────────────────────────────────
# BOUCLE D'AFFICHAGE LED
# ─────────────────────────────────────────────

async def display_loop(audio_state: AudioState, fps: float = 20.0):
    delay = 1.0 / fps

    async with BleDisplaySession(MAC_ADDRESS) as session:
        print("Panneau LED connecté.")
        while True:
            with audio_state.lock:
                levels   = audio_state.levels.copy()
                peaks    = audio_state.peak.copy()
                finished = audio_state.finished

            png = render_vumeter(levels, peaks)
            await session.send_png(png, delay=0.0)

            if finished and levels.max() < 0.01:
                break

            await asyncio.sleep(delay)

    # Éteindre le panneau à la fin
    blank = render_vumeter(np.zeros(NB_BARS), np.zeros(NB_BARS))
    async with BleDisplaySession(MAC_ADDRESS) as session:
        await session.send_png(blank)


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────

async def main(mp3_path: str):
    audio_state = AudioState()

    # Lance le thread audio (lecture + analyse)
    t = threading.Thread(
        target=audio_thread,
        args=(mp3_path, audio_state),
        daemon=True,
    )
    t.start()

    # Lance la boucle d'affichage LED en parallèle
    await display_loop(audio_state, fps=20.0)

    t.join()
    print("Programme terminé.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage : python vumeter.py mon_fichier.mp3")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
