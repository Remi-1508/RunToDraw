import { useCallback, useMemo, useState } from "react";
import { DEFAULT_DISTANCE_KM, INITIAL_DRAWING, LONG_DISTANCE_CONFIRM_KM, MIN_DRAW_POINTS } from "./config";
import LoadingModal from "./components/feedback/LoadingModal";
import Toast from "./components/feedback/Toast";
import MapView from "./components/map/MapView";
import Sidebar from "./components/sidebar/Sidebar";
import { useMapBackground } from "./hooks/useMapBackground";
import { useGeolocation } from "./hooks/useGeolocation";
import { useRouteEditor } from "./hooks/useRouteEditor";
import { useRouteExport } from "./hooks/useRouteExport";
import { useRoutePlanning } from "./hooks/useRoutePlanning";
import { useServerLimits } from "./hooks/useServerLimits";
import { useSidebarResize } from "./hooks/useSidebarResize";
import { useTheme } from "./hooks/useTheme";
import { useToast } from "./hooks/useToast";

// Composant racine : il assemble les hooks (thème, largeur de la barre, génération, export…)
// et répartit l'écran en deux zones, les contrôles à gauche et la carte à droite.
export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { neutralBackground, toggleNeutralBackground } = useMapBackground();
  const { sidebarWidth, startResize } = useSidebarResize();
  const { toast, showToast, hideToast } = useToast();
  const { maxDistanceKm } = useServerLimits();

  // Choix de l'utilisateur : point de départ, distance, dessin (forme ou texte).
  const [center, setCenter] = useState(null);
  const [requestedDistanceKm, setDistanceKm] = useState(DEFAULT_DISTANCE_KM);
  const [drawing, setDrawing] = useState(INITIAL_DRAWING);

  const planning = useRoutePlanning({ showToast });
  // Édition manuelle du tracé sur la carte : `editor.route` est l'itinéraire choisi, avec ses modifications.
  const editor = useRouteEditor({
    routePlan: planning.routePlan,
    selectedRoute: planning.selectedRoute,
    planContext: planning.planContext,
    showToast,
  });
  const exportRoute = useRouteExport({ selectedRoute: editor.route, showToast });

  // Liste de propositions affichée dans la barre latérale : l'itinéraire modifié remplace son original
  // (distance à jour, exports sur le tracé modifié).
  const { routePlan } = planning;
  const displayedPlan = useMemo(() => {
    if (!routePlan || !editor.route) return routePlan;
    return { ...routePlan, routes: routePlan.routes.map((r) => (r.id === editor.route.id ? editor.route : r)) };
  }, [routePlan, editor.route]);

  // Changer de point de départ efface les résultats précédents.
  const resetPlanning = planning.reset;
  const chooseCenter = useCallback(
    (latlng) => {
      setCenter(latlng);
      resetPlanning();
    },
    [resetPlanning]
  );
  const showError = useCallback((message) => showToast(message, "error"), [showToast]);
  const { locating, locate } = useGeolocation({ onPosition: chooseCenter, onError: showError });

  // Si le serveur annonce un maximum inférieur à la distance choisie, on la ramène à ce maximum.
  const distanceKm = Math.min(requestedDistanceKm, maxDistanceKm);

  function handleGenerate() {
    if (!center) return;

    if (
      distanceKm > LONG_DISTANCE_CONFIRM_KM &&
      !window.confirm(
        `Tu demandes ${distanceKm} km. Sur une telle distance, le téléchargement du réseau routier ` +
          "peut prendre plusieurs minutes. Continuer ?"
      )
    ) {
      return;
    }

    const [lat, lon] = center;
    planning.generate({ lat, lon, distanceKm, drawing });
  }

  // Après une extraction, on affiche le rayon réellement téléchargé (calculé par le backend selon la
  // forme) ; avant, ou si la distance a changé depuis, l'estimation par défaut (distance / 2).
  const { graphData } = planning;
  const radiusKm = graphData && graphData.distanceKm === distanceKm ? graphData.radiusKm : distanceKm / 2;

  const waiting = Boolean(planning.busy) || locating;

  // Un dessin libre doit contenir assez de points pour être exploitable ; les autres modes sont toujours prêts.
  const drawingIsReady = drawing.mode !== "custom" || (drawing.points?.length ?? 0) >= MIN_DRAW_POINTS;

  return (
    <div style={styles.page}>
      {/* Fenêtre d'attente : génération en cours ou recherche de la position. */}
      <LoadingModal
        open={waiting}
        title={locating ? "Localisation en cours" : "Préparation de l’itinéraire"}
        kicker={locating ? "Position actuelle" : planning.busy?.kicker || "RunToDraw"}
        description={locating ? "On récupère ta position…" : planning.busy?.description || "Calcul en cours…"}
        indeterminate
        onCancel={planning.busy && !locating ? planning.cancel : undefined}
      />

      <aside style={{ ...styles.sidebarWrap, width: sidebarWidth, minWidth: sidebarWidth }}>
        <Sidebar
          theme={theme}
          center={center}
          distanceKm={distanceKm}
          setDistanceKm={setDistanceKm}
          maxDistanceKm={maxDistanceKm}
          drawing={drawing}
          setDrawing={setDrawing}
          onUseMyLocation={locate}
          onPickSuggestion={chooseCenter}
          onGenerateRoutes={handleGenerate}
          canGenerate={Boolean(center) && drawingIsReady && !planning.busy}
          routePlan={displayedPlan}
          selectedRouteId={planning.selectedRouteId}
          onSelectRoute={planning.setSelectedRouteId}
          onExportRoute={exportRoute}
        />
      </aside>

      {/* Poignée de redimensionnement entre la barre latérale et la carte. */}
      <div
        style={styles.resizeHandleWrap}
        onMouseDown={startResize}
        role="separator"
        aria-orientation="vertical"
        aria-label="Redimensionner la sidebar"
        title="Glisser pour redimensionner"
      >
        <div style={styles.resizeHandle} />
      </div>

      <main style={styles.mapArea}>
        <MapView
          theme={theme}
          onToggleTheme={toggleTheme}
          neutralBackground={neutralBackground}
          onToggleNeutralBackground={toggleNeutralBackground}
          center={center}
          radiusKm={radiusKm}
          selectedRoute={editor.route}
          editor={editor}
          onPickCenter={chooseCenter}
        />
      </main>

      <Toast open={toast.open} message={toast.message} type={toast.type} onClose={hideToast} />
    </div>
  );
}

// Mise en page : la page est divisée en deux zones, les contrôles à gauche et la carte à droite.
const styles = {
  page: {
    height: "100vh",
    width: "100vw",
    display: "flex",
    background: "var(--bg)",
  },

  sidebarWrap: {
    height: "100vh",
    overflow: "auto",
    borderRight: "1px solid var(--border)",
    background: "var(--bg-elevated)",
  },

  resizeHandleWrap: {
    width: 12,
    minWidth: 12,
    height: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    cursor: "col-resize",
    background: "var(--bg)",
  },

  resizeHandle: {
    width: 4,
    height: 66,
    borderRadius: 999,
    background: "var(--border-strong)",
  },

  mapArea: {
    flex: 1,
    height: "100vh",
    padding: 12,
    minWidth: 0,
  },
};
