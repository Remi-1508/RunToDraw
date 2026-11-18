// API_BASE définit l’URL du backend utilisée par le frontend.
//
// Si une variable d’environnement est disponible, on l’utilise.
// Sinon, on prend par défaut le backend local sur le port 8000.
//
// Cela rend le code plus facile à utiliser :
// - en développement local
// - puis plus tard dans un autre environnement de déploiement
const API_BASE = import.meta.env.VITE_ROUTE_API_URL || "http://localhost:8000";

// fetchGraphForRun demande au backend d’extraire le graphe routier
// autour du point choisi par l’utilisateur.
//
// Le frontend envoie :
// - la latitude
// - la longitude
// - la distance de course demandée
//
// Le backend :
// - calcule le rayon d’extraction
// - interroge OpenStreetMap / Overpass
// - construit le graphe
// - le renvoie dans un format réutilisable
//
// Cette fonction ne construit pas elle-même le graphe.
// Elle se contente de le demander au backend.
export async function fetchGraphForRun({ lat, lon, distanceKm, drawing }) {
  const res = await fetch(`${API_BASE}/api/graph/fetch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },

    // Le corps de la requête contient uniquement les informations nécessaires
    // pour construire le graphe autour de la zone choisie.
    body: JSON.stringify({
      lat,
      lon,
      distance_km: distanceKm,
      // Le backend calcule le rayon utile à partir de la forme demandée.
      drawing,
    }),
  });

  // Si le backend renvoie une erreur, on lit aussi le texte renvoyé
  // pour garder un message d’erreur plus utile.
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Extraction du graphe impossible"));
  }

  // Le backend renvoie le graphe au format JSON.
  const { meta } = await res.json();

  /*
  Le graphe reste sur le serveur : on ne reçoit qu'un résumé
  (centre, rayon réellement utilisé, nombre de sommets et d'arêtes).
  */
  return {
    center: meta?.center ?? [lat, lon],
    radiusKm: meta?.radius_km ?? distanceKm / 2,
    distanceKm,
    nodeCount: meta?.node_count ?? 0,
    edgeCount: meta?.edge_count ?? 0,
  };
}

/*
Lit le message d'erreur renvoyé par FastAPI ({"detail": "..."}) pour l'afficher à l'utilisateur.
*/
export async function readErrorMessage(res, fallback) {
  const text = await res.text();
  try {
    const detail = JSON.parse(text)?.detail;
    if (typeof detail === "string") return detail;
  } catch {
    // réponse non JSON : on garde le texte brut
  }
  return `${fallback} (HTTP ${res.status})${text ? ` : ${text.slice(0, 200)}` : ""}`;
}
