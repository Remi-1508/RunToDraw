import L from "leaflet";
import { Circle, MapContainer, Marker, Polyline, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { Fragment, useEffect, useId, useMemo, useRef, useState } from "react";
import { DEFAULT_CENTER } from "../../config";
import { boundsFromCenterRadiusKm } from "../../utils/geo";
import RouteEditLayer from "./RouteEditLayer";
import RouteEditToolbar from "./RouteEditToolbar";

// FitToRadius ajuste automatiquement la vue de la carte
// à la zone de course choisie quand le centre ou le rayon change.
function FitToRadius({ center, radiusKm }) {
  const map = useMap();

  useEffect(() => {
    if (!center) return;
    const [lat, lng] = center;
    const bounds = boundsFromCenterRadiusKm(lat, lng, radiusKm);
    map.fitBounds(bounds, { padding: [30, 30] });
  }, [center, radiusKm, map]);

  return null;
}

// FitToRoute recentre la carte sur l’itinéraire actuellement sélectionné.
// C’est utile une fois que l’utilisateur choisit un trajet parmi les résultats.
// Le recadrage n'a lieu que lorsqu'on change d'itinéraire (id), jamais après une modification manuelle :
// sinon la carte bougerait sous les doigts de l'utilisateur à chaque point déplacé.
function FitToRoute({ selectedRoute }) {
  const map = useMap();
  const routeId = selectedRoute?.id;
  const routeRef = useRef(selectedRoute);
  // Mise à jour dans un effet (déclaré avant celui du recadrage, donc exécuté avant lui).
  useEffect(() => {
    routeRef.current = selectedRoute;
  });

  useEffect(() => {
    const route = routeRef.current;
    if (!route?.segments?.length) return;
    const allPoints = route.segments.flatMap((segment) => segment.points || []);
    if (allPoints.length < 2) return;
    map.fitBounds(allPoints, { padding: [45, 45] });
  }, [routeId, map]);

  return null;
}

// Petit bouton flottant de la carte (icône + libellé). `pressed` sert aux boutons à bascule.
// `disabledReason` : quand il est renseigné, le bouton est grisé et ce texte explique pourquoi.
// On utilise aria-disabled plutôt que disabled pour que le bouton reste atteignable au clavier
// et que son message soit lu / affiché au survol, au focus et au clic.
function MapControl({ icon, label, onClick, pressed, disabledReason }) {
  const [hintOpen, setHintOpen] = useState(false);
  const disabled = Boolean(disabledReason);
  const hintId = useId();

  return (
    <div
      style={styles.controlWrap}
      onMouseEnter={() => setHintOpen(true)}
      onMouseLeave={() => setHintOpen(false)}
      onFocus={() => setHintOpen(true)}
      onBlur={() => setHintOpen(false)}
    >
      <button
        type="button"
        onClick={disabled ? () => setHintOpen(true) : onClick}
        style={{
          ...styles.control,
          ...(pressed ? styles.controlPressed : null),
          ...(disabled ? styles.controlDisabled : null),
        }}
        aria-pressed={disabled ? undefined : pressed}
        aria-disabled={disabled}
        aria-describedby={disabled ? hintId : undefined}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          {icon}
        </svg>
        <span style={styles.controlText}>{label}</span>
      </button>
      {disabled && hintOpen ? (
        <div id={hintId} role="status" style={styles.controlHint}>
          {disabledReason}
        </div>
      ) : null}
    </div>
  );
}

const ICON_SUN = (
  <>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" />
  </>
);
const ICON_MOON = <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />;
const ICON_LAYERS = (
  <>
    <path d="M12 3l9 5-9 5-9-5z" />
    <path d="M3 13l9 5 9-5" />
  </>
);

// NeutralBackground applique (ou retire) la classe CSS qui remplace la carte par un aplat uni.
// On passe par le conteneur Leaflet car MapContainer ne met pas à jour ses props après sa création.
function NeutralBackground({ neutral }) {
  const map = useMap();
  useEffect(() => {
    map.getContainer().classList.toggle("map-neutral", neutral);
  }, [map, neutral]);
  return null;
}

// Un clic sur la carte fixe le point de départ, uniquement quand l'utilisateur a choisi « Choisir un point
// sur la carte » dans la barre latérale ; le curseur en croix indique que la carte attend ce clic.
function PickCenter({ onPick, enabled }) {
  const map = useMap();
  useMapEvents({
    click(event) {
      if (enabled && onPick) onPick([event.latlng.lat, event.latlng.lng]);
    },
  });
  useEffect(() => {
    map.getContainer().classList.toggle("map-pickable", Boolean(enabled && onPick));
  }, [map, enabled, onPick]);
  return null;
}

// Marqueur de départ : un simple point cerclé de blanc. Il ne porte volontairement aucune étiquette,
// car une pastille de texte posée sur la carte masquait une partie du dessin (le nom s'affiche au survol).
// L'icône est créée une seule fois (voir RouteEditLayer : en recréer une à chaque rendu ferait
// reconstruire l'élément du marqueur par Leaflet).
const START_ICON = L.divIcon({
  className: "",
  iconSize: [18, 18],
  iconAnchor: [9, 9],
  html: '<div class="rtd-start-dot"></div>',
});

// PlannedRouteOverlay dessine l’itinéraire sélectionné sur la carte.
//
// Le trajet peut contenir plusieurs segments (une lettre = un segment en mode texte), dessinés chacun
// avec un liseré puis un trait orange. Les liaisons entre lettres d'un mot relié sont en pointillés gris :
// elles servent à passer d'une lettre à l'autre et ne font pas partie du dessin.
function PlannedRouteOverlay({ selectedRoute }) {
  if (!selectedRoute?.segments?.length) return null;

  const first = selectedRoute.segments[0]?.points?.[0];
  return (
    <>
      {selectedRoute.segments.map((segment, index) => {
        const isLink = segment.kind === "link";
        const key = `${selectedRoute.id}-${index}`;
        return (
          <Fragment key={key}>
            {isLink ? null : (
              <Polyline
                positions={segment.points}
                pathOptions={{ className: "rtd-route-casing", weight: 11, opacity: 1, lineCap: "round", lineJoin: "round", interactive: false }}
              />
            )}
            <Polyline
              positions={segment.points}
              pathOptions={{
                className: isLink ? "rtd-route-link" : "rtd-route-line",
                weight: isLink ? 4 : 6,
                opacity: 1,
                dashArray: isLink ? "6 8" : undefined,
                lineCap: "round",
                lineJoin: "round",
                interactive: false,
              }}
            />
          </Fragment>
        );
      })}
      {first ? <Marker position={first} icon={START_ICON} title="Départ" keyboard={false} /> : null}
    </>
  );
}

// MapView est le composant principal de carte de l’application.
//
// Il s’occupe de :
// - afficher le fond de carte
// - montrer la zone de course sélectionnée
// - afficher l’itinéraire généré sélectionné
// - garder quelques informations visuelles au-dessus de la carte
//
// Ce composant gère surtout l’affichage et le comportement de la carte.
// Il ne génère pas lui-même les itinéraires.
export default function MapView({
  theme,
  onToggleTheme,
  neutralBackground,
  onToggleNeutralBackground,
  center,
  radiusKm,
  selectedRoute,
  editor,
  pickingOnMap,
  onPickCenter,
}) {
  // Un centre par défaut est utilisé avant que l’utilisateur choisisse
  // une vraie localisation.
  // Ici on utilise Bordeaux comme valeur de secours.
  const safeCenter = center ?? DEFAULT_CENTER;

  // Le fond neutre n'a de sens que pour faire ressortir un tracé : sans itinéraire affiché, la carte
  // resterait un aplat vide. Le réglage choisi par l'utilisateur est conservé, mais il ne s'applique
  // que lorsqu'un tracé est dessiné.
  const canUseNeutral = Boolean(selectedRoute);
  const neutral = neutralBackground && canUseNeutral;


  // Le fond de carte dépend du thème actuel.
  // On mémorise cette configuration pour ne la recalculer que lorsque le thème change.
  // Tuiles OpenStreetMap standard : gratuites, sans clé d'API. Un filtre CSS (index.css) les désature,
  // et les assombrit en mode nuit, pour que le tracé orange soit la seule chose colorée.
  const tileConfig = useMemo(
    () => ({
      url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      className: theme === "dark" ? "tiles-dark" : "tiles-light",
    }),
    [theme]
  );

  return (
    <div style={styles.shell}>
      <MapContainer center={safeCenter} zoom={13} style={styles.map}>
        <NeutralBackground neutral={neutral} />
        <PickCenter onPick={onPickCenter} enabled={pickingOnMap} />

        {/* key={theme} force Leaflet à recréer la couche quand le thème change (className n'est pas mis à jour sinon).
            En fond neutre, aucune tuile n'est chargée. */}
        {neutral ? null : (
          <TileLayer
            key={theme}
            attribution={tileConfig.attribution}
            url={tileConfig.url}
            className={tileConfig.className}
            maxZoom={19}
          />
        )}

        {/*
           Le cercle représente la zone sélectionnée utilisée
           pour extraire le graphe.
        */}
        {center && !neutral && (
          <Circle
            center={center}
            radius={radiusKm * 1000}
            pathOptions={{ className: "rtd-zone", weight: 2, fillOpacity: 0.06, interactive: false }}
          />
        )}


        {/* Avant la génération, le point choisi est repéré par le même point que le départ du tracé. */}
        {center && !selectedRoute && <Marker position={center} icon={START_ICON} title="Départ" interactive={false} />}
        <PlannedRouteOverlay selectedRoute={selectedRoute} />
        {editor?.editMode && selectedRoute && (
          <RouteEditLayer
            route={selectedRoute}
            pending={editor.pending}
            selectedAnchor={editor.selectedAnchor}
            onSelect={editor.selectAnchor}
            onOperation={editor.applyOperation}
          />
        )}
        <FitToRadius center={center} radiusKm={radiusKm} />
        <FitToRoute selectedRoute={selectedRoute} />
      </MapContainer>

      {/* Édition du tracé : seulement quand un itinéraire de forme ou de mot est affiché. */}
      {editor && selectedRoute && (
        <RouteEditToolbar
          editMode={editor.editMode}
          onToggleEditMode={editor.toggleEditMode}
          pending={editor.pending}
          canUndo={editor.canUndo}
          canRedo={editor.canRedo}
          canReset={editor.canReset}
          hasSelection={Boolean(editor.selectedAnchor)}
          isEdited={editor.isEdited}
          onUndo={editor.undo}
          onRedo={editor.redo}
          onReset={editor.reset}
          onDeleteSelected={editor.deleteSelected}
        />
      )}

      {/* Réglages d'affichage de la carte : thème et fond neutre. */}
      <div style={styles.topBar}>
      <div style={styles.controls}>
        <MapControl
          icon={theme === "dark" ? ICON_SUN : ICON_MOON}
          label={theme === "dark" ? "Mode jour" : "Mode nuit"}
          onClick={onToggleTheme}
        />
        <MapControl
          icon={ICON_LAYERS}
          label="Fond neutre"
          onClick={onToggleNeutralBackground}
          pressed={neutral}
          disabledReason={canUseNeutral ? undefined : "Génère d’abord un parcours : le fond neutre sert à faire ressortir ton tracé."}
        />
      </div>

      {/* Barre de résultats : la distance et l'écart à la cible de l'itinéraire affiché. */}
      {selectedRoute ? (
        <div style={styles.statsBar}>
          <div style={styles.statMain}>
            <span style={styles.statLabel}>Distance</span>
            <span className="rtd-display" style={styles.statValue}>
              {(selectedRoute.total_distance_m / 1000).toFixed(1).replace(".", ",")} km
            </span>
          </div>
          {selectedRoute.edited ? (
            <div style={styles.stat}>
              <span style={styles.statLabelSoft}>Tracé</span>
              <span className="rtd-display" style={styles.statValue}>Modifié</span>
            </div>
          ) : (
            <div style={styles.stat}>
              <span style={styles.statLabelSoft}>Écart à la cible</span>
              <span className="rtd-display" style={styles.statValue}>{Math.round(selectedRoute.length_gap_m)} m</span>
            </div>
          )}
        </div>
      ) : null}
      </div>
    </div>
  );
}

// Les styles ci-dessous définissent la mise en page générale de la carte,
// les contrôles flottants, la carte de résumé, et le message d’avertissement.
//
// L’idée est de garder les informations importantes visibles
// sans masquer trop de surface de carte.
const styles = {
  shell: {
    height: "100%",
    width: "100%",
    position: "relative",
    borderRadius: "var(--radius)",
    overflow: "hidden",
    background: "var(--card)",
    border: "1px solid var(--border)",
  },

  map: {
    height: "100%",
    width: "100%",
  },

  // Rangée du haut : réglages à gauche, résultats à droite ; elle passe à la ligne sur écran étroit
  // au lieu de laisser les deux blocs se chevaucher. Les clics traversent les espaces vides vers la carte.
  topBar: {
    position: "absolute",
    top: 12,
    left: 68,
    right: 12,
    zIndex: 1000,
    display: "flex",
    flexWrap: "wrap",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 8,
    pointerEvents: "none",
  },

  controls: {
    display: "flex",
    gap: 8,
    pointerEvents: "auto",
  },

  controlWrap: {
    position: "relative",
  },

  controlDisabled: {
    opacity: 0.55,
    cursor: "not-allowed",
    boxShadow: "none",
  },

  controlHint: {
    position: "absolute",
    top: "calc(100% + 8px)",
    left: 0,
    width: 240,
    padding: "10px 12px",
    borderRadius: "var(--radius-sm)",
    background: "var(--text)",
    color: "var(--bg-elevated)",
    fontSize: 13,
    fontWeight: 600,
    lineHeight: 1.4,
    boxShadow: "var(--shadow-strong)",
  },

  control: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    minHeight: 44,
    border: "2px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay-strong)",
    color: "var(--text)",
    padding: "0 14px",
    boxShadow: "var(--shadow-strong)",
    fontWeight: 700,
    cursor: "pointer",
  },

  controlPressed: {
    background: "var(--accent)",
    borderColor: "var(--accent)",
    color: "var(--on-accent)",
  },

  controlText: {
    fontSize: 14,
    whiteSpace: "nowrap",
  },

  statsBar: {
    pointerEvents: "auto",
    marginLeft: "auto",
    display: "flex",
    overflow: "hidden",
    borderRadius: "var(--radius)",
    background: "var(--overlay-strong)",
    color: "var(--text)",
    boxShadow: "var(--shadow-strong)",
  },

  statMain: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    padding: "10px 18px",
    background: "var(--accent)",
    color: "var(--on-accent)",
  },

  stat: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    padding: "10px 18px",
  },

  statLabel: {
    fontSize: 12.5,
    fontWeight: 700,
  },

  statLabelSoft: {
    fontSize: 12.5,
    fontWeight: 600,
    color: "var(--text-soft)",
  },

  statValue: {
    fontSize: 26,
    lineHeight: 1,
    fontWeight: 900,
    whiteSpace: "nowrap",
  },
};
