import { useRef } from "react";

// Distance (px) ou vitesse (px/ms) de glissement vers le bas à partir desquelles le tiroir se referme.
const CLOSE_DISTANCE = 100;
const CLOSE_VELOCITY = 0.6;

// Glisser vers le bas sur l'en-tête du tiroir mobile (élément `.rtd-sheet-handle`) le referme.
// Pendant le geste, le tiroir suit le doigt ; au relâchement il se referme ou revient en place.
// Le déplacement est appliqué directement sur l'élément (sans état React) pour rester fluide.
// Renvoie `ref` (à poser sur le tiroir) et les gestionnaires d'événements à lui passer.
export function useSheetSwipe({ enabled, onClose }) {
  const ref = useRef(null);
  const drag = useRef(null);

  function onPointerDown(event) {
    if (!enabled || event.button > 0) return;
    // Le bouton « replier » garde son clic ; seul le reste de l'en-tête sert de poignée.
    if (event.target.closest("button") || !event.target.closest(".rtd-sheet-handle")) return;
    drag.current = { id: event.pointerId, startY: event.clientY, lastY: event.clientY, lastT: event.timeStamp, velocity: 0, dy: 0 };
    event.currentTarget.setPointerCapture(event.pointerId);
    ref.current.style.transition = "none";
  }

  function onPointerMove(event) {
    const state = drag.current;
    if (!state || state.id !== event.pointerId) return;
    state.dy = Math.max(0, event.clientY - state.startY);
    const dt = event.timeStamp - state.lastT;
    if (dt > 0) state.velocity = (event.clientY - state.lastY) / dt;
    state.lastY = event.clientY;
    state.lastT = event.timeStamp;
    ref.current.style.transform = `translateY(${state.dy}px)`;
  }

  function end(event) {
    const state = drag.current;
    if (!state || state.id !== event.pointerId) return;
    drag.current = null;
    // On rend la main au CSS : le tiroir s'anime vers sa position fermée ou revient à sa place.
    ref.current.style.transition = "";
    ref.current.style.transform = "";
    if (event.type === "pointerup" && (state.dy > CLOSE_DISTANCE || state.velocity > CLOSE_VELOCITY)) onClose();
  }

  return { ref, handlers: { onPointerDown, onPointerMove, onPointerUp: end, onPointerCancel: end } };
}
