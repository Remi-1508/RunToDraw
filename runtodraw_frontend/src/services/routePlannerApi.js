import { readErrorMessage } from "./osmGraph";

/*
============================================================
EN:
API_BASE defines the backend URL used to call the route planner.

If a custom environment variable exists, we use it.
Otherwise, the frontend uses the local backend.

This allows easy switching between:
- local development
- deployed backend later

FR:
API_BASE définit l’URL du backend utilisée pour appeler
le moteur de génération d’itinéraires.

Si une variable d’environnement existe, on l’utilise.
Sinon, le frontend utilise le backend local.

Cela permet de passer facilement entre :
- le développement local
- un backend déployé plus tard
============================================================
*/
const API_BASE = import.meta.env.VITE_ROUTE_API_URL || "http://localhost:8000";

/*
============================================================
EN:
planRoutes sends the user choices to the backend
so it can calculate route proposals.

The frontend sends:
- the selected point (the graph itself stays cached on the server)
- the requested distance
- the drawing settings (shape or text)

The backend then uses the Python planner to generate
several route candidates.

This function only communicates with the API.

FR:
planRoutes envoie les choix utilisateur
au backend pour calculer des propositions d’itinéraires.

Le frontend envoie :
- le point choisi (le graphe lui-même reste en cache sur le serveur)
- la distance demandée
- les paramètres du dessin (forme ou texte)

Le backend utilise ensuite le moteur Python pour générer
plusieurs itinéraires candidats.

Cette fonction sert uniquement à communiquer avec l’API.
============================================================
*/
export async function planRoutes({ lat, lon, distanceKm, drawing }) {
  const res = await fetch(`${API_BASE}/api/routes/plan`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    /*
    EN:
    The payload contains everything needed by the planner.

    lat / lon:
    selected point, used by the server to find the cached road graph

    distance_km:
    target running distance

    drawing:
    user request (shape mode or text mode)

    FR:
    Le payload contient tout ce dont le moteur a besoin.

    lat / lon :
    point choisi, qui permet au serveur de retrouver le graphe en cache

    distance_km :
    distance cible

    drawing :
    demande utilisateur (mode forme ou mode texte)
    */
    body: JSON.stringify({
      // Le serveur retrouve le graphe dans son cache à partir du point choisi :
      // plus besoin de renvoyer le graphe complet.
      lat,
      lon,
      distance_km: distanceKm,
      drawing,
    }),
  });

  /*
  EN:
  If the backend fails, we try to read the response text
  to display a more useful error message.

  FR:
  Si le backend échoue, on essaie de lire le texte renvoyé
  pour afficher un message d’erreur plus utile.
  */
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Calcul des itinéraires impossible"));
  }

  /*
  EN:
  On success, the backend returns:
  - a summary text
  - several route proposals
  - metrics for each route

  FR:
  En cas de succès, le backend renvoie :
  - un texte résumé
  - plusieurs propositions d’itinéraires
  - des métriques pour chaque trajet
  */
  return res.json();
}