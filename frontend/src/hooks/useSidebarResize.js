import { useCallback, useEffect, useState } from "react";
import { SIDEBAR_WIDTH, STORAGE_KEYS } from "../config";
import { readStorage, writeStorage } from "../utils/storage";

// Place minimale laissée à la carte quand la barre latérale est agrandie.
const MIN_MAP_WIDTH = 420;

function restoreWidth() {
  const saved = Number(readStorage(STORAGE_KEYS.sidebarWidth));
  const valid = Number.isFinite(saved) && saved >= SIDEBAR_WIDTH.min && saved <= SIDEBAR_WIDTH.max;
  return valid ? saved : SIDEBAR_WIDTH.default;
}

// Largeur de la barre latérale, redimensionnable à la souris (poignée entre la barre et la carte).
// La largeur choisie est mémorisée entre deux visites.
export function useSidebarResize() {
  const [sidebarWidth, setSidebarWidth] = useState(restoreWidth);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    writeStorage(STORAGE_KEYS.sidebarWidth, sidebarWidth);
  }, [sidebarWidth]);

  // Pendant le glissement : la souris met à jour la largeur, son relâchement arrête le mode.
  useEffect(() => {
    if (!isResizing) return undefined;

    document.body.classList.add("app-resizing");

    function handleMouseMove(event) {
      const maxAllowed = Math.min(SIDEBAR_WIDTH.max, window.innerWidth - MIN_MAP_WIDTH);
      setSidebarWidth(Math.min(Math.max(event.clientX, SIDEBAR_WIDTH.min), Math.max(SIDEBAR_WIDTH.min, maxAllowed)));
    }
    const stopResize = () => setIsResizing(false);

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopResize);
    window.addEventListener("mouseleave", stopResize);
    return () => {
      document.body.classList.remove("app-resizing");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopResize);
      window.removeEventListener("mouseleave", stopResize);
    };
  }, [isResizing]);

  const startResize = useCallback(() => setIsResizing(true), []);

  return { sidebarWidth, startResize };
}
