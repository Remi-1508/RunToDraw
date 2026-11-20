import { useCallback, useEffect, useState } from "react";
import { STORAGE_KEYS } from "../config";
import { readStorage, writeStorage } from "../utils/storage";

const DARK_QUERY = "(prefers-color-scheme: dark)";

// Réglage du téléphone ou de l'ordinateur : "dark" ou "light".
function systemTheme() {
  return window.matchMedia?.(DARK_QUERY).matches ? "dark" : "light";
}

// Thème clair / sombre. Tant que la personne n'a pas choisi elle-même (bouton « Mode nuit »), on suit le réglage
// de son appareil, y compris quand il change (passage automatique en mode sombre le soir). Dès qu'elle bascule
// le thème, son choix est mémorisé et prime sur le réglage de l'appareil.
export function useTheme() {
  const [choice, setChoice] = useState(() => readStorage(STORAGE_KEYS.theme)); // "light" | "dark" | null (auto)
  const [system, setSystem] = useState(systemTheme);

  useEffect(() => {
    const query = window.matchMedia?.(DARK_QUERY);
    if (!query) return undefined;
    const onChange = () => setSystem(query.matches ? "dark" : "light");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const theme = choice === "dark" || choice === "light" ? choice : system;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    const next = theme === "light" ? "dark" : "light";
    writeStorage(STORAGE_KEYS.theme, next);
    setChoice(next);
  }, [theme]);

  return { theme, toggleTheme };
}
