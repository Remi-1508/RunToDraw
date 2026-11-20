import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGraph, planRoutes } from "../api/runtodraw";
import { estimateGraphSeconds, estimatePlanSeconds, recordGraphDuration, recordPlanDuration } from "../utils/estimate";
import { isGraphReady, markGraphReady } from "../utils/graphPrefetch";
import { notifyRouteReady } from "../utils/notify";

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
  // null quand rien n'est en cours, sinon { title, startedAt, estimateSeconds } pour la fenêtre d'attente
  // (`title` : étape en cours ; `startedAt` : clic sur « Générer », pour le chronomètre ; `estimateSeconds` : durée
  // totale estimée de la génération).
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

  // Lance la génération. La distance demandée n'est jamais modifiée : si les serveurs OpenStreetMap échouent
  // (erreur 502), la même génération est retentée une fois, car leur lenteur varie d'une minute à l'autre.
  const generate = useCallback(
    async ({ lat, lon, distanceKm, drawing }) => {
      const controller = new AbortController();
      abortRef.current = controller;
      const options = { signal: controller.signal };

      // Un seul chronomètre pour toute la génération : il part au clic et ne se remet pas à zéro entre l'extraction
      // du réseau routier et le calcul de l'itinéraire. Pendant l'extraction on ne connaît pas encore la taille du
      // graphe : l'estimation totale suppose environ 1 000 intersections par km², puis elle est recalculée avec le
      // vrai nombre d'intersections dès que le serveur le donne.
      const startedAt = Date.now();
      const NODES_PER_KM2_GUESS = 1000;

      async function attempt() {
        const graphRadiusKm = distanceKm / 2; // estimation : le serveur précise le rayon réel après l'extraction
        const graphStart = Date.now();
        const guessedNodes = Math.PI * graphRadiusKm * graphRadiusKm * NODES_PER_KM2_GUESS;
        setBusy({
          title: "Extraction de la zone de course",
          startedAt,
          // Réseau déjà préchargé (ou généré récemment) : seul reste un aller-retour avec le serveur.
          estimateSeconds:
            (isGraphReady({ lat, lon, distanceKm, drawing }) ? 2 : estimateGraphSeconds(graphRadiusKm)) +
            estimatePlanSeconds(guessedNodes, drawing),
        });
        const nextGraph = await fetchGraph({ lat, lon, distanceKm, drawing }, options);
        recordGraphDuration(nextGraph.radiusKm, (Date.now() - graphStart) / 1000);
        markGraphReady({ lat, lon, distanceKm, drawing });
        setGraphData(nextGraph);
        setRoutePlan(null);
        setSelectedRouteId(null);

        const planStart = Date.now();
        setBusy({
          title: "Calcul de l’itinéraire",
          startedAt,
          // temps déjà écoulé + durée estimée du calcul, maintenant que la taille du graphe est connue
          estimateSeconds: (planStart - startedAt) / 1000 + estimatePlanSeconds(nextGraph.nodeCount, drawing),
        });
        const nextPlan = await planRoutes({ lat, lon, distanceKm, drawing }, options);
        recordPlanDuration(nextGraph.nodeCount, drawing, (Date.now() - planStart) / 1000);
        setRoutePlan(nextPlan);
        setPlanContext({ lat, lon, distanceKm, drawing });
        setSelectedRouteId(nextPlan?.routes?.[0]?.id ?? null);
      }

      try {
        try {
          await attempt();
        } catch (error) {
          if (error.status !== 502) throw error;
          showToast("Les serveurs OpenStreetMap n’ont pas répondu : nouvel essai automatique.", "info");
          await attempt();
        }
        showToast("Les propositions d’itinéraires sont prêtes.", "success");
        notifyRouteReady({ title: "Parcours prêt", body: "Tes propositions d’itinéraires sont prêtes, touche pour les voir." });
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
