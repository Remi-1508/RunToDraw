import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { editRoute, linkLetters } from "../api/runtodraw";

// Nombre maximal d'étapes gardées pour annuler / rétablir (par itinéraire).
const MAX_HISTORY = 60;

const NO_HISTORIES = {};

// Édition de l'itinéraire sur la carte : déplacer, insérer ou supprimer un point du tracé.
//
// Chaque modification est envoyée au serveur, qui ne recalcule que les tronçons voisins du point touché
// et renvoie les segments à jour. Le hook garde, pour chaque itinéraire, l'historique des versions
// (segments complets) : annuler / rétablir ne rappelle donc pas le serveur.
//
// L'historique est rattaché à la liste de propositions courante (`routePlan`) : une nouvelle génération
// repart de zéro sans qu'il faille nettoyer quoi que ce soit.
export function useRouteEditor({ routePlan, selectedRoute, planContext, showToast }) {
  // { plan, byId: { [idItinéraire]: { stack: [segments, ...], index } } }
  const [state, setState] = useState({ plan: null, byId: NO_HISTORIES });
  const [editMode, setEditMode] = useState(false);
  const [pending, setPending] = useState(false);
  // Point sélectionné : { segments, segmentIndex, anchor }. `segments` sert à invalider la sélection
  // dès que le tracé change (les numéros de points ne sont plus valables).
  const [selection, setSelection] = useState(null);
  const busyRef = useRef(false);
  const abortRef = useRef(null);

  const histories = state.plan === routePlan ? state.byId : NO_HISTORIES;
  const history = selectedRoute ? histories[selectedRoute.id] : undefined;

  // Itinéraire affiché : l'original, ou sa dernière version modifiée.
  const route = useMemo(() => {
    if (!selectedRoute) return null;
    if (!history || history.index === 0) return selectedRoute;
    const segments = history.stack[history.index];
    return {
      ...selectedRoute,
      segments,
      total_distance_m: segments.reduce((sum, segment) => sum + (segment.distance_m ?? 0), 0),
      edited: true,
    };
  }, [selectedRoute, history]);

  const selectedAnchor = selection && route && selection.segments === route.segments ? selection : null;
  const canUndo = Boolean(history && history.index > 0);
  const canRedo = Boolean(history && history.index < history.stack.length - 1);

  // Remplace l'historique de l'itinéraire courant (le plan peut avoir changé depuis le dernier appel).
  const writeHistory = useCallback(
    (routeId, next) => {
      setState((prev) => {
        const base = prev.plan === routePlan ? prev.byId : NO_HISTORIES;
        const copy = { ...base };
        if (next) copy[routeId] = next;
        else delete copy[routeId];
        return { plan: routePlan, byId: copy };
      });
    },
    [routePlan]
  );

  // Envoie une modification au serveur. Renvoie true si elle a été appliquée (le marqueur déplacé
  // sait ainsi s'il doit revenir à sa place d'origine).
  const applyOperation = useCallback(
    async (segmentIndex, operation) => {
      if (!route || !planContext || busyRef.current) return false;
      const controller = new AbortController();
      abortRef.current = controller;
      busyRef.current = true;
      setPending(true);
      try {
        const result = await editRoute(planContext, route.segments, segmentIndex, operation, {
          signal: controller.signal,
        });
        const base = history ?? { stack: [selectedRoute.segments], index: 0 };
        const stack = [...base.stack.slice(0, base.index + 1), result.segments].slice(-MAX_HISTORY);
        // `source` (lettres reliées) est conservé : une retouche du parcours relié n'est pas écrasée.
        writeHistory(selectedRoute.id, { ...base, stack, index: stack.length - 1 });
        setSelection(null);
        return true;
      } catch (error) {
        if (error.name !== "AbortError") showToast(error.message || "Modification impossible.", "error");
        return false;
      } finally {
        abortRef.current = null;
        busyRef.current = false;
        setPending(false);
      }
    },
    [route, planContext, history, selectedRoute, writeHistory, showToast]
  );

  const undo = useCallback(() => {
    if (!history || history.index === 0) return;
    writeHistory(selectedRoute.id, { ...history, index: history.index - 1 });
    setSelection(null);
  }, [history, selectedRoute, writeHistory]);

  const redo = useCallback(() => {
    if (!history || history.index >= history.stack.length - 1) return;
    writeHistory(selectedRoute.id, { ...history, index: history.index + 1 });
    setSelection(null);
  }, [history, selectedRoute, writeHistory]);

  // Revient au tracé généré par le serveur. L'historique est conservé : « Rétablir » ramène les modifications
  // tant qu'aucune nouvelle édition n'a été faite.
  const reset = useCallback(() => {
    if (!history || history.index === 0) return;
    writeHistory(selectedRoute.id, { ...history, index: 0 });
    setSelection(null);
  }, [history, selectedRoute, writeHistory]);

  const selectAnchor = useCallback(
    (segmentIndex, anchor) => {
      if (!route) return;
      setSelection({ segments: route.segments, segmentIndex, anchor });
    },
    [route]
  );

  const deleteSelected = useCallback(() => {
    if (!selectedAnchor) return Promise.resolve(false);
    return applyOperation(selectedAnchor.segmentIndex, { type: "delete", anchor: selectedAnchor.anchor });
  }, [selectedAnchor, applyOperation]);

  const toggleEditMode = useCallback(() => {
    setEditMode((on) => !on);
    setSelection(null);
  }, []);

  // Lettres reliées : quand les lettres séparées ont été modifiées, le parcours relié est recalculé à partir
  // de ces lettres (sens de chaque lettre et liaisons réoptimisés). `history.source` mémorise les lettres
  // utilisées pour ce calcul : tant qu'elles ne changent pas, une retouche manuelle du parcours relié reste.
  const separateRoute = routePlan?.routes?.find((r) => r.kind === "letters_separate");
  const linkedRoute = routePlan?.routes?.find((r) => r.kind === "letters_linked");
  const separateHistory = separateRoute ? histories[separateRoute.id] : undefined;
  const letterSegments = separateRoute
    ? separateHistory
      ? separateHistory.stack[separateHistory.index]
      : separateRoute.segments
    : null;
  const linkedId = linkedRoute?.id;
  const linkedSource = linkedId ? histories[linkedId]?.source : undefined;
  useEffect(() => {
    if (!linkedRoute || !separateRoute || !planContext) return undefined;
    if (linkedSource === letterSegments) return undefined;
    if (letterSegments === separateRoute.segments) {
      // Lettres revenues à l'original : le parcours relié l'est aussi.
      if (linkedSource) writeHistory(linkedRoute.id, null);
      return undefined;
    }
    const controller = new AbortController();
    linkLetters(planContext, letterSegments, { signal: controller.signal })
      .then((result) => {
        writeHistory(linkedRoute.id, {
          stack: [linkedRoute.segments, result.segments],
          index: 1,
          source: letterSegments,
        });
      })
      .catch((error) => {
        if (error.name !== "AbortError") showToast(error.message || "Jonction des lettres impossible.", "error");
      });
    return () => controller.abort();
  }, [letterSegments, linkedSource, linkedRoute, separateRoute, planContext, writeHistory, showToast]);

  // Un calcul en cours est abandonné si le composant est démonté.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Raccourcis clavier (mode édition) : Ctrl/Cmd+Z annuler, Ctrl+Y ou Ctrl/Cmd+Maj+Z rétablir,
  // Suppr / Retour arrière supprime le point sélectionné. Ignorés pendant la saisie dans un champ.
  useEffect(() => {
    if (!editMode) return undefined;
    function onKeyDown(event) {
      const tag = event.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || event.target?.isContentEditable) return;
      const mod = event.ctrlKey || event.metaKey;
      const key = event.key.toLowerCase();
      if (mod && key === "z") {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
      } else if (mod && key === "y") {
        event.preventDefault();
        redo();
      } else if (key === "delete" || key === "backspace") {
        if (selectedAnchor) {
          event.preventDefault();
          deleteSelected();
        }
      } else if (key === "escape") {
        setSelection(null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editMode, undo, redo, deleteSelected, selectedAnchor]);

  return {
    route,
    editMode,
    toggleEditMode,
    pending,
    canUndo,
    canRedo,
    canReset: canUndo,
    isEdited: Boolean(route?.edited),
    selectedAnchor,
    selectAnchor,
    applyOperation,
    deleteSelected,
    undo,
    redo,
    reset,
  };
}
