import { useRouteElevation } from "../../hooks/useRouteElevation";

// Dénivelé positif et négatif d'un itinéraire, en texte discret. Rien n'est affiché si le service d'altitudes
// est indisponible : mieux vaut ne rien dire qu'un chiffre faux.
export default function ElevationStat({ route, strong = false }) {
  const { status, elevation } = useRouteElevation(route);
  if (status === "unavailable") return strong ? <span>—</span> : null;
  if (status === "loading") return <span aria-busy="true">Dénivelé : calcul…</span>;
  return (
    <span title="Estimation à partir d'un modèle de terrain (précision de quelques mètres à dizaines de mètres)">
      {strong ? null : "Dénivelé : "}
      <strong>+{elevation.gainM} m</strong> / −{elevation.lossM} m
    </span>
  );
}
