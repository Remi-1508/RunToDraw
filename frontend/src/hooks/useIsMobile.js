import { useSyncExternalStore } from "react";

// Largeur en dessous de laquelle la barre latérale devient un tiroir par-dessus la carte (voir index.css,
// qui utilise la même valeur dans sa règle @media).
export const MOBILE_MAX_WIDTH = 820;
const QUERY = `(max-width: ${MOBILE_MAX_WIDTH}px)`;

function subscribe(onChange) {
  const query = window.matchMedia(QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

// true sur smartphone / petite fenêtre ; se met à jour si la fenêtre est redimensionnée ou l'écran pivoté.
export function useIsMobile() {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => false
  );
}
