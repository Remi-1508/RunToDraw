import { useEffect, useState } from "react";
import { fetchOverpassStatus } from "../api/runtodraw";

const REFRESH_MS = 90_000;

// État des serveurs OpenStreetMap, vérifié à l'ouverture puis toutes les 90 secondes tant que la page est visible.
export function useOverpassStatus() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    const refresh = () => {
      if (document.hidden) return;
      fetchOverpassStatus({ signal: controller.signal })
        .then(setStatus)
        .catch(() => {});
    };
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  return status;
}
