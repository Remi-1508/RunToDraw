import { useCallback, useEffect, useState } from "react";
import { STORAGE_KEYS } from "../config";
import { readStorage, writeStorage } from "../utils/storage";

// Fond de la carte : tuiles OpenStreetMap désaturées, ou aplat neutre où seul le tracé reste visible.
// Le choix est mémorisé dans le navigateur (même principe que le thème).
export function useMapBackground() {
  const [neutralBackground, setNeutralBackground] = useState(
    () => readStorage(STORAGE_KEYS.mapBackground) === "neutral"
  );

  useEffect(() => {
    writeStorage(STORAGE_KEYS.mapBackground, neutralBackground ? "neutral" : "map");
  }, [neutralBackground]);

  const toggleNeutralBackground = useCallback(() => setNeutralBackground((current) => !current), []);

  return { neutralBackground, toggleNeutralBackground };
}
