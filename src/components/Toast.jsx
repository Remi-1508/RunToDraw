export default function Toast({ open, message, type = "success", onClose }) {
  if (!open) return null;

  const accent =
    type === "success" ? "var(--good)" : type === "error" ? "#ff3b30" : "var(--warn)";

  return (
    <div style={{ ...styles.wrap, borderColor: accent }}>
      <div style={styles.titleRow}>
        <div style={{ ...styles.dot, background: accent }} />
        <div style={styles.title}>
          {type === "success" ? "Export réussi ✅" : type === "error" ? "Erreur" : "Info"}
        </div>
        <button style={styles.close} onClick={onClose} aria-label="Fermer">
          ✕
        </button>
      </div>

      <div style={styles.msg}>{message}</div>
    </div>
  );
}

const styles = {
  wrap: {
    position: "fixed",
    bottom: 18,
    right: 18,
    width: 380,
    maxWidth: "calc(100vw - 36px)",
    background: "rgba(10,10,12,0.92)",
    color: "var(--text)",
    border: "2px solid var(--good)",
    borderRadius: 14,
    padding: 12,
    zIndex: 10000,
    boxShadow: "0 12px 30px rgba(0,0,0,0.4)",
    backdropFilter: "blur(6px)",
    whiteSpace: "pre-line",
  },
  titleRow: { display: "flex", alignItems: "center", gap: 10 },
  dot: { width: 10, height: 10, borderRadius: 999 },
  title: { fontWeight: 900, letterSpacing: 0.2 },
  close: {
    marginLeft: "auto",
    border: "none",
    background: "transparent",
    color: "var(--muted)",
    cursor: "pointer",
    fontSize: 14,
  },
  msg: { marginTop: 8, fontSize: 12.5, color: "var(--muted)", lineHeight: 1.35 },
};