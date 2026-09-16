import { API_BASE } from "../config";

/*
============================================================
EN:
fetchGraphForRun asks the backend to extract the road graph
around the point selected by the user.

The frontend sends:
- latitude
- longitude
- requested running distance

The backend then:
- computes the extraction radius
- queries OpenStreetMap / Overpass
- builds the graph
- returns it in a reusable format

This function does not build the graph itself.
It only requests it from the backend.

FR:
fetchGraphForRun demande au backend d’extraire le graphe routier
autour du point choisi par l’utilisateur.

Le frontend envoie :
- la latitude
- la longitude
- la distance de course demandée

Le backend :
- calcule le rayon d’extraction
- interroge OpenStreetMap / Overpass
- construit le graphe
- le renvoie dans un format réutilisable

Cette fonction ne construit pas elle-même le graphe.
Elle se contente de le demander au backend.
============================================================
*/
export async function fetchGraphForRun({ lat, lon, distanceKm }) {
  const res = await fetch(`${API_BASE}/api/graph/fetch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },

    /*
    EN:
    The request body contains only the information needed
    to build the graph around the chosen area.

    FR:
    Le corps de la requête contient uniquement les informations nécessaires
    pour construire le graphe autour de la zone choisie.
    */
    body: JSON.stringify({
      lat,
      lon,
      distance_km: distanceKm,
    }),
  });

  /*
  EN:
  If the backend returns an error, we also read the text response
  to keep a more useful error message.

  FR:
  Si le backend renvoie une erreur, on lit aussi le texte renvoyé
  pour garder un message d’erreur plus utile.
  */
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Graph fetch failed: ${res.status} ${txt}`);
  }

  /*
  EN:
  The backend returns the graph payload in JSON format.

  FR:
  Le backend renvoie le graphe au format JSON.
  */
  const graphPayload = await res.json();

  /*
  EN:
  We return:
  - the graph itself
  - the center used
  - the estimated extraction radius

  This is useful for the map display and for the next route-planning step.

  FR:
  On renvoie :
  - le graphe lui-même
  - le centre utilisé
  - le rayon estimé d’extraction

  C’est utile pour l’affichage sur la carte et pour l’étape suivante
  de génération d’itinéraire.
  */
  return {
    center: graphPayload.meta?.center ?? [lat, lon],
    radiusKm: graphPayload.meta?.radius_km ?? distanceKm / 2,
    graphPayload,
  };
}