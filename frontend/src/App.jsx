import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { reverseGeocode } from "./api/geocoding";
import { DEFAULT_DISTANCE_KM, INITIAL_DRAWING, LONG_DISTANCE_CONFIRM_KM, MIN_DRAW_POINTS, STORAGE_KEYS } from "./config";
import LoadingModal from "./components/feedback/LoadingModal";
import Toast from "./components/feedback/Toast";
import MapView from "./components/map/MapView";
import Sidebar from "./components/sidebar/Sidebar";
import WelcomeScreen from "./components/welcome/WelcomeScreen";
import { useMapBackground } from "./hooks/useMapBackground";
import { useGeolocation } from "./hooks/useGeolocation";
import { useGraphPrefetch } from "./hooks/useGraphPrefetch";
import { useIsMobile } from "./hooks/useIsMobile";
import { useOverpassStatus } from "./hooks/useOverpassStatus";
import { useSheetSwipe } from "./hooks/useSheetSwipe";
import { useRouteEditor } from "./hooks/useRouteEditor";
import { useRouteExport } from "./hooks/useRouteExport";
import { useRoutePlanning } from "./hooks/useRoutePlanning";
import { useServerLimits } from "./hooks/useServerLimits";
import { useSidebarResize } from "./hooks/useSidebarResize";
import { useTheme } from "./hooks/useTheme";
import { useToast } from "./hooks/useToast";
import { requestNotificationPermissionOnce } from "./utils/notify";
import { buildShareUrl, parseShareParams } from "./utils/shareLink";
import { readStorage, writeStorage } from "./utils/storage";

// Composant racine : il assemble les hooks (thème, largeur de la barre, génération, export…)
// et répartit l'écran en deux zones, les contrôles à gauche et la carte à droite.
export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { neutralBackground, toggleNeutralBackground } = useMapBackground();
  const { sidebarWidth, startResize } = useSidebarResize();
  const { toast, showToast, hideToast } = useToast();
  const { maxDistanceKm } = useServerLimits();
  const serviceStatus = useOverpassStatus();

  // Lien de partage ouvert : on reprend ses réglages et on lance la génération (voir plus bas).
  const [sharedParams] = useState(() => parseShareParams(window.location.search));
  // Écran d'accueil : seulement à la première visite, et jamais si on arrive par un lien de partage.
  const [welcomeOpen, setWelcomeOpen] = useState(() => !sharedParams && !readStorage(STORAGE_KEYS.welcomeSeen));
  const closeWelcome = useCallback(() => {
    writeStorage(STORAGE_KEYS.welcomeSeen, "1");
    setWelcomeOpen(false);
  }, []);

  // Choix de l'utilisateur : point de départ, distance, dessin (forme ou texte).
  const [center, setCenter] = useState(sharedParams?.center ?? null);
  const [requestedDistanceKm, setDistanceKm] = useState(sharedParams?.distanceKm ?? DEFAULT_DISTANCE_KM);
  const [drawing, setDrawing] = useState(sharedParams?.drawing ?? INITIAL_DRAWING);
  // Mode « Choisir un point sur la carte » : le prochain clic sur la carte fixe le départ.
  const [pickingOnMap, setPickingOnMap] = useState(false);
  // Barre latérale ouverte ou repliée. Sur smartphone elle recouvre la carte (tiroir) : on la replie
  // quand on a besoin de voir la carte (choix d'un point, tracé généré).
  const isMobile = useIsMobile();
  const [panelOpen, setPanelOpen] = useState(true);
  // Sur smartphone, glisser l'en-tête du tiroir vers le bas le referme.
  const swipe = useSheetSwipe({ enabled: isMobile && panelOpen, onClose: () => setPanelOpen(false) });

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
  // `startLabel` : adresse affichée du départ ("" = aucun départ, null = adresse en cours de recherche).
  const resetPlanning = planning.reset;
  const [startLabel, setStartLabel] = useState(sharedParams ? null : "");
  const reverseRef = useRef(null);
  const chooseCenter = useCallback(
    (latlng, label) => {
      setCenter(latlng);
      resetPlanning();
      reverseRef.current?.abort();
      if (label) {
        setStartLabel(label);
        return;
      }
      // Position actuelle ou clic sur la carte : on cherche l'adresse correspondante.
      setStartLabel(null);
      const controller = new AbortController();
      reverseRef.current = controller;
      reverseGeocode(latlng[0], latlng[1], { signal: controller.signal })
        .then(setStartLabel)
        .catch(() => {});
    },
    [resetPlanning]
  );
  // Retire le point de départ choisi (et les résultats qui en dépendaient).
  const clearStart = useCallback(() => {
    reverseRef.current?.abort();
    setCenter(null);
    setStartLabel("");
    resetPlanning();
  }, [resetPlanning]);
  // Le choix sur la carte se termine dès qu'un point est posé ; Échap l'annule.
  const pickOnMap = useCallback(
    (latlng) => {
      chooseCenter(latlng);
      setPickingOnMap(false);
      setPanelOpen(true);
    },
    [chooseCenter]
  );
  const togglePickOnMap = useCallback(() => {
    setPickingOnMap((on) => !on);
    if (isMobile) setPanelOpen(false);
  }, [isMobile]);
  useEffect(() => {
    if (!pickingOnMap) return undefined;
    const onKeyDown = (event) => {
      if (event.key !== "Escape") return;
      setPickingOnMap(false);
      setPanelOpen(true);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [pickingOnMap]);
  const showError = useCallback((message) => showToast(message, "error"), [showToast]);
  const { locating, locate } = useGeolocation({ onPosition: chooseCenter, onError: showError });

  // Si le serveur annonce un maximum inférieur à la distance choisie, on la ramène à ce maximum.
  const distanceKm = Math.min(requestedDistanceKm, maxDistanceKm);
  // Le réseau routier se télécharge en arrière-plan pendant que la personne règle le reste (voir graphPrefetch.js).
  useGraphPrefetch({ center, distanceKm, drawing, enabled: !welcomeOpen && !planning.busy });

  // Lance la génération avec des réglages explicites (formulaire, exemple ou lien de partage).
  const generate = planning.generate;
  const startGeneration = useCallback(
    ({ center: [lat, lon], distanceKm: km, drawing: nextDrawing }) => {
      // Geste de la personne : le bon moment pour proposer les notifications de fin de génération.
      requestNotificationPermissionOnce();
      generate({ lat, lon, distanceKm: km, drawing: nextDrawing });
    },
    [generate]
  );

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

    startGeneration({ center, distanceKm, drawing });
  }

  // Lien de partage : une seule fois au chargement, on cherche l'adresse du départ puis on génère.
  const sharedStarted = useRef(false);
  useEffect(() => {
    if (!sharedParams || sharedStarted.current) return;
    sharedStarted.current = true;
    chooseCenter(sharedParams.center);
    startGeneration(sharedParams);
  }, [sharedParams, chooseCenter, startGeneration]);

  // Copie (ou partage, sur téléphone) le lien qui recalcule ce parcours.
  async function handleShare() {
    const context = planning.planContext;
    const url = buildShareUrl({
      center: context ? [context.lat, context.lon] : center,
      distanceKm: context?.distanceKm ?? distanceKm,
      drawing: context?.drawing ?? drawing,
    });
    if (!url) {
      showToast("Un dessin libre est trop long pour tenir dans un lien : exporte plutôt le fichier GPX.", "info");
      return;
    }
    try {
      if (navigator.share && isMobile) {
        await navigator.share({ title: "RunToDraw", text: "Un parcours à dessiner en courant", url });
        return;
      }
      await navigator.clipboard.writeText(url);
      showToast("Lien copié : il recalcule le même parcours.", "success");
    } catch (error) {
      if (error?.name !== "AbortError") showToast("Impossible de copier le lien.", "error");
    }
  }

  // Après une extraction, on affiche le rayon réellement téléchargé (calculé par le backend selon la
  // forme) ; avant, ou si la distance a changé depuis, l'estimation par défaut (distance / 2).
  const { graphData } = planning;
  const radiusKm = graphData && graphData.distanceKm === distanceKm ? graphData.radiusKm : distanceKm / 2;

  // Sur smartphone, dès qu'une nouvelle liste d'itinéraires arrive, le tiroir se replie pour montrer la carte.
  // (Ajustement d'état pendant le rendu, plutôt qu'un effet : voir la doc React « You Might Not Need an Effect ».)
  const [seenPlan, setSeenPlan] = useState(routePlan);
  if (routePlan !== seenPlan) {
    setSeenPlan(routePlan);
    if (routePlan && isMobile) setPanelOpen(false);
  }

  const waiting = Boolean(planning.busy) || locating;

  // Un dessin libre doit contenir assez de points, et un texte au moins un caractère ; les formes sont toujours prêtes.
  const drawingIsReady =
    drawing.mode === "custom"
      ? (drawing.points?.length ?? 0) >= MIN_DRAW_POINTS
      : drawing.mode !== "text" || Boolean(drawing.text?.trim());

  return (
    <div className="rtd-page">
      {welcomeOpen ? <WelcomeScreen theme={theme} onGuest={closeWelcome} /> : null}

      {/* Fenêtre d'attente : génération en cours ou recherche de la position. */}
      <LoadingModal
        open={waiting}
        title={locating ? "Localisation en cours" : planning.busy?.title || "Chargement en cours"}
        kicker={locating ? "Position actuelle" : "Chargement en cours"}
        description={locating ? "On récupère ta position…" : planning.busy?.description || "Calcul en cours…"}
        startedAt={locating ? undefined : planning.busy?.startedAt}
        estimateSeconds={locating ? undefined : planning.busy?.estimateSeconds}
        indeterminate
        onCancel={planning.busy && !locating ? planning.cancel : undefined}
      />

      <aside
        className={`rtd-sidebar${panelOpen ? "" : " is-closed"}`}
        style={{ "--sidebar-w": `${sidebarWidth}px` }}
        ref={swipe.ref}
        {...swipe.handlers}
        inert={!panelOpen}
        aria-label="Paramètres de l’itinéraire"
      >
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
          startLabel={startLabel}
          pickingOnMap={pickingOnMap}
          onTogglePickOnMap={togglePickOnMap}
          onClearStart={clearStart}
          onClosePanel={() => setPanelOpen(false)}
          onGenerateRoutes={handleGenerate}
          canGenerate={Boolean(center) && drawingIsReady && !planning.busy}
          routePlan={displayedPlan}
          selectedRouteId={planning.selectedRouteId}
          onSelectRoute={planning.setSelectedRouteId}
          onExportRoute={exportRoute}
          onClearRoute={planning.reset}
          onShareRoute={handleShare}
          serviceStatus={serviceStatus}
        />
      </aside>

      {/* Smartphone : pendant le choix du départ, le tiroir est replié ; ce bandeau explique quoi faire. */}
      {isMobile && pickingOnMap ? (
        <div className="rtd-pick-banner" role="status">
          <span>Touche la carte pour choisir le départ</span>
          <button
            type="button"
            onClick={() => {
              setPickingOnMap(false);
              setPanelOpen(true);
            }}
          >
            Annuler
          </button>
        </div>
      ) : null}

      {/* Poignée de redimensionnement entre la barre latérale et la carte. */}
      <div
        className={`rtd-resize${panelOpen ? "" : " is-hidden"}`}
        onMouseDown={startResize}
        role="separator"
        aria-orientation="vertical"
        aria-label="Redimensionner la sidebar"
        title="Glisser pour redimensionner"
      >
        <div className="rtd-resize-grip" />
      </div>

      <main className="rtd-map">
        <MapView
          theme={theme}
          onToggleTheme={toggleTheme}
          neutralBackground={neutralBackground}
          onToggleNeutralBackground={toggleNeutralBackground}
          center={center}
          radiusKm={radiusKm}
          selectedRoute={editor.route}
          editor={editor}
          panelOpen={panelOpen}
          onTogglePanel={() => setPanelOpen((open) => !open)}
          pickingOnMap={pickingOnMap}
          onPickCenter={pickOnMap}
        />
      </main>

      <Toast open={toast.open} message={toast.message} type={toast.type} onClose={hideToast} />
    </div>
  );
}
