import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import LoadingModal from "./components/LoadingModal";
import Toast from "./components/Toast";
import { fetchGraphForRun } from "./services/osmGraph";
import { planRoutes } from "./services/routePlannerApi";
import { downloadKML, downloadRouteGPX } from "./utils/routeExport";

// Au-delà, on demande confirmation : le téléchargement du réseau routier devient long.
const LONG_DISTANCE_CONFIRM_KM = 50;

/*
============================================================
EN:
These constants define the allowed width range of the sidebar,
and its default width when the app starts.

FR:
Ces constantes définissent la plage de largeur autorisée
pour la sidebar, ainsi que sa largeur par défaut au lancement.
============================================================
*/
const SIDEBAR_MIN = 340;
const SIDEBAR_MAX = 720;
const SIDEBAR_DEFAULT = 430;

/*
============================================================
EN:
This is the initial drawing state used when the app loads.

By default:
- the mode is "shape"
- the selected shape is a heart
- the default text is "P2I"

FR:
Ceci est l’état initial du dessin utilisé au chargement de l’application.

Par défaut :
- le mode est "shape"
- la forme sélectionnée est un cœur
- le texte par défaut est "P2I"
============================================================
*/
const INITIAL_DRAWING = {
  mode: "shape",
  shape: "heart",
  text: "P2I",
};

/*
============================================================
EN:
App is the main component of the project.

It coordinates the full workflow:
- UI state
- map state
- loading states
- graph extraction
- route generation
- route export
- theme switching

This file is the main controller of the frontend.

FR:
App est le composant principal du projet.

Il coordonne tout le workflow :
- l’état de l’interface
- l’état de la carte
- les états de chargement
- l’extraction du graphe
- la génération des itinéraires
- l’export des trajets
- le changement de thème

Ce fichier est le contrôleur principal du frontend.
============================================================
*/
export default function App() {
  /*
  EN:
  Theme state is restored from localStorage if available.
  This lets the app remember the user’s previous choice.

  FR:
  L’état du thème est restauré depuis le localStorage si possible.
  Cela permet à l’application de se souvenir du choix précédent de l’utilisateur.
  */
  const [theme, setTheme] = useState(
    () => localStorage.getItem("runtodraw-theme") || "light"
  );


  /*
  EN:
  The sidebar width can be resized by the user.
  We restore the previous width if it exists and remains valid.

  FR:
  La largeur de la sidebar peut être redimensionnée par l’utilisateur.
  On restaure la largeur précédente si elle existe et reste valide.
  */
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = Number(localStorage.getItem("runtodraw-sidebar-width"));
    if (
      Number.isFinite(saved) &&
      saved >= SIDEBAR_MIN &&
      saved <= SIDEBAR_MAX
    ) {
      return saved;
    }
    return SIDEBAR_DEFAULT;
  });

  /*
  EN:
  Main interactive states of the application:
  - sidebar resize state
  - selected center
  - chosen distance
  - chosen drawing mode and content

  FR:
  États interactifs principaux de l’application :
  - état du redimensionnement de la sidebar
  - centre sélectionné
  - distance choisie
  - mode de dessin et contenu choisis
  */
  const [isResizing, setIsResizing] = useState(false);
  const [center, setCenter] = useState(null);
  const [distanceKm, setDistanceKm] = useState(15);
  const [drawing, setDrawing] = useState(INITIAL_DRAWING);

  /*
  EN:
  Computed data states:
  - extracted graph
  - generated route plan
  - currently selected route

  FR:
  États des données calculées :
  - graphe extrait
  - plan d’itinéraires généré
  - itinéraire actuellement sélectionné
  */
  const [graphData, setGraphData] = useState(null);
  const [routePlan, setRoutePlan] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);

  /*
  EN:
  Dedicated loading states:
  - location loading
  - theme transition loading
  - global busy modal for graph / route generation

  FR:
  États de chargement dédiés :
  - chargement de la position
  - modal globale d’activité pour l’extraction / génération
  */
  const [loadingLocation, setLoadingLocation] = useState(false);

  const [busyState, setBusyState] = useState({
    open: false,
    progress: 0,
    title: "",
    kicker: "",
    description: "",
    indeterminate: false,
  });

  /*
  EN:
  Toast state used for small success / error messages.

  FR:
  État du toast utilisé pour les petits messages de succès / erreur.
  */
  const [toast, setToast] = useState({
    open: false,
    message: "",
    type: "success",
  });

  /*
  EN:
  Refs are used here to keep track of timers and intervals
  without triggering re-renders.

  FR:
  Les refs sont utilisées ici pour conserver des timers et intervalles
  sans provoquer de re-render.
  */
  const toastTimerRef = useRef(null);

  /*
  EN:
  Save the current theme and apply it to the document root.
  This allows CSS variables to react to the selected theme.

  FR:
  Sauvegarde le thème actuel et l’applique à la racine du document.
  Cela permet aux variables CSS de réagir au thème sélectionné.
  */
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("runtodraw-theme", theme);
  }, [theme]);

  /*
  EN:
  Save the sidebar width whenever it changes.

  FR:
  Sauvegarde la largeur de la sidebar à chaque changement.
  */
  useEffect(() => {
    localStorage.setItem("runtodraw-sidebar-width", String(sidebarWidth));
  }, [sidebarWidth]);


  /*
  EN:
  Cleanup effect.
  When the component unmounts, all pending timers and intervals are cleared.

  FR:
  Effet de nettoyage.
  Lorsque le composant est démonté, tous les timers et intervalles restants sont supprimés.
  */
  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  /*
  ============================================================
  EN:
  Sidebar resize behavior.

  While the user is dragging the resize handle:
  - mouse movement updates the sidebar width
  - mouse release stops the resize mode

  FR:
  Gestion du redimensionnement de la sidebar.

  Pendant que l’utilisateur déplace la poignée :
  - le mouvement de la souris met à jour la largeur
  - le relâchement arrête le mode redimensionnement
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

  // Bascule clair / sombre, immédiatement.
  function toggleTheme() {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }

  /*
  EN:
  Displays a toast and automatically hides it after a short delay.

  FR:
  Affiche un toast puis le masque automatiquement après un court délai.
  */
  function showToast(message, type = "success") {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);

    setToast({
      open: true,
      message,
      type,
    });

    toastTimerRef.current = setTimeout(() => {
      setToast((current) => ({ ...current, open: false }));
    }, 3500);
  }

  /*
  EN:
  Clears all computed route/graph data.
  This is useful when the selected location changes.

  FR:
  Réinitialise toutes les données calculées liées au graphe et aux itinéraires.
  C’est utile quand la localisation choisie change.
  */
  function resetComputedGraph() {
    setGraphData(null);
    setRoutePlan(null);
    setSelectedRouteId(null);
    setShowFullGraph(false);
  }

  /*
  EN:
  Called when the user selects a suggestion from the address list.

  FR:
  Appelée quand l’utilisateur choisit une suggestion dans la liste d’adresses.
  */
  function handlePickSuggestion(latlng) {
    setCenter(latlng);
    resetComputedGraph();
  }

  /*
  ============================================================
  EN:
  Gets the user’s current location using the browser geolocation API.

  If successful:
  - the map center is updated
  - computed graph data is reset

  If it fails:
  - an error toast is displayed

  FR:
  Récupère la position actuelle de l’utilisateur via l’API de géolocalisation du navigateur.

  En cas de succès :
  - le centre de la carte est mis à jour
  - les données calculées sont réinitialisées

  En cas d’échec :
  - un toast d’erreur est affiché
  ============================================================
  */
  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      showToast("La géolocalisation n’est pas supportée par ton navigateur.", "error");
      return;
    }

    setLoadingLocation(true);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCenter([lat, lng]);
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

  // Ouvre la fenêtre de chargement. La durée réelle (Overpass surtout) n'est pas
  // mesurable, donc la barre est indéterminée plutôt qu'une progression inventée.
  function startBusy({ title, kicker, description }) {
    setBusyState({
      open: true,
      progress: 0,
      title,
      kicker,
      description,
      indeterminate: true,
    });
  }

  /*
  EN:
  Updates part of the busy modal state without replacing everything.

  FR:
  Met à jour une partie de l’état de la modal de chargement sans tout remplacer.
  */
  function updateBusy(patch) {
    setBusyState((current) => ({ ...current, ...patch }));
  }

  function stopBusy() {
    setBusyState((current) => ({ ...current, open: false, progress: 0 }));
  }

  /*
  ============================================================
  EN:
  Main route generation workflow.

  Steps:
  1) extract the graph from the backend
  2) ask the backend to generate route proposals (the graph stays cached on the server)
  3) store the results and auto-select the first route
  4) show a success or error feedback

  This is the central async action of the frontend.

  FR:
  Workflow principal de génération d’itinéraires.

  Étapes :
  1) extraire le graphe depuis le backend
  2) demander au backend de générer les propositions (le graphe reste en cache sur le serveur)
  3) stocker les résultats et sélectionner automatiquement le premier itinéraire
  4) afficher un retour de succès ou d’erreur

  C’est l’action asynchrone centrale du frontend.
  ============================================================
  */
  async function handleGenerateRoutes() {
    if (!center) return;

    const [lat, lng] = center;

    if (
      distanceKm > LONG_DISTANCE_CONFIRM_KM &&
      !window.confirm(
        `Tu demandes ${distanceKm} km. Sur une telle distance, le téléchargement du réseau routier ` +
          "peut prendre plusieurs minutes. Continuer ?"
      )
    ) {
      return;
    }

    try {
      startBusy({
        title: "Préparation de l’itinéraire",
        kicker: "Étape 1/2",
        description: "Extraction du graphe OpenStreetMap…",
      });

      const nextGraph = await fetchGraphForRun({
        lat,
        lon: lng,
        distanceKm,
        drawing,
      });

      setGraphData(nextGraph);
      setRoutePlan(null);
      setSelectedRouteId(null);

      updateBusy({
        kicker: "Étape 2/2",
        description:
          "Analyse de la forme demandée et recherche des meilleures trajectoires…",
      });

      const nextPlan = await planRoutes({
        lat,
        lon: lng,
        distanceKm,
        drawing,
      });


      setRoutePlan(nextPlan);
      const preferred = nextPlan?.routes?.[0]?.id ?? null;
      setSelectedRouteId(preferred);

      stopBusy();
      showToast("Les propositions d’itinéraires sont prêtes.", "success");
    } catch (error) {
      console.error("handleGenerateRoutes error:", error);
      setRoutePlan(null);
      setSelectedRouteId(null);
      stopBusy();
      showToast(
        error?.message
          ? `Erreur pendant la génération : ${error.message}`
          : "Erreur pendant la génération des itinéraires. Vérifie la console et le terminal backend.",
        "error"
      );
    }
  }

  /*
  Export de l'itinéraire sélectionné (GPX ou KML). Pour un mot en lettres séparées,
  `segmentIndex` désigne la lettre à exporter seule en GPX.
  */
  function handleExportRoute(exportType, segmentIndex = null) {
    const route = routePlan?.routes?.find((item) => item.id === selectedRouteId);
    if (!route) return;

    const safeBaseName = route.label
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    try {
      if (exportType === "gpx") {
        const segment = segmentIndex === null ? null : route.segments?.[segmentIndex];
        const suffix = segment
          ? `_lettre-${String(segment.label).toLowerCase()}-${segmentIndex + 1}`
          : "";
        downloadRouteGPX(route, `runtodraw_${safeBaseName}${suffix}.gpx`, segmentIndex);
        showToast(
          segment
            ? `GPX de la lettre ${segment.label} généré.`
            : "Export GPX généré. C’est le plus simple pour Strava et beaucoup d’applis GPS.",
          "success"
        );
        return;
      }

      if (exportType === "kml") {
        downloadKML(route, `runtodraw_${safeBaseName}.kml`);
        showToast("Export KML généré pour Google My Maps.", "success");
      }
    } catch (error) {
      showToast(error?.message ?? "Export impossible.", "error");
    }
  }

  /*
  EN:
  Derived values used by child components:
  - extraction radius displayed on the map
  - currently selected route object

  FR:
  Valeurs dérivées utilisées par les composants enfants :
  - rayon d’extraction affiché sur la carte
  - objet de l’itinéraire actuellement sélectionné
  */
  // Après une extraction, on affiche le rayon réellement téléchargé (calculé par le backend
  // selon la forme) ; avant, ou si la distance a changé depuis, l'ancienne estimation (distance / 2).
  const radiusKm =
    graphData && graphData.distanceKm === distanceKm ? graphData.radiusKm : distanceKm / 2;
  const selectedRoute =
    routePlan?.routes?.find((item) => item.id === selectedRouteId) ?? null;

  return (
    <div style={styles.page}>
      {/*
      EN:
      Global loading modal.
      It can reflect:
      - route generation
      - location loading

      FR:
      Modal globale de chargement.
      Elle peut refléter :
      - la génération d’itinéraires
      - le chargement de la position
      */}
      <LoadingModal
        open={busyState.open || loadingLocation}
        progress={busyState.progress}
        title={loadingLocation ? "Localisation en cours" : busyState.title || "Préparation en cours"}
        kicker={loadingLocation ? "Position actuelle" : busyState.kicker || "RunToDraw"}
        description={
          loadingLocation
            ? "On récupère ta position…"
            : busyState.description || "Calcul en cours…"
        }
        indeterminate
      />

      {/*
      EN:
      Left sidebar containing the full control flow.

      FR:
      Sidebar de gauche contenant tout le parcours de contrôle.
      */}
      <aside
        style={{
          ...styles.sidebarWrap,
          width: sidebarWidth,
          minWidth: sidebarWidth,
        }}
      >
        <Sidebar
          theme={theme}
          center={center}
          distanceKm={distanceKm}
          setDistanceKm={setDistanceKm}
          drawing={drawing}
          setDrawing={setDrawing}
          onUseMyLocation={handleUseMyLocation}
          onPickSuggestion={handlePickSuggestion}
          onGenerateRoutes={handleGenerateRoutes}
          canGenerate={!!center && !busyState.open}
          routePlan={routePlan}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
          onExportRoute={handleExportRoute}
        />
      </aside>

      {/*
      EN:
      Resize handle placed between sidebar and map.

      FR:
      Poignée de redimensionnement placée entre la sidebar et la carte.
      */}
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

      {/*
      EN:
      Main map area.

      FR:
      Zone principale de la carte.
      */}
      <main style={styles.mapArea}>
        <MapView
          theme={theme}
          onToggleTheme={toggleTheme}
          center={center}
          radiusKm={radiusKm}
          graphData={graphData}
          routePlan={routePlan}
          selectedRoute={selectedRoute}
        />
      </main>

      {/*
      EN:
      Floating toast for quick user feedback.

      FR:
      Toast flottant pour les retours rapides à l’utilisateur.
      */}
      <Toast
        open={toast.open}
        message={toast.message}
        type={toast.type}
        onClose={() => setToast((current) => ({ ...current, open: false }))}
      />
    </div>
  );
}

/*
============================================================
EN:
Main layout styles:
- global page
- sidebar wrapper
- resize handle
- map area

The idea is to keep the application split into two main zones:
controls on the left, map on the right.

FR:
Styles principaux de mise en page :
- page globale
- conteneur de sidebar
- poignée de redimensionnement
- zone de carte

L’idée est de garder l’application divisée en deux grandes zones :
les contrôles à gauche, la carte à droite.
============================================================
*/
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