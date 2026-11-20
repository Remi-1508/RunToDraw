import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGraph, planRoutes } from "../api/runtodraw";
import { estimateGraphSeconds, estimatePlanSeconds, recordGraphDuration, recordPlanDuration } from "../utils/estimate";
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
  // null quand rien n'est en cours, sinon { kicker, description, startedAt, estimateSeconds } pour la fenêtre d'attente
  // (`startedAt` : début de l'étape en cours, pour le chronomètre ; `estimateSeconds` : durée estimée de cette étape).
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

      async function attempt() {
        const wordLabel = drawing?.mode === "text" ? "le mot " + (drawing.text || "").toUpperCase() : "la forme demandée";
        const graphRadiusKm = distanceKm / 2; // estimation : le serveur précise le rayon réel après l'extraction
        const graphStart = Date.now();
        setBusy({
          kicker: "Étape 1/2 · Réseau routier",
          description: `Téléchargement des routes et chemins OpenStreetMap autour du départ (zone d’environ ${graphRadiusKm.toFixed(1)} km de rayon). C’est l’étape la plus longue.`,
          startedAt: graphStart,
          estimateSeconds: estimateGraphSeconds(graphRadiusKm),
        });
        const nextGraph = await fetchGraph({ lat, lon, distanceKm, drawing }, options);
        recordGraphDuration(nextGraph.radiusKm, (Date.now() - graphStart) / 1000);
        setGraphData(nextGraph);
        setRoutePlan(null);
        setSelectedRouteId(null);

        const planStart = Date.now();
        setBusy({
          kicker: "Étape 2/2 · Calcul des tracés",
          description: `Recherche des meilleurs tracés pour ${wordLabel} parmi ${nextGraph.nodeCount.toLocaleString("fr-FR")} intersections.`,
          startedAt: planStart,
          estimateSeconds: estimatePlanSeconds(nextGraph.nodeCount, drawing),
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
