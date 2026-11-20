import { useEffect, useRef } from "react";

// Distance (px) ou vitesse (px/ms) de glissement vers le bas à partir desquelles le tiroir se referme.
const CLOSE_DISTANCE = 100;
const CLOSE_VELOCITY = 0.6;

// Glisser vers le bas sur l'en-tête du tiroir mobile (élément `.rtd-sheet-handle`) le referme.
// Pendant le geste, le tiroir suit le doigt ; au relâchement il se referme ou revient en place.
// Le déplacement est appliqué directement sur l'élément (sans état React) pour rester fluide, et les
// écouteurs sont posés sur l'élément lui-même : le hook renvoie seulement la `ref` à poser sur le tiroir.
export function useSheetSwipe({ enabled, onClose }) {
  const ref = useRef(null);
  const closeRef = useRef(onClose);

  // Garde la dernière fonction de fermeture sans réinstaller les écouteurs à chaque rendu.
  useEffect(() => {
    closeRef.current = onClose;
  });

  useEffect(() => {
    const element = ref.current;
    if (!element || !enabled) return undefined;
    let drag = null;

    function onPointerDown(event) {
      if (event.button > 0) return;
      // Le bouton « replier » garde son clic ; seul le reste de l'en-tête sert de poignée.
      if (event.target.closest("button") || !event.target.closest(".rtd-sheet-handle")) return;
      drag = { id: event.pointerId, startY: event.clientY, lastY: event.clientY, lastT: event.timeStamp, velocity: 0, dy: 0 };
      element.setPointerCapture(event.pointerId);
      element.style.transition = "none";
    }

    function onPointerMove(event) {
      if (!drag || drag.id !== event.pointerId) return;
      drag.dy = Math.max(0, event.clientY - drag.startY);
      const dt = event.timeStamp - drag.lastT;
      if (dt > 0) drag.velocity = (event.clientY - drag.lastY) / dt;
      drag.lastY = event.clientY;
      drag.lastT = event.timeStamp;
      element.style.transform = `translateY(${drag.dy}px)`;
    }

    function end(event) {
      if (!drag || drag.id !== event.pointerId) return;
      const state = drag;
      drag = null;
      // On rend la main au CSS : le tiroir s'anime vers sa position fermée ou revient à sa place.
      element.style.transition = "";
      element.style.transform = "";
      if (event.type === "pointerup" && (state.dy > CLOSE_DISTANCE || state.velocity > CLOSE_VELOCITY)) closeRef.current();
    }

    element.addEventListener("pointerdown", onPointerDown);
    element.addEventListener("pointermove", onPointerMove);
    element.addEventListener("pointerup", end);
    element.addEventListener("pointercancel", end);
    return () => {
      element.removeEventListener("pointerdown", onPointerDown);
      element.removeEventListener("pointermove", onPointerMove);
      element.removeEventListener("pointerup", end);
      element.removeEventListener("pointercancel", end);
      element.style.transition = "";
      element.style.transform = "";
    };
  }, [enabled]);

  return ref;
}
