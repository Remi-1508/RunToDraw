# RunToDraw

Génère un itinéraire de course à pied (ou marche, vélo...) qui dessine une forme ou un texte sur une vraie carte, en s'appuyant sur le réseau routier réel autour d'un point choisi.

1. Choisir un point de départ
2. Choisir une distance cible
3. Choisir une forme (cœur, carré, rond, étoile, infini) ou un texte court
4. Le réseau routier local est extrait depuis OpenStreetMap (Overpass)
5. Le moteur cherche plusieurs itinéraires suivant les vraies routes et se rapprochant du dessin demandé
6. Choisir le meilleur trajet parmi les propositions, l'exporter en GPX / KML / lien Google Maps

## Stack

- **Frontend** : React + Vite, Leaflet / React-Leaflet pour la carte
- **Backend** : FastAPI (Python)
- **Données routières** : OpenStreetMap via l'API Overpass
- Moteur de génération d'itinéraires écrit en interne (géométrie, graphe, recherche, scoring)

## Architecture backend

Le moteur vit dans le package `backend/runtodraw/`, découpé par responsabilité et testé unitairement (63 tests, `backend/tests/`) :

| Module | Rôle |
|---|---|
| `geometry.py` | Fonctions géométriques pures (conversions GPS ↔ local, opérations sur les polylignes) |
| `graph.py` | `RoadGraph` : graphe routier + recherche du nœud le plus proche via un KD-tree, Dijkstra |
| `shapes.py` | Formes de base et glyphes des lettres |
| `scoring.py` | Notation d'un itinéraire candidat par rapport à la forme demandée |
| `search.py` | Génération et évaluation des candidats (projection/translation × distance/compromis) |
| `osm.py` | Extraction du graphe depuis Overpass, avec cache en mémoire |
| `planner.py` | Point d'entrée : assemble tout ce qui précède pour répondre à une requête |
| `parallel.py` | Pool de threads pour évaluer les candidats en parallèle |
| `jobs.py` | File de tâches en arrière-plan avec suivi de progression par polling |

`app.py` ne contient que les routes FastAPI ; toute la logique métier est dans `runtodraw`.

## Ce qui a été optimisé

Le premier jet du moteur (un seul fichier de ~1200 lignes) prenait jusqu'à 15 minutes sur les cas les plus lourds. Les changements suivants, chacun mesuré et vérifié à résultats identiques, ont ramené ça à quelques secondes/dizaines de secondes dans la plupart des cas :

- **Recherche du nœud le plus proche par KD-tree** (SciPy) au lieu d'une distance à tous les nœuds : ~31x plus rapide sur un graphe de test, résultats identiques.
- **Cache en mémoire des extractions Overpass** (TTL 6h, coordonnées arrondies à ~110m/250m) : évite de refaire l'étape la plus lente et la plus instable pour des requêtes proches.
- **Évaluation des candidats en parallèle** avec un petit pool de threads (~1.45x sur une forme, ~1.9x sur un texte). Un `ProcessPoolExecutor` a aussi été testé mais s'est révélé plus lent une fois le KD-tree en place : le travail par candidat est trop court pour amortir le coût de sérialisation entre processus.
- **Progression réelle** (candidats effectivement évalués / total) au lieu d'une barre de chargement simulée par un minuteur.
- **Tâches en arrière-plan** : `POST /api/routes/plan/jobs` renvoie tout de suite un `job_id`, et `GET /api/routes/plan/jobs/{id}` est interrogé par polling — plus de requête HTTP bloquante de plusieurs minutes qui risquerait un timeout derrière un proxy en déploiement.
- Le temps de calcul réel est renvoyé par l'API et affiché dans les résultats.

Reste identifié mais pas encore fait : simplifier le graphe en amont (fusionner les nœuds qui ne sont pas des intersections) et garder le graphe en mémoire côté serveur au lieu de le faire aller-retour vers le frontend en JSON.

## Installation

Prérequis : Python 3.10+, Node.js 18+, npm, Git.

```bash
git clone https://github.com/Remi-1508/RunToDraw.git
cd RunToDraw
```

### Backend

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate — macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8000
```

Pour lancer les tests (63 tests unitaires + intégration) :

```bash
pip install -r requirements-dev.txt
python -m pytest
```

### Frontend

```bash
cd runtodraw_frontend
npm install
npm run dev
```

L'URL du backend est lue depuis `runtodraw_frontend/.env` (`VITE_ROUTE_API_URL`, `http://localhost:8000` par défaut).

## Conseils d'utilisation

- **Distance** : 10 km ou plus (idéalement 15) donne de meilleurs résultats visuels — en dessous, le réseau routier disponible est souvent trop limité pour bien approcher la forme.
- **Mode texte** : 1 à 3 lettres maximum (ex. `P2I`, `RUN`, `GO`). Les mots plus longs sont plus difficiles à approcher précisément dans la distance demandée.
- **Affichage du graphe complet** : facultatif, à activer seulement pour explorer la zone — le laisser masqué garde l'interface plus fluide sur les gros graphes.

## Déploiement

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour déployer le backend (Docker / Render) et le frontend (Vercel / Netlify).
