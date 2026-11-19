import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGraph, planRoutes } from "../api/runtodraw";

// Part de la distance demandée conservée quand les serveurs OpenStreetMap sont trop lents (voir generate).
const RETRY_DISTANCE_RATIO = 0.6;

// Génération des itinéraires : téléchargement du réseau routier puis calcul des propositions.
// Le hook garde les résultats (graphe, propositions, itinéraire choisi) et l'état d'attente,
// et permet d'annuler une génération en cours.
export function useRoutePlanning({ showToast }) {
  const [graphData, setGraphData] = useState(null);
  const [routePlan, setRoutePlan] = useState(null);
  // Paramètres de la génération en cours de validité ({ lat, lon, distanceKm, drawing }) : nécessaires
  // pour modifier ensuite le tracé sur le même réseau routier, même si le formulaire a changé entre-temps.
  const [planContext, setPlanContext] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  // null quand rien n'est en cours, sinon { kicker, description } pour la fenêtre d'attente.
  const [busy, setBusy] = useState(null);
  const abortRef = useRef(null);

  const selectedRoute = routePlan?.routes?.find((route) => route.id === selectedRouteId) ?? null;

  // Efface les résultats (par exemple quand le point de départ change).
  const reset = useCallback(() => {
    setGraphData(null);
    setRoutePlan(null);
    setPlanContext(null);
    setSelectedRouteId(null);
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  // Une génération en cours est annulée si le composant est démonté.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Lance la génération. `onShorterDistance(km)` est appelée si un nouvel essai avec une distance plus courte
  // est tenté automatiquement (la zone à télécharger étant plus petite, Overpass y répond plus souvent) :
  // l'interface y met à jour la distance affichée.
  const generate = useCallback(
    async ({ lat, lon, distanceKm, drawing }, { onShorterDistance } = {}) => {
      const controller = new AbortController();
      abortRef.current = controller;
      const options = { signal: controller.signal };

      async function attempt(km) {
        setBusy({ kicker: "Étape 1/2", description: "Extraction du graphe OpenStreetMap…" });
        const nextGraph = await fetchGraph({ lat, lon, distanceKm: km, drawing }, options);
        setGraphData(nextGraph);
        setRoutePlan(null);
        setSelectedRouteId(null);

        setBusy({
          kicker: "Étape 2/2",
          description: "Analyse de la forme demandée et recherche des meilleures trajectoires…",
        });
        const nextPlan = await planRoutes({ lat, lon, distanceKm: km, drawing }, options);
        setRoutePlan(nextPlan);
        setPlanContext({ lat, lon, distanceKm: km, drawing });
        setSelectedRouteId(nextPlan?.routes?.[0]?.id ?? null);
      }

      try {
        let km = distanceKm;
        let retried = false;
        for (;;) {
          try {
            await attempt(km);
            break;
          } catch (error) {
            // Erreur 502 = serveurs OpenStreetMap indisponibles ou trop lents : un seul nouvel essai, plus court.
            const shorter = Math.max(2, Math.round(km * RETRY_DISTANCE_RATIO));
            if (error.status !== 502 || retried || !onShorterDistance || shorter >= km) throw error;
            retried = true;
            km = shorter;
            onShorterDistance(shorter);
            showToast(`Serveurs OpenStreetMap trop lents : nouvel essai automatique avec ${shorter} km.`, "info");
          }
        }
        showToast("Les propositions d’itinéraires sont prêtes.", "success");
      } catch (error) {
        setRoutePlan(null);
        setPlanContext(null);
        setSelectedRouteId(null);
        if (error.name === "AbortError") {
          showToast("Génération annulée.", "info");
        } else {
          console.error("Erreur pendant la génération :", error);
          showToast(error.message || "Erreur pendant la génération des itinéraires.", "error");
        }
      } finally {
        abortRef.current = null;
        setBusy(null);
      }
    },
    [showToast]
  );

  return { graphData, routePlan, planContext, selectedRoute, selectedRouteId, setSelectedRouteId, busy, generate, cancel, reset };
}
