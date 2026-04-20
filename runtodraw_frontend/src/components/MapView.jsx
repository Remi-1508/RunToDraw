import { Circle, MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo, useState } from "react";
import { boundsFromCenterRadiusKm } from "../utils/geo";
import GraphOverlay from "./GraphOverlay";

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
function ThemeControl({ theme, onToggleTheme, themeLoading }) {
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={onToggleTheme}
      disabled={themeLoading}
      style={{
        ...styles.themeControl,
        opacity: themeLoading ? 0.72 : 1,
        cursor: themeLoading ? "wait" : "pointer",
      }}
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

  return (
    <>
      {selectedRoute.segments.map((segment, index) => (
        <Polyline
          key={`${selectedRoute.id}-${index}`}
          positions={segment.points}
          pathOptions={{
            color: index % 2 === 0 ? "#34c759" : "#ff9f0a",
            weight: 5,
            opacity: 0.9,
          }}
        />
      ))}
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
- optionally displaying the road graph
- showing the selected generated route
- keeping a few visual indicators on top of the map

This component is mostly about display and map behavior.
It does not generate routes itself.

FR:
MapView est le composant principal de carte de l’application.

Il s’occupe de :
- afficher le fond de carte
- montrer la zone de course sélectionnée
- afficher le graphe routier si besoin
- afficher l’itinéraire généré sélectionné
- garder quelques informations visuelles au-dessus de la carte

Ce composant gère surtout l’affichage et le comportement de la carte.
Il ne génère pas lui-même les itinéraires.
============================================================
*/
export default function MapView({
  theme,
  onToggleTheme,
  themeLoading,
  center,
  radiusKm,
  graphData,
  showFullGraph,
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

  const [showWarn, setShowWarn] = useState(false);

  /*
  EN:
  These limits are used to avoid slowing down the browser too much
  when the graph is large.

  FR:
  Ces limites servent à éviter de trop ralentir le navigateur
  quand le graphe est grand.
  */
  const MAX_SEG = 2000;
  const MAX_NODES = 3000;

  const vertexCount = graphData?.nodesById?.size ?? 0;
  const edgeCount = graphData?.edgeCount ?? 0;

  /*
  EN:
  If the graph is larger than the display limits, we still keep the real stats,
  but we warn the user that the visual rendering is limited.

  FR:
  Si le graphe dépasse les limites d’affichage, on garde quand même
  les vraies statistiques, mais on avertit l’utilisateur que le rendu visuel est limité.
  */
  const limited = graphData && (edgeCount > MAX_SEG || vertexCount > MAX_NODES);

  /*
  EN:
  The tile provider depends on the current theme.
  We memoize the configuration so it is only recalculated when the theme changes.

  FR:
  Le fond de carte dépend du thème actuel.
  On mémorise cette configuration pour ne la recalculer que lorsque le thème change.
  */
  const tileConfig = useMemo(() => {
    if (theme === "dark") {
      return {
        url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      };
    }

    return {
      url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
    };
  }, [theme]);

  return (
    <div style={styles.shell}>
      <MapContainer center={safeCenter} zoom={13} style={styles.map}>
        <TileLayer attribution={tileConfig.attribution} url={tileConfig.url} />

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

        {/*
        EN:
        The raw graph is optional because drawing everything all the time
        would be too heavy and not always useful for the user.

        FR:
        L’affichage du graphe brut est optionnel car tout dessiner en permanence
        serait trop lourd et pas toujours utile pour l’utilisateur.
        */}
        {showFullGraph && graphData?.nodesById && graphData?.edgesByNode && (
          <GraphOverlay
            nodesById={graphData.nodesById}
            edgesByNode={graphData.edgesByNode}
            maxSegments={MAX_SEG}
            maxNodes={MAX_NODES}
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
        <ThemeControl theme={theme} onToggleTheme={onToggleTheme} themeLoading={themeLoading} />
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
              Vert/orange = segments du trajet sélectionné
            </div>
          </div>

          {/*
          EN:
          If the graph rendering is limited, we display a warning button
          with an explanation box.

          FR:
          Si l’affichage du graphe est limité, on affiche un bouton d’avertissement
          avec une boîte explicative.
          */}
          {limited && (
            <div style={{ marginTop: 10 }}>
              <button style={styles.warnBtn} onClick={() => setShowWarn((s) => !s)}>
                Affichage limité
              </button>

              {showWarn && (
                <div style={styles.warnBox}>
                  Pour éviter les ralentissements du navigateur, l’affichage du graphe est limité
                  à <b>{MAX_SEG} arêtes</b> et <b>{MAX_NODES} sommets</b>.
                  <br />
                  Les statistiques restent exactes.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/*
============================================================
EN:
The styles below define the general map layout,
floating controls, summary card, and warning message.

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

  warnBtn: {
    width: "100%",
    border: "none",
    background: "#ff9500",
    color: "white",
    padding: "12px 14px",
    borderRadius: 18,
    cursor: "pointer",
    fontWeight: 700,
    boxShadow: "0 10px 24px rgba(255,149,0,0.28)",
  },

  warnBox: {
    marginTop: 10,
    background: "var(--overlay)",
    border: "1px solid rgba(255,149,0,0.35)",
    borderRadius: 18,
    padding: 12,
    fontSize: 12,
    color: "var(--text)",
    lineHeight: 1.45,
    backdropFilter: "blur(16px)",
    boxShadow: "var(--shadow-soft)",
  },
};