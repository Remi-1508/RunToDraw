import { useEffect, useState } from "react";
import { getRouteElevation } from "../api/elevation";

// Dénivelé d'un itinéraire (voir api/elevation.js). `status` : "loading" | "ready" | "unavailable".
// Un court délai évite de multiplier les requêtes pendant qu'on déplace un point du tracé.
export function useRouteElevation(route) {
  const [state, setState] = useState({ route: null, result: undefined });

  useEffect(() => {
    if (!route) return undefined;
    let cancelled = false;
    const timer = setTimeout(() => {
      getRouteElevation(route).then((result) => {
        if (!cancelled) setState({ route, result });
      });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [route]);

  if (!route || state.route !== route || state.result === undefined) return { status: "loading", elevation: null };
  return state.result ? { status: "ready", elevation: state.result } : { status: "unavailable", elevation: null };
}
