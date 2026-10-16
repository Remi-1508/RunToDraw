import { Circle, MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo } from "react";
import { boundsFromCenterRadiusKm } from "../utils/geo";

/*
============================================================
EN:
FitToRadius automatically adjusts the map view to the selected
running area when the center or radius changes.

FR:
FitToRadius ajuste automatiquement la vue de la carte
à la zone de course choisie quand le centre ou le rayon change.
============================================================
*/
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

/*
============================================================
EN:
FitToRoute recenters the map on the currently selected route.
This is useful once the user chooses one itinerary from the results.

FR:
FitToRoute recentre la carte sur l’itinéraire actuellement sélectionné.
C’est utile une fois que l’utilisateur choisit un trajet parmi les résultats.
============================================================
*/
function FitToRoute({ selectedRoute }) {
  const map = useMap();

  useEffect(() => {
    if (!selectedRoute?.segments?.length) return;
    const allPoints = selectedRoute.segments.flatMap((segment) => segment.points || []);
    if (allPoints.length < 2) return;
    map.fitBounds(allPoints, { padding: [45, 45] });
  }, [selectedRoute, map]);

  return null;
}

/*
============================================================
EN:
ThemeControl is the small button displayed on the map
to switch between light mode and dark mode.

FR:
ThemeControl est le petit bouton affiché sur la carte
pour passer du mode clair au mode sombre.
============================================================
*/
function ThemeControl({ theme, onToggleTheme }) {
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={onToggleTheme}
      style={styles.themeControl}
      title={isDark ? "Passer en mode jour" : "Passer en mode nuit"}
      aria-label={isDark ? "Passer en mode jour" : "Passer en mode nuit"}
    >
      <span style={styles.themeControlEmoji}>{isDark ? "🌙" : "☀️"}</span>
      <span style={styles.themeControlText}>{isDark ? "Mode nuit" : "Mode jour"}</span>
    </button>
  );
}

/*
============================================================
EN:
PlannedRouteOverlay draws the selected route on the map.

The route can contain several segments, especially in text mode,
so we draw each segment one after another.
Two colors are alternated to make the segments easier to distinguish.

FR:
PlannedRouteOverlay dessine l’itinéraire sélectionné sur la carte.

Le trajet peut contenir plusieurs segments, surtout en mode texte,
donc on dessine chaque segment séparément.
Deux couleurs sont alternées pour mieux distinguer les segments.
============================================================
*/
function PlannedRouteOverlay({ selectedRoute }) {
  if (!selectedRoute?.segments?.length) return null;

  // Les lettres alternent vert / orange ; les liaisons entre lettres d'un mot relié
  // sont en pointillés gris, pour bien voir qu'elles ne font pas partie du dessin.
  let letterIndex = 0;
  return (
    <>
      {selectedRoute.segments.map((segment, index) => {
        const isLink = segment.kind === "link";
        const color = isLink ? "#8e8e93" : letterIndex++ % 2 === 0 ? "#34c759" : "#ff9f0a";
        return (
          <Polyline
            key={`${selectedRoute.id}-${index}`}
            positions={segment.points}
            pathOptions={{
              color,
              weight: isLink ? 4 : 5,
              opacity: isLink ? 0.85 : 0.9,
              dashArray: isLink ? "6 8" : undefined,
            }}
          />
        );
      })}
    </>
  );
}

/*
============================================================
EN:
MapView is the main map component of the application.

It is responsible for:
- displaying the base map
- showing the selected running zone
- showing the selected generated route
- keeping a few visual indicators on top of the map

This component is mostly about display and map behavior.
It does not generate routes itself.

FR:
MapView est le composant principal de carte de l’application.

Il s’occupe de :
- afficher le fond de carte
- montrer la zone de course sélectionnée
- afficher l’itinéraire généré sélectionné
- garder quelques informations visuelles au-dessus de la carte

Ce composant gère surtout l’affichage et le comportement de la carte.
Il ne génère pas lui-même les itinéraires.
============================================================
*/
export default function MapView({
  theme,
  onToggleTheme,
  center,
  radiusKm,
  graphData,
  routePlan,
  selectedRoute,
}) {
  /*
  EN:
  A default center is used before the user chooses a real location.
  Here we use Bordeaux as a fallback.

  FR:
  Un centre par défaut est utilisé avant que l’utilisateur choisisse
  une vraie localisation.
  Ici on utilise Bordeaux comme valeur de secours.
  */
  const safeCenter = center ?? [44.8378, -0.5792];

  const vertexCount = graphData?.nodeCount ?? graphData?.nodesById?.size ?? 0;
  const edgeCount = graphData?.edgeCount ?? 0;


  /*
  EN:
  The tile provider depends on the current theme.
  We memoize the configuration so it is only recalculated when the theme changes.

  FR:
  Le fond de carte dépend du thème actuel.
  On mémorise cette configuration pour ne la recalculer que lorsque le thème change.
  */
  // Tuiles OpenStreetMap standard : gratuites, sans clé d'API.
  // Un filtre CSS les rend plus sobres (couleurs très atténuées) et le mode nuit les inverse :
  // classes "tiles-light" / "tiles-dark" dans index.css.
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
        {/* key={theme} force Leaflet à recréer la couche quand le thème change (className n'est pas mis à jour sinon) */}
        <TileLayer
          key={theme}
          attribution={tileConfig.attribution}
          url={tileConfig.url}
          className={tileConfig.className}
          maxZoom={19}
        />

        {/*
        EN:
        The circle shows the selected area used to extract the graph.

        FR:
        Le cercle représente la zone sélectionnée utilisée
        pour extraire le graphe.
        */}
        {center && (
          <Circle
            center={center}
            radius={radiusKm * 1000}
            pathOptions={{
              color: "var(--accent-strong)",
              fillColor: "var(--accent-strong)",
              fillOpacity: 0.08,
            }}
          />
        )}


        <PlannedRouteOverlay selectedRoute={selectedRoute} />
        <FitToRadius center={center} radiusKm={radiusKm} />
        <FitToRoute selectedRoute={selectedRoute} />
      </MapContainer>

      {/*
      EN:
      Theme switch button placed directly on the map.

      FR:
      Bouton de changement de thème placé directement sur la carte.
      */}
      <div style={styles.themeControlWrap}>
        <ThemeControl theme={theme} onToggleTheme={onToggleTheme}  />
      </div>

      {/*
      EN:
      This small top-right panel gives quick feedback about the graph
      and the selected route.

      FR:
      Ce petit panneau en haut à droite donne un retour rapide
      sur le graphe et l’itinéraire sélectionné.
      */}
      {(graphData || routePlan) && (
        <div style={styles.topRight}>
          <div style={styles.hud}>
            <div style={styles.hudTitle}>Résumé</div>

            {graphData ? (
              <div style={styles.hudStat}>Sommets : {vertexCount.toLocaleString()}</div>
            ) : null}

            {graphData ? (
              <div style={styles.hudStat}>Arêtes : {edgeCount.toLocaleString()}</div>
            ) : null}

            {selectedRoute ? (
              <div style={styles.hudStat}>Itinéraire : {selectedRoute.label}</div>
            ) : null}

            {selectedRoute ? (
              <div style={styles.hudStat}>
                Distance : {(selectedRoute.total_distance_m / 1000).toFixed(2)} km
              </div>
            ) : null}

            <div style={styles.hudCaption}>
              {selectedRoute?.segments?.some((segment) => segment.kind === "link")
                ? "Vert/orange = lettres · pointillés gris = liaisons"
                : "Vert/orange = morceaux du trajet sélectionné"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/*
============================================================
EN:
The styles below define the general map layout,
floating controls and summary card.

The idea is to keep important map information visible
without hiding too much of the map itself.

FR:
Les styles ci-dessous définissent la mise en page générale de la carte,
les contrôles flottants, la carte de résumé, et le message d’avertissement.

L’idée est de garder les informations importantes visibles
sans masquer trop de surface de carte.
============================================================
*/
const styles = {
  shell: {
    height: "100%",
    width: "100%",
    position: "relative",
    borderRadius: 32,
    overflow: "hidden",
    background: "var(--card)",
    border: "1px solid var(--border)",
    boxShadow: "var(--shadow-soft)",
  },

  map: {
    height: "100%",
    width: "100%",
  },

  themeControlWrap: {
    position: "absolute",
    top: 12,
    left: 68,
    zIndex: 1000,
  },

  themeControl: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    border: "1px solid var(--border)",
    borderRadius: 16,
    background: "var(--overlay-strong)",
    color: "var(--text)",
    padding: "10px 12px",
    boxShadow: "var(--shadow-soft)",
    backdropFilter: "blur(16px)",
    fontWeight: 700,
    cursor: "pointer",
  },

  themeControlEmoji: {
    fontSize: 16,
    lineHeight: 1,
  },

  themeControlText: {
    fontSize: 13,
    whiteSpace: "nowrap",
  },

  topRight: {
    position: "absolute",
    top: 16,
    right: 16,
    zIndex: 1000,
    width: 280,
  },

  hud: {
    background: "var(--overlay)",
    color: "var(--text)",
    border: "1px solid var(--border)",
    borderRadius: 24,
    padding: 14,
    fontSize: 13,
    lineHeight: 1.4,
    boxShadow: "var(--shadow-soft)",
    backdropFilter: "blur(16px)",
  },

  hudTitle: {
    fontWeight: 800,
    fontSize: 15,
    marginBottom: 6,
  },

  hudStat: {
    marginBottom: 2,
  },

  hudCaption: {
    marginTop: 8,
    fontSize: 11.5,
    color: "var(--text-soft)",
  },
};