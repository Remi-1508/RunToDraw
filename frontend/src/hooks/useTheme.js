import { useCallback, useEffect, useState } from "react";
import { STORAGE_KEYS } from "../config";
import { readStorage, writeStorage } from "../utils/storage";

// Thème clair / sombre : restauré depuis le stockage local, appliqué à la racine du document
// (les variables CSS réagissent à l'attribut data-theme) et mémorisé à chaque changement.
export function useTheme() {
  const [theme, setTheme] = useState(() => readStorage(STORAGE_KEYS.theme) || "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    writeStorage(STORAGE_KEYS.theme, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }, []);

  return { theme, toggleTheme };
}
