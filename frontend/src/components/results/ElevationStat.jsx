import { useRouteElevation } from "../../hooks/useRouteElevation";

// Dénivelé positif total de l'itinéraire, affiché « 123 d+ ». Rien n'est montré si le service d'altitudes
// est indisponible : mieux vaut ne rien dire qu'un chiffre faux.
export default function ElevationStat({ route, strong = false }) {
  const { status, elevation } = useRouteElevation(route);
  if (status === "unavailable") return strong ? <span>—</span> : null;
  if (status === "loading") return <span aria-busy="true">… d+</span>;
  return (
    <span title="Dénivelé positif cumulé, estimé à partir d'un modèle de terrain">
      <strong>{elevation.gainM} d+</strong>
    </span>
  );
}
