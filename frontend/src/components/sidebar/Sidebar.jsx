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
  startLabel,
  pickingOnMap,
  onTogglePickOnMap,
  onClearStart,
  onClosePanel,
  onGenerateRoutes,
  canGenerate,
  routePlan,
  selectedRouteId,
  onSelectRoute,
  onExportRoute,
  onClearRoute,
  onShareRoute,
  serviceStatus,
}) {
  const currentLogo = theme === "dark" ? logoRunToDrawNight : logoRunToDrawDay;

  return (
    <div style={styles.sidebar}>
      {/* Logo collant : l'identité du projet reste visible quand la barre défile. */}
      <div className="rtd-sheet-handle" style={styles.logoStickyWrap}>
        <div className="rtd-sheet-grip" aria-hidden="true" />
        <div style={styles.logoZone}>
          <img src={currentLogo} alt="RunToDraw" style={styles.logoImage} />
        </div>
        <button type="button" className="rtd-collapse" onClick={onClosePanel} aria-label="Replier le panneau" title="Replier le panneau">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path className="rtd-collapse-desktop" d="M15 6l-6 6 6 6" />
            <path className="rtd-collapse-mobile" d="M6 9l6 6 6-6" />
          </svg>
        </button>
      </div>

      <LocationStep
        center={center}
        onUseMyLocation={onUseMyLocation}
        onPickSuggestion={onPickSuggestion}
        startLabel={startLabel}
        pickingOnMap={pickingOnMap}
        onTogglePickOnMap={onTogglePickOnMap}
        onClearStart={onClearStart}
      />
      <DistanceStep distanceKm={distanceKm} setDistanceKm={setDistanceKm} maxDistanceKm={maxDistanceKm} />
      <DrawingStep drawing={drawing} setDrawing={setDrawing} />
      <GenerateStep canGenerate={canGenerate} onGenerateRoutes={onGenerateRoutes} serviceStatus={serviceStatus} />

      {/* Résultats et exports. */}
      <RouteResultsPanel
        routePlan={routePlan}
        selectedRouteId={selectedRouteId}
        onSelectRoute={onSelectRoute}
        onExportRoute={onExportRoute}
        onClearRoute={onClearRoute}
        onShareRoute={onShareRoute}
      />
    </div>
  );
}
