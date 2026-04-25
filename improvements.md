# Idées de démos et jeux pour les 4 panneaux LED (128×32 px)

## Jeux interactifs

### Breakout / Casse-briques
Raquette en bas, balle qui rebondit, rangées de briques colorées à détruire.
Briques de 4×3 px, plusieurs couleurs par rangée, accélération progressive.
Contrôle : gauche/droite. Vies affichées en pixel-art.

### Space Invaders
Grille d'envahisseurs (6×3 px chacun) qui descend lentement. Le joueur tire vers le haut.
Format idéal pour l'écran large : envahisseurs sur toute la largeur, joueur centré en bas.
Contrôle : gauche/droite + espace pour tirer.

### Flappy Bird
Personnage 4×4 px qui tombe par gravité. Tuyaux verticaux (gaps aléatoires) qui défilent de droite à gauche.
Hauteur de 32 px rend le jeu tendu. Contrôle : espace/haut pour battre des ailes.

### Voiture / Course
Vue de dessus. Route qui défile vers le bas, voitures adverses à éviter.
La largeur de 128 px donne de la place pour 3 voies.
Contrôle : gauche/droite.

### Tir à la cible
Cibles apparaissent aléatoirement sur les panneaux, le joueur déplace un viseur et tire.
Système de score avec bonus pour les tirs rapides. Contrôle : 4 flèches + entrée.

### Simon Says (mémoire)
Séquences de flashs colorés par panneau (chaque panneau = une couleur).
Le joueur reproduit la séquence en appuyant sur 1/2/3/4. Difficulté croissante.

### Ping-Pong 2 joueurs
Extension de pong4panels.py : 2 joueurs humains, joueur gauche (Z/S) vs joueur droit (↑/↓).

---

## Effets visuels et animations

### Plasma / Ondes de couleur
Combinaison de fonctions sinus sur X et Y pour créer un effet plasma psychédélique.
Couleurs HSV cycliques, très fluide à 20 FPS. Aucune interaction requise.

### Feu (Fire simulation)
Automate cellulaire classique de feu : base en rouge/orange chaud, flammes qui montent.
Chaque colonne propage de la chaleur vers le haut avec un léger bruit aléatoire.

### Pluie de Matrix
Colonnes de caractères ASCII qui tombent en vert, comme dans le film.
Utilise la police aldopc ou une police 3×5 custom. Traînées qui s'estompent.

### Champ d'étoiles (warp speed)
Points blancs (étoiles) qui convergent depuis le centre et accélèrent vers les bords.
Effet de vitesse lumière. Étoiles générées aléatoirement avec vitesse proportionnelle à la distance.

### Métaballs
Cercles flottants qui fusionnent quand ils se touchent. Rendu par seuillage de la somme des champs.
2 ou 3 billes colorées, trajectoires sinusoïdales.

### Automate de Langton (Fourmi de Langton)
Fourmi qui tourne à gauche sur cellule blanche, à droite sur cellule noire.
Produit des structures complexes. Réinitialisation automatique après stagnation.

### Bruit de Perlin / Terrain généré
Terrain montagneux défilant de droite à gauche, généré par bruit de Perlin 1D.
Couleurs par altitude : eau, herbe, roche, neige.

### Horloge pixel-art
Affichage de l'heure en grands chiffres sur les 4 panneaux (HH:MM ou HH:MM:SS).
Couleurs qui changent selon l'heure (matin = bleu, jour = blanc, soir = orange...).
Nécessite `import datetime`.

### Trieur de données (Visualisation d'algorithmes)
Barres verticales représentant des valeurs. Animation du tri (bulles, fusion, rapide...).
Chaque comparaison/échange visible en temps réel. Barres colorées par état.

### Oscilloscope / Formes de Lissajous
Courbes de Lissajous animées : sin(at + δ) vs sin(bt). Ratios a:b variables dans le temps.
Trace persistante qui s'efface progressivement.

### Vagues interférentes
Deux sources d'ondes circulaires, affichage de l'interférence constructive/destructive.
Palette de couleurs chaudes/froides selon l'amplitude. Sources qui se déplacent lentement.

### Fractale de Mandelbrot
Zoom progressif sur un point de l'ensemble de Mandelbrot. Rendu incrémental à 128×32.
Palette de couleurs cyclique selon le nombre d'itérations.

---

## Données en temps réel

### Météo en direct
Fetch d'une API météo (température, icône pluie/soleil/nuage en pixel-art, vent).
Mise à jour toutes les 10 minutes. Affichage en défilement ou statique.

### Ticker boursier
Prix d'actions ou de crypto en défilement continu. Flèche verte/rouge selon variation.
Source : API publique (Yahoo Finance, CoinGecko...).

### Monitoring système
CPU, RAM, température du Raspberry Pi en bargraphes animés sur chaque panneau.
Mise à jour toutes les secondes via `psutil`.

### Compteur de dépôts GitHub
Affiche les commits récents d'un dépôt sous forme de texte défilant + sparkline d'activité.

---

## Interactif / Créatif

### Éditeur de pixel-art
Mode dessin : curseur déplaçable aux 4 flèches, touche entrée pour poser/effacer un pixel.
Palette de couleurs sélectionnable. Sauvegarde en PNG.

### Affichage d'images / Diaporama
Charge des PNG depuis un dossier `assets/slides/`, les affiche 5 secondes chacun.
Redimensionnement automatique à 128×32. Transition par fondu (fade-in/out).

### GIF reader
Lecture de GIFs animés redimensionnés à 128×32, frame par frame, avec la bonne durée par frame.

### Réaction au son (micro)
Via `pyaudio` : analyse de volume ou FFT du micro. Bargraphes VU-mètre en temps réel,
ou spectre de fréquences sur toute la largeur (128 colonnes = 128 bandes de fréquences).

### Jeu coopératif réseau (socket)
Deux machines se connectent via socket TCP. Chacune contrôle une moitié de l'écran.
Exemple : tennis de table multi-joueurs à distance.
