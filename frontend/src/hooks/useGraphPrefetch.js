import { useEffect } from "react";
import { LONG_DISTANCE_CONFIRM_KM, MIN_DRAW_POINTS } from "../config";
import { prefetchGraph } from "../utils/graphPrefetch";

// Délai sans changement avant de lancer le préchargement : tant que la personne règle la distance ou tape
// son mot, on n'envoie rien au serveur.
const PREFETCH_DELAY_MS = 2500;

// Précharge le réseau routier en arrière-plan dès que le départ, la distance et le dessin sont choisis.
// Le rayon à télécharger dépend du texte et, pour un dessin libre, du tracé : on attend donc que la personne ait
// fini de taper ou de dessiner (le délai repart à chaque changement), puis on envoie le même dessin que la
// génération enverra, pour que le serveur calcule la même zone. Pas de préchargement pour un texte ou un dessin
// trop courts, pour les très longues distances (téléchargement lourd, demandé seulement après confirmation)
// ni pendant une génération.
export function useGraphPrefetch({ center, distanceKm, drawing, enabled }) {
  const mode = drawing.mode;
  const text = drawing.text;
  const shape = drawing.shape;
  const points = drawing.points;

  useEffect(() => {
    if (!enabled || !center || distanceKm > LONG_DISTANCE_CONFIRM_KM) return undefined;
    if (mode === "text" && !text?.trim()) return undefined;
    if (mode === "custom" && (points?.length ?? 0) < MIN_DRAW_POINTS) return undefined;
    const timer = setTimeout(() => {
      prefetchGraph({ lat: center[0], lon: center[1], distanceKm, drawing: { mode, shape, text, points: mode === "custom" ? points : [] } });
    }, PREFETCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [enabled, center, distanceKm, mode, shape, text, points]);
}
