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
- solutions les plus proches de la distance demandée
- meilleurs compromis globaux

## Export

Les itinéraires peuvent être exportés en :

- GPX
- KML
- Lien Google Maps

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

python -m uvicorn app:app --reload --port 8000

## Terminal/Onglet frontend

cd RunToDraw/runtodraw_frontend

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

La génération peut être longue selon :

- la zone choisie
- la densité des routes
- le texte demandé
- la distance choisie

Sur les cas les plus lourds, le temps de calcul peut atteindre :

jusqu’à environ **15 minutes**

Il est donc conseillé de :

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

# Conseils d’affichage

L’affichage complet du graphe routier reste facultatif.

Pour garder une interface fluide :

- laisser le graphe masqué si non nécessaire
- l’activer uniquement pour explorer la zone
