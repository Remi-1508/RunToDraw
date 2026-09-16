import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import LoadingModal from "./components/LoadingModal";
import Toast from "./components/Toast";
import { useTheme } from "./hooks/useTheme";
import { useRoutePlanner } from "./hooks/useRoutePlanner";
import {
  downloadGoogleMapsShortcut,
  downloadKML,
  downloadRouteGPX,
} from "./utils/routeExport";

// Plage de largeur autorisée pour la sidebar, et sa largeur par défaut.
const SIDEBAR_MIN = 340;
const SIDEBAR_MAX = 720;
const SIDEBAR_DEFAULT = 430;

const INITIAL_DRAWING = {
  mode: "shape",
  shape: "heart",
  text: "P2I",
};

/*
============================================================
App est le composant principal : il coordonne l'état de l'interface (thème,
sidebar, dessin demandé) et délègue l'extraction du graphe / la génération
d'itinéraires à useRoutePlanner.
============================================================
*/
export default function App() {
  const { theme, loadingTheme, toggleTheme } = useTheme();

  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = Number(localStorage.getItem("runtodraw-sidebar-width"));
    if (Number.isFinite(saved) && saved >= SIDEBAR_MIN && saved <= SIDEBAR_MAX) {
      return saved;
    }
    return SIDEBAR_DEFAULT;
  });
  const [isResizing, setIsResizing] = useState(false);

  const [center, setCenter] = useState(null);
  const [distanceKm, setDistanceKm] = useState(15);
  const [drawing, setDrawing] = useState(INITIAL_DRAWING);

  const [loadingLocation, setLoadingLocation] = useState(false);
  const [toast, setToast] = useState({ open: false, message: "", type: "success" });
  const toastTimerRef = useRef(null);

  function showToast(message, type = "success") {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);

    setToast({ open: true, message, type });

    toastTimerRef.current = setTimeout(() => {
      setToast((current) => ({ ...current, open: false }));
    }, 3500);
  }

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const {
    graphData,
    routePlan,
    selectedRouteId,
    setSelectedRouteId,
    showFullGraph,
    setShowFullGraph,
    busyState,
    generateRoutes,
    resetComputedGraph,
  } = useRoutePlanner({
    center,
    distanceKm,
    drawing,
    onSuccess: () => showToast("Les propositions d’itinéraires sont prêtes.", "success"),
    onError: () =>
      showToast(
        "Erreur pendant la génération des itinéraires. Vérifie la console et le terminal backend.",
        "error"
      ),
  });

  useEffect(() => {
    localStorage.setItem("runtodraw-sidebar-width", String(sidebarWidth));
  }, [sidebarWidth]);

  /*
  ============================================================
  Redimensionnement de la sidebar : le mouvement de la souris met à jour la
  largeur pendant le glissement, le relâchement arrête le mode redimensionnement.
  ============================================================
  */
  useEffect(() => {
    if (!isResizing) {
      document.body.classList.remove("app-resizing");
      return undefined;
    }

    document.body.classList.add("app-resizing");

    function handleMouseMove(event) {
      const viewportWidth = window.innerWidth;
      const maxAllowed = Math.min(SIDEBAR_MAX, viewportWidth - 420);
      const nextWidth = Math.min(
        Math.max(event.clientX, SIDEBAR_MIN),
        Math.max(SIDEBAR_MIN, maxAllowed)
      );
      setSidebarWidth(nextWidth);
    }

    function stopResize() {
      setIsResizing(false);
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopResize);
    window.addEventListener("mouseleave", stopResize);

    return () => {
      document.body.classList.remove("app-resizing");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", stopResize);
      window.removeEventListener("mouseleave", stopResize);
    };
  }, [isResizing]);

  function handlePickSuggestion(latlng) {
    setCenter(latlng);
    resetComputedGraph();
  }

  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      showToast("La géolocalisation n’est pas supportée par ton navigateur.", "error");
      return;
    }

    setLoadingLocation(true);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        await new Promise((resolve) => setTimeout(resolve, 520));
        setCenter([pos.coords.latitude, pos.coords.longitude]);
        resetComputedGraph();
        setLoadingLocation(false);
      },
      () => {
        setLoadingLocation(false);
        showToast("Impossible de récupérer la position actuelle.", "error");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }

  function handleExportRoute(exportType) {
    const route = routePlan?.routes?.find((item) => item.id === selectedRouteId);
    if (!route) return;

    const safeBaseName = route.label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    if (exportType === "gpx") {
      downloadRouteGPX(route, `runtodraw_${safeBaseName}.gpx`);
      showToast("Export GPX généré. C’est le plus simple pour Strava et beaucoup d’applis GPS.", "success");
      return;
    }

    if (exportType === "kml") {
      downloadKML(route, `runtodraw_${safeBaseName}.kml`);
      showToast("Export KML généré pour Google My Maps.", "success");
      return;
    }

    if (exportType === "google_maps") {
      downloadGoogleMapsShortcut(route);
      showToast("Le lien Google Maps a été ouvert dans un nouvel onglet.", "success");
    }
  }

  const radiusKm = distanceKm / 2;
  const selectedRoute = routePlan?.routes?.find((item) => item.id === selectedRouteId) ?? null;

  return (
    <div style={styles.page}>
      <LoadingModal
        open={busyState.open || loadingLocation || loadingTheme}
        progress={loadingLocation || loadingTheme ? 100 : busyState.progress}
        title={
          loadingTheme
            ? "Changement de thème"
            : loadingLocation
              ? "Localisation en cours"
              : busyState.title || "Préparation en cours"
        }
        kicker={
          loadingTheme
            ? "Notification"
            : loadingLocation
              ? "Position actuelle"
              : busyState.kicker || "RunToDraw"
        }
        description={
          loadingTheme
            ? "Changement de thème en cours…"
            : loadingLocation
              ? "On récupère ta position pour recentrer la carte de manière plus progressive…"
              : busyState.description || "Calcul en cours…"
        }
        indeterminate={loadingLocation || loadingTheme || busyState.indeterminate}
      />

      <aside style={{ ...styles.sidebarWrap, width: sidebarWidth, minWidth: sidebarWidth }}>
        <Sidebar
          theme={theme}
          center={center}
          showFullGraph={showFullGraph}
          onToggleShowFullGraph={() => graphData && setShowFullGraph((current) => !current)}
          canToggleGraph={!!graphData && !busyState.open}
          distanceKm={distanceKm}
          setDistanceKm={setDistanceKm}
          drawing={drawing}
          setDrawing={setDrawing}
          onUseMyLocation={handleUseMyLocation}
          onPickSuggestion={handlePickSuggestion}
          onGenerateRoutes={generateRoutes}
          canGenerate={!!center && !busyState.open}
          routePlan={routePlan}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
          onExportRoute={handleExportRoute}
        />
      </aside>

      <div
        style={styles.resizeHandleWrap}
        onMouseDown={() => setIsResizing(true)}
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
          themeLoading={loadingTheme}
          center={center}
          radiusKm={radiusKm}
          graphData={graphData}
          showFullGraph={showFullGraph}
          routePlan={routePlan}
          selectedRoute={selectedRoute}
        />
      </main>

      <Toast
        open={toast.open}
        message={toast.message}
        type={toast.type}
        onClose={() => setToast((current) => ({ ...current, open: false }))}
      />
    </div>
  );
}

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
