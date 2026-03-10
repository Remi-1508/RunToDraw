import { MapContainer, TileLayer, Circle, useMap } from "react-leaflet";
import { useEffect, useState } from "react";
import { boundsFromCenterRadiusKm } from "../utils/geo";
import GraphOverlay from "./GraphOverlay";

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

export default function MapView({ center, radiusKm, graphData }) {
  const safeCenter = center ?? [44.8378, -0.5792];
  const [showWarn, setShowWarn] = useState(false);

  const MAX_SEG = 2000;
  const MAX_NODES = 3000;

  const vertexCount = graphData?.nodesById?.size ?? 0;
  const edgeCount = graphData?.edgeCount ?? 0;

  const limited = graphData && (edgeCount > MAX_SEG || vertexCount > MAX_NODES);

  return (
    <div style={{ height: "100%", width: "100%", position: "relative" }}>
      <MapContainer
        center={safeCenter}
        zoom={13}
        style={{ height: "100%", width: "100%", borderRadius: 16 }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {center && <Circle center={center} radius={radiusKm * 1000} />}

        {graphData?.nodesById && graphData?.edgesByNode && (
          <GraphOverlay
            nodesById={graphData.nodesById}
            edgesByNode={graphData.edgesByNode}
            maxSegments={MAX_SEG}
            maxNodes={MAX_NODES}
          />
        )}

        <FitToRadius center={center} radiusKm={radiusKm} />
      </MapContainer>

      {graphData && (
        <div style={styles.topRight}>
          <div style={styles.hud}>
            <div style={{ fontWeight: 900 }}>Graphe</div>
            <div>Sommets : {vertexCount.toLocaleString()}</div>
            <div>Arêtes : {edgeCount.toLocaleString()}</div>
            <div style={{ marginTop: 6, fontSize: 11, opacity: 0.9 }}>
              Bleu = arêtes • Rouge = sommets
            </div>
          </div>

          {limited && (
            <div style={{ marginTop: 10 }}>
              <button
                style={styles.warnBtn}
                onClick={() => setShowWarn((s) => !s)}
              >
                ⚠️ AFFICHAGE LIMITÉ
              </button>

              {showWarn && (
                <div style={styles.warnBox}>
                  Pour éviter de faire lag le navigateur, on n’affiche qu’un
                  échantillon : <b>max {MAX_SEG} arêtes</b> /{" "}
                  <b>{MAX_NODES} sommets</b>.
                  <br />
                  Les stats “Sommets/Arêtes” restent exactes.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  topRight: {
    position: "absolute",
    top: 14,
    right: 14,
    zIndex: 1000,
    width: 280,
  },
  hud: {
    background: "rgba(10,10,12,0.88)",
    color: "var(--text)",
    border: "2px solid rgba(255,255,255,0.15)",
    borderRadius: 14,
    padding: 12,
    fontSize: 12,
    lineHeight: 1.35,
    boxShadow: "0 10px 24px rgba(0,0,0,0.35)",
  },
  warnBtn: {
    width: "100%",
    border: "2px solid #ff3b30",
    background: "#ff3b30",
    color: "#0b0c10",
    padding: "10px 12px",
    borderRadius: 14,
    cursor: "pointer",
    fontWeight: 950,
    letterSpacing: 0.5,
    boxShadow: "0 10px 22px rgba(255,59,48,0.35)",
  },
  warnBox: {
    marginTop: 10,
    background: "rgba(10,10,12,0.92)",
    border: "2px solid rgba(255,59,48,0.55)",
    borderRadius: 14,
    padding: 12,
    fontSize: 12,
    color: "var(--text)",
    lineHeight: 1.35,
    boxShadow: "0 10px 24px rgba(0,0,0,0.35)",
  },
};