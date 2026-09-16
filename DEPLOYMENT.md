# Déploiement

RunToDraw se déploie en deux parties indépendantes : le backend FastAPI (une API) et le frontend React (des fichiers statiques après build). Rien ici n'est fait à ta place : chaque étape se fait depuis ton propre compte sur la plateforme choisie.

## Backend (FastAPI)

Le backend est fourni avec un `Dockerfile` (image Python 3.12 slim + uvicorn) et un `render.yaml` prêt pour [Render](https://render.com), qui a un plan gratuit adapté à une démo.

### Avec Render

1. Sur Render : **New > Blueprint**, connecte le dépôt GitHub `RunToDraw`. Render lit `render.yaml` et crée le service `runtodraw-backend` automatiquement.
2. Une fois déployé, note l'URL donnée (ex. `https://runtodraw-backend.onrender.com`).
3. Dans les variables d'environnement du service, définis `ALLOWED_ORIGINS` avec l'URL du frontend une fois celui-ci déployé (ex. `https://runtodraw.vercel.app`), pour que l'API n'accepte que ce domaine plutôt que `*`.

### Avec Docker, n'importe où ailleurs

```bash
cd backend
docker build -t runtodraw-backend .
docker run -p 8000:8000 -e ALLOWED_ORIGINS=https://ton-frontend.example.com runtodraw-backend
```

Le conteneur écoute sur `$PORT` s'il est défini (Render, Railway, Fly.io le font automatiquement), sinon sur `8000`.

## Frontend (React + Vite)

Le frontend est un site statique après `npm run build` (dossier `runtodraw_frontend/dist`). Le dépôt contient une config prête pour Vercel (`vercel.json`) et pour Netlify (`netlify.toml`), toutes deux pensées pour un dépôt où le frontend est dans un sous-dossier.

### Avec Vercel

1. **Add New > Project**, importe le dépôt GitHub. `vercel.json` à la racine indique déjà où builder (pas besoin de configurer le "Root Directory" dans l'interface).
2. Dans les variables d'environnement du projet, ajoute `VITE_ROUTE_API_URL` avec l'URL du backend déployé (ex. `https://runtodraw-backend.onrender.com`).
3. Redéployer après avoir ajouté la variable, si le premier build a eu lieu avant.

### Avec Netlify

1. **Add new site > Import an existing project**, choisis le dépôt. `netlify.toml` fixe déjà le dossier de base (`runtodraw_frontend`), la commande de build et le dossier publié (`dist`).
2. Dans **Site configuration > Environment variables**, ajoute `VITE_ROUTE_API_URL` avec l'URL du backend déployé.

## Ordre conseillé

1. Déployer le backend en premier (Render ou Docker) pour obtenir son URL.
2. Déployer le frontend avec `VITE_ROUTE_API_URL` pointant vers cette URL.
3. Revenir sur le backend pour restreindre `ALLOWED_ORIGINS` à l'URL réelle du frontend, plutôt que de garder `*`.

## Limites connues à garder en tête pour une démo publique

- Le cache Overpass et la file de tâches (`jobs.py`) sont en mémoire, par processus : ils sont perdus à chaque redémarrage/redeploy, et ne fonctionnent pas tels quels si le service tourne sur plusieurs instances derrière un load balancer.
- Les plans gratuits (Render notamment) mettent le service en veille après une période d'inactivité : la première requête après une veille peut prendre plusieurs dizaines de secondes le temps que le conteneur redémarre.
