import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import LoadingModal from "./components/LoadingModal";
import Toast from "./components/Toast";
import { fetchGraphForRun } from "./services/osmGraph";
import { planRoutes } from "./services/routePlannerApi";
import {
  downloadGoogleMapsShortcut,
  downloadKML,
  downloadRouteGPX,
} from "./utils/routeExport";

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
  This option controls whether the raw graph should be shown on the map.
  It is also restored from localStorage.

  FR:
  Cette option contrôle si le graphe brut doit être affiché sur la carte.
  Elle est elle aussi restaurée depuis le localStorage.
  */
  const [showFullGraph, setShowFullGraph] = useState(() => {
    const saved = localStorage.getItem("runtodraw-show-full-graph");
    return saved === null ? false : saved === "true";
  });

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
  - graph payload sent to the backend
  - generated route plan
  - currently selected route

  FR:
  États des données calculées :
  - graphe extrait
  - payload du graphe envoyé au backend
  - plan d’itinéraires généré
  - itinéraire actuellement sélectionné
  */
  const [graphData, setGraphData] = useState(null);
  const [graphJsonPayload, setGraphJsonPayload] = useState(null);
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
  - chargement du changement de thème
  - modal globale d’activité pour l’extraction / génération
  */
  const [loadingLocation, setLoadingLocation] = useState(false);
  const [loadingTheme, setLoadingTheme] = useState(false);

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
  const themeTimeoutsRef = useRef([]);
  const busyIntervalRef = useRef(null);

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
  Save the graph visibility preference whenever it changes.

  FR:
  Sauvegarde la préférence d’affichage du graphe à chaque changement.
  */
  useEffect(() => {
    localStorage.setItem("runtodraw-show-full-graph", String(showFullGraph));
  }, [showFullGraph]);

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
      themeTimeoutsRef.current.forEach(clearTimeout);
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
      if (busyIntervalRef.current) clearInterval(busyIntervalRef.current);
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

  /*
  EN:
  Starts a short visual transition before switching theme.
  This keeps the effect a bit smoother for the user.

  FR:
  Lance une petite transition visuelle avant de changer de thème.
  Cela rend l’effet un peu plus fluide pour l’utilisateur.
  */
  function toggleTheme() {
    if (loadingTheme) return;

    setLoadingTheme(true);
    themeTimeoutsRef.current.forEach(clearTimeout);
    themeTimeoutsRef.current = [
      setTimeout(() => {
        setTheme((current) => (current === "light" ? "dark" : "light"));
      }, 260),
      setTimeout(() => {
        setLoadingTheme(false);
      }, 980),
    ];
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
    setGraphJsonPayload(null);
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
      async (pos) => {
        await new Promise((resolve) => setTimeout(resolve, 520));
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

  /*
  EN:
  Opens the global loading modal and starts a fake progressive bar
  when the real progress cannot be tracked precisely.

  FR:
  Ouvre la modal globale de chargement et lance une barre de progression simulée
  quand la progression réelle ne peut pas être suivie précisément.
  */
  function startBusy({ title, kicker, description, indeterminate = false }) {
    if (busyIntervalRef.current) clearInterval(busyIntervalRef.current);

    setBusyState({
      open: true,
      progress: 0,
      title,
      kicker,
      description,
      indeterminate,
    });

    if (!indeterminate) {
      busyIntervalRef.current = setInterval(() => {
        setBusyState((current) => ({
          ...current,
          progress: Math.min(
            92,
            current.progress + Math.max(0.8, (92 - current.progress) * 0.06)
          ),
        }));
      }, 140);
    }
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

  /*
  EN:
  Finishes the loading modal smoothly by pushing progress to 100,
  waiting a bit, then closing it.

  FR:
  Termine proprement la modal de chargement en poussant la progression à 100,
  en attendant un peu, puis en la fermant.
  */
  async function stopBusy() {
    if (busyIntervalRef.current) clearInterval(busyIntervalRef.current);

    setBusyState((current) => ({
      ...current,
      progress: 100,
    }));

    await new Promise((resolve) => setTimeout(resolve, 180));

    setBusyState((current) => ({
      ...current,
      open: false,
      progress: 0,
    }));
  }

  /*
  ============================================================
  EN:
  Main route generation workflow.

  Steps:
  1) extract the graph from the backend
  2) validate the graph payload
  3) ask the backend to generate route proposals
  4) store the results and auto-select the first route
  5) show a success or error feedback

  This is the central async action of the frontend.

  FR:
  Workflow principal de génération d’itinéraires.

  Étapes :
  1) extraire le graphe depuis le backend
  2) valider le payload du graphe
  3) demander au backend de générer les propositions
  4) stocker les résultats et sélectionner automatiquement le premier itinéraire
  5) afficher un retour de succès ou d’erreur

  C’est l’action asynchrone centrale du frontend.
  ============================================================
  */
  async function handleGenerateRoutes() {
    if (!center) return;

    const [lat, lng] = center;

    try {
      startBusy({
        title: "Préparation de l’itinéraire",
        kicker: "Étape 1/3",
        description: "Extraction du graphe OpenStreetMap…",
      });

      const nextGraph = await fetchGraphForRun({
        lat,
        lon: lng,
        distanceKm,
      });

      const payload = nextGraph.graphPayload;

      if (!payload || !payload.nodes || !payload.edges) {
        throw new Error("Graph payload invalide reçu depuis le backend.");
      }

      setGraphData(nextGraph);
      setGraphJsonPayload(payload);
      setRoutePlan(null);
      setSelectedRouteId(null);
      setShowFullGraph(false);

      updateBusy({
        kicker: "Étape 2/3",
        description:
          "Analyse de la forme demandée et recherche des meilleures trajectoires…",
        progress: 35,
      });

      const nextPlan = await planRoutes({
        graphPayload: payload,
        distanceKm,
        drawing,
      });

      updateBusy({
        kicker: "Étape 3/3",
        description:
          "Mise en forme des propositions, calcul des distances et préparation des exports GPS…\nSur une grosse zone ou un mot long, ce calcul peut monter vers ~15 minutes côté projet.",
        progress: 88,
      });

      setRoutePlan(nextPlan);
      const preferred = nextPlan?.routes?.[0]?.id ?? null;
      setSelectedRouteId(preferred);

      await stopBusy();
      showToast("Les propositions d’itinéraires sont prêtes.", "success");
    } catch (error) {
      console.error("handleGenerateRoutes error:", error);
      setRoutePlan(null);
      setSelectedRouteId(null);
      await stopBusy();
      showToast(
        "Erreur pendant la génération des itinéraires. Vérifie la console et le terminal backend.",
        "error"
      );
    }
  }

  /*
  ============================================================
  EN:
  Handles export for the currently selected route.

  Supported exports:
  - GPX
  - KML
  - Google Maps shortcut

  The file name is cleaned so it remains valid and readable.

  FR:
  Gère l’export de l’itinéraire actuellement sélectionné.

  Exports pris en charge :
  - GPX
  - KML
  - lien Google Maps

  Le nom de fichier est nettoyé pour rester valide et lisible.
  ============================================================
  */
  function handleExportRoute(exportType) {
    const route = routePlan?.routes?.find((item) => item.id === selectedRouteId);
    if (!route) return;

    const safeBaseName = route.label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    if (exportType === "gpx") {
      downloadRouteGPX(route, `runtodraw_${safeBaseName}.gpx`);
      showToast(
        "Export GPX généré. C’est le plus simple pour Strava et beaucoup d’applis GPS.",
        "success"
      );
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
  const radiusKm = distanceKm / 2;
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
      - theme switching

      FR:
      Modal globale de chargement.
      Elle peut refléter :
      - la génération d’itinéraires
      - le chargement de la position
      - le changement de thème
      */}
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
          showFullGraph={showFullGraph}
          onToggleShowFullGraph={() =>
            graphData && setShowFullGraph((current) => !current)
          }
          canToggleGraph={!!graphData && !busyState.open}
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
          themeLoading={loadingTheme}
          center={center}
          radiusKm={radiusKm}
          graphData={graphData}
          showFullGraph={showFullGraph}
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