# RunToDraw

RunToDraw est une application web qui permet de générer des parcours de course ou de marche dessinant des formes sur une carte.

L'idée du projet est d'utiliser le réseau de rues réel pour créer des tracés qui, une fois parcourus, dessinent une forme (mot, symbole, etc.).

## Fonctionnement actuel

Pour le moment l'application permet de :

- choisir une position de départ (adresse ou position actuelle)
- choisir une distance
- récupérer le réseau de rues de la zone correspondante à partir des données OpenStreetMap
- transformer ces données en graphe
- afficher ce graphe sur une carte
- exporter le graphe au format JSON

Cela constitue la base pour la suite du projet.

## Suite du projet

L'objectif est maintenant d'utiliser ce graphe pour identifier des formes dans le réseau de rues et générer un parcours correspondant.

Le MVP consistera à identifier une forme simple (comme un carré) dans le graphe.  
Ensuite l'objectif sera d'identifier des formes plus complexes pour pouvoir écrire des lettres ou des symboles.

## Technologies utilisées

- React
- Leaflet
- OpenStreetMap
- Overpass API

## Auteur

Projet réalisé dans le cadre du P2i à l'ENSC.

Rémi Monier
