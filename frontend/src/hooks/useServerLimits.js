import { useEffect, useState } from "react";
import { FALLBACK_MAX_DISTANCE_KM } from "../config";
import { fetchServerLimits } from "../api/runtodraw";

// Distance maximale acceptée par le serveur, lue une fois au chargement
// (valeur prudente en attendant la réponse, ou si le serveur ne répond pas).
export function useServerLimits() {
  const [maxDistanceKm, setMaxDistanceKm] = useState(FALLBACK_MAX_DISTANCE_KM);

  useEffect(() => {
    const controller = new AbortController();
    fetchServerLimits({ signal: controller.signal })
      .then((limits) => setMaxDistanceKm(limits.maxDistanceKm))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  return { maxDistanceKm };
}
