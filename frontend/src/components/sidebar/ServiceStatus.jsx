// Pastille d'état des serveurs OpenStreetMap : explique à l'avance pourquoi une génération peut être lente
// ou échouer, au lieu de laisser la personne attendre sans comprendre.
const TEXTS = {
  ok: { color: "var(--success-strong)", text: "Serveurs OpenStreetMap : disponibles." },
  slow: { color: "#c77700", text: "Serveurs OpenStreetMap : lents en ce moment, la génération peut durer plus longtemps." },
  down: { color: "#c0341d", text: "Serveurs OpenStreetMap : injoignables pour l’instant. Réessaie dans quelques minutes." },
};

export default function ServiceStatus({ status }) {
  const info = status ? TEXTS[status.state] : null;
  if (!info) return null;
  return (
    <div style={styles.row} role="status">
      <span style={{ ...styles.dot, background: info.color }} aria-hidden="true" />
      <span>{info.text}</span>
    </div>
  );
}

const styles = {
  row: {
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
    marginTop: 12,
    fontSize: 12.5,
    fontWeight: 600,
    color: "var(--text-soft)",
    lineHeight: 1.4,
  },
  dot: {
    flexShrink: 0,
    width: 9,
    height: 9,
    marginTop: 4,
    borderRadius: "50%",
  },
};
