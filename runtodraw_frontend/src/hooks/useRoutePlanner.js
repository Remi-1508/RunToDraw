import { useEffect, useRef, useState } from "react";
import { fetchGraphForRun } from "../services/osmGraph";
import { planRoutesWithProgress } from "../services/routePlannerApi";

const SHOW_GRAPH_STORAGE_KEY = "runtodraw-show-full-graph";

/*
============================================================
Génération d'itinéraires : extraction du graphe puis recherche des
itinéraires, avec une progression réelle (le backend expose désormais une
tâche interrogeable par polling — voir routePlannerApi.planRoutesWithProgress
— au lieu d'une seule requête bloquante suivie d'une barre simulée).
============================================================
*/
export function useRoutePlanner({ center, distanceKm, drawing, onError, onSuccess }) {
  const [graphData, setGraphData] = useState(null);
  const [graphJsonPayload, setGraphJsonPayload] = useState(null);
  const [routePlan, setRoutePlan] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);

  const [showFullGraph, setShowFullGraph] = useState(() => {
    const saved = localStorage.getItem(SHOW_GRAPH_STORAGE_KEY);
    return saved === null ? false : saved === "true";
  });

  const [busyState, setBusyState] = useState({
    open: false,
    progress: 0,
    indeterminate: false,
    title: "",
    kicker: "",
    description: "",
  });

  const abortRef = useRef(null);

  useEffect(() => {
    localStorage.setItem(SHOW_GRAPH_STORAGE_KEY, String(showFullGraph));
  }, [showFullGraph]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  function resetComputedGraph() {
    setGraphData(null);
    setGraphJsonPayload(null);
    setRoutePlan(null);
    setSelectedRouteId(null);
    setShowFullGraph(false);
  }

  async function generateRoutes() {
    if (!center) return;
    const [lat, lng] = center;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setBusyState({
        open: true,
        progress: 0,
        indeterminate: true,
        title: "Préparation de l’itinéraire",
        kicker: "Étape 1/2",
        description: "Extraction du graphe OpenStreetMap…",
      });

      const nextGraph = await fetchGraphForRun({ lat, lon: lng, distanceKm });
      const payload = nextGraph.graphPayload;

      if (!payload || !payload.nodes || !payload.edges) {
        throw new Error("Graph payload invalide reçu depuis le backend.");
      }

      setGraphData(nextGraph);
      setGraphJsonPayload(payload);
      setRoutePlan(null);
      setSelectedRouteId(null);
      setShowFullGraph(false);

      setBusyState((current) => ({
        ...current,
        indeterminate: false,
        kicker: "Étape 2/2",
        description: "Recherche des meilleures trajectoires…",
        progress: 0,
      }));

      const nextPlan = await planRoutesWithProgress({
        graphPayload: payload,
        distanceKm,
        drawing,
        signal: controller.signal,
        onProgress: (fraction) => {
          setBusyState((current) => ({ ...current, progress: Math.round(fraction * 100) }));
        },
      });

      setRoutePlan(nextPlan);
      setSelectedRouteId(nextPlan?.routes?.[0]?.id ?? null);

      setBusyState((current) => ({ ...current, progress: 100 }));
      await new Promise((resolve) => setTimeout(resolve, 180));
      setBusyState((current) => ({ ...current, open: false, progress: 0 }));

      onSuccess?.();
    } catch (error) {
      if (error.name === "AbortError") return;

      console.error("generateRoutes error:", error);
      setRoutePlan(null);
      setSelectedRouteId(null);
      setBusyState((current) => ({ ...current, open: false, progress: 0 }));
      onError?.(error);
    }
  }

  return {
    graphData,
    graphJsonPayload,
    routePlan,
    selectedRouteId,
    setSelectedRouteId,
    showFullGraph,
    setShowFullGraph,
    busyState,
    generateRoutes,
    resetComputedGraph,
  };
}
