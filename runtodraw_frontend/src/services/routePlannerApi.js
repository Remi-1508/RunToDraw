import { readErrorMessage } from "./osmGraph";

// API_BASE définit l’URL du backend utilisée pour appeler
// le moteur de génération d’itinéraires.
//
// Si une variable d’environnement existe, on l’utilise.
// Sinon, le frontend utilise le backend local.
//
// Cela permet de passer facilement entre :
// - le développement local
// - un backend déployé plus tard
const API_BASE = import.meta.env.VITE_ROUTE_API_URL || "http://localhost:8000";

// planRoutes envoie les choix utilisateur
// au backend pour calculer des propositions d’itinéraires.
//
// Le frontend envoie :
// - le point choisi (le graphe lui-même reste en cache sur le serveur)
// - la distance demandée
// - les paramètres du dessin (forme ou texte)
//
// Le backend utilise ensuite le moteur Python pour générer
// plusieurs itinéraires candidats.
//
// Cette fonction sert uniquement à communiquer avec l’API.
export async function planRoutes({ lat, lon, distanceKm, drawing }) {
  const res = await fetch(`${API_BASE}/api/routes/plan`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    // Le payload contient tout ce dont le moteur a besoin.
    //
    // lat / lon :
    // point choisi, qui permet au serveur de retrouver le graphe en cache
    //
    // distance_km :
    // distance cible
    //
    // drawing :
    // demande utilisateur (mode forme ou mode texte)
    body: JSON.stringify({
      // Le serveur retrouve le graphe dans son cache à partir du point choisi :
      // plus besoin de renvoyer le graphe complet.
      lat,
      lon,
      distance_km: distanceKm,
      drawing,
    }),
  });

  // Si le backend échoue, on essaie de lire le texte renvoyé
  // pour afficher un message d’erreur plus utile.
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Calcul des itinéraires impossible"));
  }

  // En cas de succès, le backend renvoie :
  // - un texte résumé
  // - plusieurs propositions d’itinéraires
  // - des métriques pour chaque trajet
  return res.json();
}