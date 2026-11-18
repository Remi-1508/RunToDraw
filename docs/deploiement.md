# Déploiement de RunToDraw

Le frontend (React) est hébergé sur **Vercel**, le backend (FastAPI) sur **Render**. Les deux se déploient
automatiquement à chaque push sur la branche `main`.

```
Navigateur ──▶ Vercel (site statique) ──▶ Render (API FastAPI) ──▶ OpenStreetMap (Overpass)
```

## Avant de commencer

- Le code à déployer doit être sur la branche `main` de GitHub (fusionner la branche de travail).
- Comptes gratuits : [Render](https://render.com) et [Vercel](https://vercel.com), tous deux reliés à GitHub.
- Facultatif : une clé [Geoapify](https://myprojects.geoapify.com) pour la recherche d'adresses hors de France.

## 1. Backend sur Render

1. Render → **New +** → **Blueprint** → choisir le dépôt. Render lit `render.yaml` et crée le service
   `runtodraw-api` (Docker, offre gratuite).
2. Attendre la fin du premier déploiement (quelques minutes), puis noter l'adresse du service,
   par exemple `https://runtodraw-api.onrender.com`.
3. Vérifier `https://runtodraw-api.onrender.com/health` : la réponse doit contenir `"ok": true`.

La variable `RUNTODRAW_ALLOWED_ORIGINS` est demandée mais reste vide pour l'instant : on la renseigne à
l'étape 3, quand l'adresse du site Vercel existe.

## 2. Frontend sur Vercel

1. Vercel → **Add New… → Project** → importer le dépôt.
2. **Root Directory** : `frontend` (le reste est détecté : Vite, `npm run build`, dossier `dist`).
3. **Environment Variables** :

   | Nom | Valeur |
   |---|---|
   | `VITE_ROUTE_API_URL` | adresse du backend Render, **sans** `/` final |
   | `VITE_GEOAPIFY_KEY` | clé Geoapify (facultatif) |

4. **Deploy**, puis noter l'adresse du site, par exemple `https://runtodraw.vercel.app`.

Les variables `VITE_*` sont intégrées au moment de la construction : après toute modification, il faut
redéployer le frontend.

## 3. Autoriser le site auprès de l'API (CORS)

Dans Render → service `runtodraw-api` → **Environment** :

- `RUNTODRAW_ALLOWED_ORIGINS` = `https://runtodraw.vercel.app` (adresse exacte, sans `/` final ; plusieurs
  adresses possibles, séparées par des virgules).
- Facultatif, pour que les déploiements de prévisualisation Vercel fonctionnent aussi :
  `RUNTODRAW_ALLOWED_ORIGIN_REGEX` = `https://runtodraw-.*\.vercel\.app`.

Enregistrer : Render redéploie le service.

## 4. Protéger la clé Geoapify

Sur myprojects.geoapify.com, limiter la clé à ses **origines autorisées** : l'adresse du site Vercel et
`http://localhost:5173`. La clé est visible dans le code du navigateur ; cette restriction empêche qu'on
l'utilise ailleurs.

## 5. Vérification de bout en bout

1. Ouvrir le site : la page se charge, sans erreur rouge dans la console du navigateur (F12).
2. Chercher une adresse et la choisir.
3. Générer un cœur de 5 km : des propositions apparaissent sur la carte.
4. Exporter en GPX et ouvrir le fichier dans une application de sport.

## Limites de l'offre gratuite

- **Mise en veille de Render** après 15 minutes sans requête : le premier appel peut prendre 30 à 60 secondes.
  Le site interroge `/health` dès son chargement, ce qui réveille le serveur pendant que l'utilisateur choisit
  son point de départ.
- **Mémoire de 512 Mo** : d'où la distance maximale de 25 km et les 2 graphes gardés en cache (réglables dans
  `render.yaml`).
- **Overpass** est un service public partagé : la première génération dans une zone peut durer une minute ou
  plus. Les suivantes, dans la même zone, sont presque immédiates tant que le graphe est en cache (il est perdu à
  chaque redémarrage du serveur).

## Tester l'image Docker en local

```bash
docker build -t runtodraw-api backend
docker run --rm -p 8000:8000 -e RUNTODRAW_TRUSTED_PROXY_HOPS=0 runtodraw-api
# puis ouvrir http://localhost:8000/health
```

## En cas de problème

| Symptôme | Cause probable |
|---|---|
| Erreur « CORS » dans la console du navigateur | `RUNTODRAW_ALLOWED_ORIGINS` ne correspond pas exactement à l'adresse du site (`https`, pas de `/` final) |
| « Impossible de joindre le serveur » | `VITE_ROUTE_API_URL` absente ou erronée : corriger, puis redéployer le frontend |
| « Trop de requêtes » | Limite de débit atteinte (30 requêtes par minute et par adresse IP) : patienter une minute |
| « Overpass indisponible » | Services OpenStreetMap saturés : réessayer un peu plus tard |
| Le service redémarre pendant un calcul | Mémoire dépassée : réduire `RUNTODRAW_MAX_DISTANCE_KM` ou `RUNTODRAW_GRAPH_CACHE_SIZE` |
