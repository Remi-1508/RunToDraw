import { useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import LoadingModal from "./components/LoadingModal";
import Toast from "./components/Toast";
import { fetchGraphForRun } from "./services/osmGraph";
import { graphToFullJSON, downloadJSON } from "./utils/exportGraph";

export default function App() {
  const [center, setCenter] = useState(null); // position centrale de départ [lat, lng]
  const [distanceKm, setDistanceKm] = useState(10);
  const [graphData, setGraphData] = useState(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [progress, setProgress] = useState(0);
  const [toast, setToast] = useState({ open: false, message: "", type: "success" });

  const toastTimerRef = useRef(null);

  function showToast(message, type = "success") {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ open: true, message, type });

    toastTimerRef.current = setTimeout(() => {
      setToast((t) => ({ ...t, open: false }));
    }, 3500);
  }

  function handlePickSuggestion(latlng) {
    setCenter(latlng);
    setGraphData(null);
  }

  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      alert("La géolocalisation n'est pas supportée par ton navigateur.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCenter([lat, lng]);
        setGraphData(null);
      },
      (err) => {
        console.log(err);
        alert("Impossible de récupérer la position (permission refusée ?).");
      }
    );
  }

  async function handleValidateZone() {
    if (!center) return;
    const [lat, lng] = center;

    setLoadingGraph(true);
    setProgress(0);

    const id = setInterval(() => {
      setProgress((p) => {
        const target = 90;
        const next = p + Math.max(0.6, (target - p) * 0.06);
        return Math.min(target, next);
      });
    }, 120);

    try {
      const g = await fetchGraphForRun({ lat, lon: lng, distanceKm });
      clearInterval(id);
      setProgress(100);
      setGraphData(g);
      await new Promise((r) => setTimeout(r, 180));
    } catch (e) {
      console.log(e);
      alert("Erreur extraction du graphe (Overpass). Réessaye ou baisse la distance.");
      setGraphData(null);
      clearInterval(id);
    } finally {
      setLoadingGraph(false);
      setProgress(0);
    }
  }

  function handleExportFullGraph() {
    if (!graphData) return;

    const payload = graphToFullJSON({ graphData, distanceKm });
    const filename = downloadJSON(`runtodraw_graph_${distanceKm}km_full.json`, payload);

    showToast(
      `Fichier "${filename}" téléchargé.\n➡️ Il est dans le dossier Téléchargements de ton navigateur (ou l’emplacement défini dans ses paramètres).`,
      "success"
    );
  }

  const radiusKm = distanceKm / 2;

  return (
    <div style={styles.page}>
      <LoadingModal open={loadingGraph} progress={progress} />

      <div style={styles.sidebar}>
        <Sidebar
          distanceKm={distanceKm}
          setDistanceKm={setDistanceKm}
          onUseMyLocation={handleUseMyLocation}
          onPickSuggestion={handlePickSuggestion}
          onValidateZone={handleValidateZone}
          canValidate={!!center && !loadingGraph}
          onExportFullGraph={handleExportFullGraph}
          canExport={!!graphData && !loadingGraph}
        />
      </div>

      <div style={styles.mapArea}>
        <MapView center={center} radiusKm={radiusKm} graphData={graphData} />
      </div>

      <Toast
        open={toast.open}
        message={toast.message}
        type={toast.type}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
      />
    </div>
  );
}

const styles = {
  page: {
    height: "100vh",
    width: "100vw",
    display: "grid",
    gridTemplateColumns: "360px 1fr",
    background: "var(--bg)",
  },
  sidebar: { height: "100%", overflow: "auto" },
  mapArea: { height: "100%", padding: 16, boxSizing: "border-box" },
};