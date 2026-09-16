import { useEffect, useRef, useState } from "react";

const STORAGE_KEY = "runtodraw-theme";

/*
============================================================
Thème clair/sombre : restauré depuis localStorage, appliqué sur
document.documentElement pour que les variables CSS réagissent, et changé
avec une petite transition (le nouveau thème n'apparaît qu'après un court
délai, le temps qu'un voile de transition masque le changement brutal).
============================================================
*/
export function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem(STORAGE_KEY) || "light");
  const [loadingTheme, setLoadingTheme] = useState(false);
  const timeoutsRef = useRef([]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(clearTimeout);
    };
  }, []);

  function toggleTheme() {
    if (loadingTheme) return;

    setLoadingTheme(true);
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [
      setTimeout(() => {
        setTheme((current) => (current === "light" ? "dark" : "light"));
      }, 260),
      setTimeout(() => {
        setLoadingTheme(false);
      }, 980),
    ];
  }

  return { theme, loadingTheme, toggleTheme };
}
