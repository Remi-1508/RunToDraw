import { useCallback, useEffect, useRef, useState } from "react";

// Un message d'erreur est plus long à lire (et souvent à comprendre) qu'une confirmation.
const TOAST_DURATION_MS = 3500;
const ERROR_DURATION_MS = 9000;

// Petit message flottant (succès, erreur, information) qui se masque tout seul après quelques secondes.
export function useToast() {
  const [toast, setToast] = useState({ open: false, message: "", type: "success" });
  const timerRef = useRef(null);

  const hideToast = useCallback(() => {
    setToast((current) => ({ ...current, open: false }));
  }, []);

  const showToast = useCallback(
    (message, type = "success") => {
      if (timerRef.current) clearTimeout(timerRef.current);
      setToast({ open: true, message, type });
      timerRef.current = setTimeout(hideToast, type === "error" ? ERROR_DURATION_MS : TOAST_DURATION_MS);
    },
    [hideToast]
  );

  // Au démontage, le minuteur en cours est supprimé.
  useEffect(() => () => timerRef.current && clearTimeout(timerRef.current), []);

  return { toast, showToast, hideToast };
}
