# RunToDraw

## Présentation du projet

RunToDraw est une application web permettant de générer des itinéraires de course à pied, de marche, de vélo ... ayant la forme d’un dessin.

Le principe est simple :

1. Choisir une zone de départ sur la carte  
2. Sélectionner une distance cible  
3. Choisir une forme ou écrire un texte  
4. L’application extrait le réseau routier local depuis  
5. Un moteur Python recherche plusieurs itinéraires correspondant au dessin demandé  
6. Les meilleurs trajets peuvent ensuite être exportés vers des applications GPS

Le projet combine :

- **React + Vite** pour le frontend
- **Leaflet / React-Leaflet** pour l’affichage cartographique
- **FastAPI (Python)** pour le backend
- **OpenStreetMap / Overpass API** pour les données routières
- Des algorithmes personnalisés de graphes et de génération d’itinéraires

---

# Fonctionnalités principales

## Choix de la zone

L’utilisateur peut :

- utiliser sa position actuelle
- rechercher une adresse
- choisir le point de départ du parcours

## Choix de la distance

L’utilisateur sélectionne la distance souhaitée en kilomètres.

## Mode forme

Exemples disponibles :

- Carré
- Rond
- Cœur
- Étoile
- Infini

## Mode texte

L’utilisateur peut entrer un texte court (exemple : `P2I`).

Le moteur essaie alors de générer des trajets représentant les lettres.

## Propositions d’itinéraires

Plusieurs variantes sont calculées :

- méthodes par projection
- méthodes par translation
- « Départ inclus » : un itinéraire qui part et revient exactement au point choisi
  (le départ peut être n'importe quel point du dessin)
- pour chaque méthode, la solution la plus proche de la distance demandée et le meilleur compromis
- les propositions identiques sont fusionnées

En mode texte, trois versions sont proposées :

- **mot entier** : un seul itinéraire de la distance demandée qui écrit tout le mot
- **lettres séparées** : un itinéraire par lettre, chacun de la distance demandée
- **lettres reliées** : ces mêmes lettres enchaînées en un seul itinéraire, reliées par le plus court chemin

## Modifier le tracé sur la carte

Le bouton **Modifier le tracé** (en bas de la carte) permet de retoucher l'itinéraire choisi, comme sur Strava,
en formes comme en texte. Les points du tracé apparaissent sous forme de ronds, notamment au bout des
aller-retours :

- **déplacer** un point : on le glisse, le tracé est recalculé sur les vraies routes ;
- **ajouter** un point : on appuie sur le tracé et on tire ;
- **supprimer** un point : clic sur le point puis `Suppr` (ou le bouton de la barre d'outils) ;
- **annuler / rétablir** : `Ctrl+Z` / `Ctrl+Y`, ou « Tracé d'origine » pour tout reprendre.

Seuls les deux tronçons voisins du point touché sont recalculés (`POST /api/routes/edit`), donc la réponse est
quasi instantanée. L'export GPX / KML porte sur le tracé modifié.

## Export

Les itinéraires peuvent être exportés en :

- GPX (un fichier par lettre pour les lettres séparées)
- KML (Google My Maps)

---

# Installation

## Prérequis

Avant de lancer le projet, vérifier que les outils suivants sont installés :

- Python 3.10 minimum
- Node.js 18 minimum
- npm (installé avec Node.js)
- Git

## Cloner le projet

git clone https://github.com/Remi-1508/RunToDraw.git

cd RunToDraw

### Ici, il faut ouvrir un terminal pour le backend, et un pour le frontend
### Je vous conseille d'ouvir deux onglets VSCode

## Terminal/Onglet backend

cd RunToDraw/backend

python -m pip install -r requirements.txt

python -m uvicorn runtodraw.api:app --reload --port 8000

Pour mettre le projet en ligne (Vercel + Render), voir [docs/deploiement.md](docs/deploiement.md).

### Configuration et protections de l'API

Le backend lit ses réglages dans des variables d'environnement (liste commentée dans `backend/.env.example`).
En local, aucune n'est nécessaire. En production, il faut au minimum :

- `RUNTODRAW_ALLOWED_ORIGINS` : adresse du site qui appelle l'API (CORS), par exemple `https://runtodraw.vercel.app`.

Protections actives par défaut, volontairement permissives :

- distance limitée à 50 km (`RUNTODRAW_MAX_DISTANCE_KM`) ;
- 30 requêtes coûteuses par minute et par adresse IP, soit environ 15 générations (`RUNTODRAW_RATE_LIMIT_PER_MINUTE`) ;
- 240 modifications de tracé par minute et par adresse IP, car déplacer un point sur la carte est léger mais fréquent (`RUNTODRAW_EDIT_RATE_LIMIT_PER_MINUTE`) ;
- 2 calculs d'itinéraires simultanés, les suivants patientent puis reçoivent « serveur occupé » ;
- une seule requête Overpass par zone, même si plusieurs utilisateurs la demandent en même temps ;
- texte normalisé (majuscules, accents retirés), formes validées, erreurs lisibles et sans détail interne.

### Tests du moteur (facultatif)

python -m pip install -r requirements-dev.txt

python -m pytest tests

## Terminal/Onglet frontend

cd RunToDraw/frontend

npm install

npm run dev

---

#Utilisation

## Fonctionnement classique

1.Ouvrir l’application web
2.Choisir sa position
3.Sélectionner une distance
4.Choisir une forme ou un texte
5.Cliquer sur Générer les propositions d’itinéraires
6.Attendre le calcul
7.Choisir l’itinéraire préféré
8.Exporter vers le format GPS souhaité

## Conseils d’utilisation importants

# Distances recommandées

Pour obtenir de meilleurs résultats visuels, il est conseillé de choisir :

**10 km ou plus (environ 15 si possible)**

Les petites distances donnent souvent des formes moins satisfaisantes car le réseau routier disponible est trop limité.

# Temps de calcul

L’étape la plus longue est le téléchargement du réseau routier depuis OpenStreetMap (Overpass),
souvent une à deux minutes selon la zone, la distance et la disponibilité des serveurs.
Le calcul des itinéraires lui-même prend ensuite quelques secondes.

Le réseau téléchargé reste en mémoire côté serveur : une nouvelle génération au même endroit,
avec la même distance, ne le retélécharge pas.

Pendant le calcul, il est conseillé de :

- ne pas actualiser la page trop vite
- patienter pendant le traitement
- éviter de multiplier les clics pendant le calcul

# Conseils pour le mode texte

Les meilleurs résultats sont obtenus avec :

1 à 3 lettres **maximum**

Exemples :

- P2I
- RUN
- GO
- AI

Les mots trop longs sont plus difficiles à calculer et souvent moins précis.

Au-delà de 50 km, l’application demande confirmation avant de lancer le calcul :
le téléchargement du réseau routier devient long.
