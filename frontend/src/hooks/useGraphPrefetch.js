import { useEffect } from "react";
import { LONG_DISTANCE_CONFIRM_KM } from "../config";
import { prefetchGraph } from "../utils/graphPrefetch";

// Délai sans changement avant de lancer le préchargement : tant que la personne règle la distance ou tape
// son mot, on n'envoie rien au serveur.
const PREFETCH_DELAY_MS = 2500;

// Précharge le réseau routier en arrière-plan dès que le départ, la distance et le dessin sont choisis.
// Pas de préchargement pour un dessin libre (il change le rayon à chaque trait), pour un texte vide, pour
// les très longues distances (téléchargement lourd, demandé seulement après confirmation) ni pendant une génération.
export function useGraphPrefetch({ center, distanceKm, drawing, enabled }) {
  const mode = drawing.mode;
  const text = drawing.text;
  const shape = drawing.shape;

  useEffect(() => {
    if (!enabled || !center || distanceKm > LONG_DISTANCE_CONFIRM_KM) return undefined;
    if (mode === "custom" || (mode === "text" && !text?.trim())) return undefined;
    const timer = setTimeout(() => {
      prefetchGraph({ lat: center[0], lon: center[1], distanceKm, drawing: { mode, shape, text, points: [] } });
    }, PREFETCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [enabled, center, distanceKm, mode, shape, text]);
}
