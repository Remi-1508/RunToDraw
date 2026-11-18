// Appels vers le backend RunToDraw : limites du serveur, graphe routier et calcul des itinéraires.
import { FALLBACK_MAX_DISTANCE_KM } from "../config";
import { request } from "./client";

// Limites annoncées par le serveur (distance maximale). En cas d'échec, on garde une valeur prudente.
export async function fetchServerLimits({ signal } = {}) {
  try {
    const data = await request("/health", { signal });
    return { maxDistanceKm: data.max_distance_km ?? FALLBACK_MAX_DISTANCE_KM };
  } catch (error) {
    if (error.name === "AbortError") throw error;
    return { maxDistanceKm: FALLBACK_MAX_DISTANCE_KM };
  }
}

// Demande au serveur de préparer (et garder en cache) le réseau routier autour du point choisi.
// Le graphe lui-même reste sur le serveur : on ne reçoit qu'un résumé
// (centre, rayon réellement utilisé, nombre de sommets et d'arêtes).
export async function fetchGraph({ lat, lon, distanceKm, drawing }, { signal } = {}) {
  const { meta } = await request("/api/graph/fetch", {
    method: "POST",
    body: { lat, lon, distance_km: distanceKm, drawing },
    signal,
    fallback: "Extraction du réseau routier impossible",
  });
  return {
    center: meta?.center ?? [lat, lon],
    radiusKm: meta?.radius_km ?? distanceKm / 2,
    distanceKm,
    nodeCount: meta?.node_count ?? 0,
    edgeCount: meta?.edge_count ?? 0,
  };
}

// Demande au serveur de calculer les propositions d'itinéraires (texte résumé, trajets, métriques).
// Le serveur retrouve le graphe dans son cache à partir du point choisi.
export function planRoutes({ lat, lon, distanceKm, drawing }, { signal } = {}) {
  return request("/api/routes/plan", {
    method: "POST",
    body: { lat, lon, distance_km: distanceKm, drawing },
    signal,
    fallback: "Calcul des itinéraires impossible",
  });
}
