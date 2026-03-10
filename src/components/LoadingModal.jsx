export default function LoadingModal({ open, progress = 0 }) {
  if (!open) return null;

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        <div style={styles.title}>Génération du graphe</div>

        <div style={styles.row}>
          <div style={styles.barOuter}>
            <div style={{ ...styles.barInner, width: `${progress}%` }} />
          </div>
          <div style={styles.pct}>{Math.round(progress)}%</div>
        </div>

        <div style={styles.small}>
          Extraction OpenStreetMap + construction du graphe…
        </div>
      </div>
    </div>
  );
}

const styles = {
  backdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.45)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999,
  },
  modal: {
    width: 380,
    background: "var(--panel)",
    color: "var(--text)",
    borderRadius: 16,
    padding: 16,
    border: "1px solid var(--border)",
    boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
  },
  title: { fontWeight: 900, fontSize: 16, marginBottom: 10 },
  row: { display: "flex", gap: 10, alignItems: "center" },
  barOuter: {
    flex: 1,
    height: 10,
    background: "rgba(255,255,255,0.08)",
    borderRadius: 999,
    overflow: "hidden",
    border: "1px solid rgba(255,255,255,0.08)",
  },
  barInner: {
    height: "100%",
    background: "var(--accent)",
    borderRadius: 999,
    transition: "width 120ms linear",
  },
  pct: { width: 52, textAlign: "right", color: "var(--muted)", fontWeight: 800 },
  small: { marginTop: 10, fontSize: 12, color: "var(--muted)" },
};