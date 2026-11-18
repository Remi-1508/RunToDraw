import logoRunToDrawDay from "../../assets/logo_runtodraw_day.png";
import logoRunToDrawNight from "../../assets/logo_runtodraw_night.png";
import RouteResultsPanel from "../results/RouteResultsPanel";
import DistanceStep from "./DistanceStep";
import DrawingStep from "./DrawingStep";
import GenerateStep from "./GenerateStep";
import LocationStep from "./LocationStep";
import { styles } from "./styles";

// Panneau de contrôle principal : il guide l'utilisateur de bout en bout.
//   1) choisir un point de départ        4) générer les itinéraires
//   2) choisir une distance               5) consulter les résultats
//   3) choisir une forme ou un texte      6) exporter un itinéraire
export default function Sidebar({
  theme,
  center,
  distanceKm,
  setDistanceKm,
  maxDistanceKm,
  drawing,
  setDrawing,
  onUseMyLocation,
  onPickSuggestion,
  onGenerateRoutes,
  canGenerate,
  routePlan,
  selectedRouteId,
  onSelectRoute,
  onExportRoute,
}) {
  const currentLogo = theme === "dark" ? logoRunToDrawNight : logoRunToDrawDay;

  return (
    <div style={styles.sidebar}>
      {/* Logo collant : l'identité du projet reste visible quand la barre défile. */}
      <div style={styles.logoStickyWrap}>
        <div style={styles.logoZone}>
          <img src={currentLogo} alt="RunToDraw" style={styles.logoImage} />
        </div>
      </div>

      <LocationStep center={center} onUseMyLocation={onUseMyLocation} onPickSuggestion={onPickSuggestion} />
      <DistanceStep distanceKm={distanceKm} setDistanceKm={setDistanceKm} maxDistanceKm={maxDistanceKm} />
      <DrawingStep drawing={drawing} setDrawing={setDrawing} />
      <GenerateStep canGenerate={canGenerate} onGenerateRoutes={onGenerateRoutes} />

      {/* Résultats et exports. */}
      <RouteResultsPanel
        routePlan={routePlan}
        selectedRouteId={selectedRouteId}
        onSelectRoute={onSelectRoute}
        onExportRoute={onExportRoute}
      />
    </div>
  );
}
