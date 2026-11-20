import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGraph, planRoutes } from "../api/runtodraw";
import { estimateGraphSeconds, estimatePlanSeconds, recordGraphDuration, recordPlanDuration } from "../utils/estimate";
import { isGraphReady, markGraphReady } from "../utils/graphPrefetch";
import { notifyRouteReady } from "../utils/notify";

// Nouvelle tentative automatique : le serveur gratuit s'endort après un moment d'inactivité et met jusqu'à une
// minute à se réveiller, et les serveurs OpenStreetMap répondent parfois en erreur. Plutôt que d'afficher une erreur
// que la personne devrait relancer à la main, on réessaie toutes les quelques secondes, jusqu'à RETRY_MAX_MS.
const RETRY_DELAY_MS = 4000;
const RETRY_MAX_MS = 3 * 60 * 1000;
const RETRY_NOTE = "Le serveur met du temps à répondre : nouvel essai automatique en cours…";

// Erreur passagère : serveur injoignable (status 0), erreur de passerelle (502/503/504) ou limite momentanée (429).
function isRetryable(error) {
  return error.name !== "AbortError" && [0, 429, 502, 503, 504].includes(error.status ?? 0);
}

// Attente interrompue par « Annuler » (le signal lève alors une AbortError).
function pause(ms, signal) {
  return new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Annulé", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    if (signal.aborted) abort();
    else signal.addEventListener("abort", abort, { once: true });
  });
}

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

  // Lance la génération. La distance demandée n'est jamais modifiée : en cas d'erreur passagère, la même génération
  // est retentée automatiquement (voir isRetryable), car la lenteur des serveurs varie d'une minute à l'autre.
  const generate = useCallback(
    async ({ lat, lon, distanceKm, drawing, throughStart = false }) => {
      const controller = new AbortController();
      abortRef.current = controller;
      const options = { signal: controller.signal };

      // Un seul chronomètre pour toute la génération : il part au clic et ne se remet pas à zéro entre l'extraction
      // du réseau routier et le calcul de l'itinéraire. Pendant l'extraction on ne connaît pas encore la taille du
      // graphe : l'estimation totale suppose environ 1 000 intersections par km², puis elle est recalculée avec le
      // vrai nombre d'intersections dès que le serveur le donne.
      const startedAt = Date.now();
      const NODES_PER_KM2_GUESS = 1000;

      async function attempt(note) {
        const graphRadiusKm = distanceKm / 2; // estimation : le serveur précise le rayon réel après l'extraction
        const graphStart = Date.now();
        const guessedNodes = Math.PI * graphRadiusKm * graphRadiusKm * NODES_PER_KM2_GUESS;
        setBusy({
          title: "Extraction de la zone de course",
          note,
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
          note,
          startedAt,
          // temps déjà écoulé + durée estimée du calcul, maintenant que la taille du graphe est connue
          estimateSeconds: (planStart - startedAt) / 1000 + estimatePlanSeconds(nextGraph.nodeCount, drawing),
        });
        const nextPlan = await planRoutes({ lat, lon, distanceKm, drawing, throughStart }, options);
        recordPlanDuration(nextGraph.nodeCount, drawing, (Date.now() - planStart) / 1000);
        setRoutePlan(nextPlan);
        setPlanContext({ lat, lon, distanceKm, drawing, throughStart });
        setSelectedRouteId(nextPlan?.routes?.[0]?.id ?? null);
      }

      try {
        const deadline = Date.now() + RETRY_MAX_MS;
        let note;
        for (;;) {
          try {
            await attempt(note);
            break;
          } catch (error) {
            if (!isRetryable(error) || Date.now() > deadline) throw error;
            note = RETRY_NOTE;
            setBusy((current) => (current ? { ...current, note } : current));
            // Limite de débit : on respecte le délai demandé par le serveur s'il est donné.
            await pause(Math.max(RETRY_DELAY_MS, (error.retryAfter ?? 0) * 1000), controller.signal);
          }
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
