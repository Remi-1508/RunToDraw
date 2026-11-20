// État des serveurs de cartes (OpenStreetMap), en une ligne avec une pastille de couleur. Le ton reste rassurant :
// on prévient d'une attente possible, pas d'un risque d'échec (la génération réessaie toute seule, voir
// useRoutePlanning). Même en cas de panne, la pastille est orange et non rouge : ce n'est pas une erreur.
const STATES = {
  ok: { color: "var(--success-strong)", text: "Serveurs de cartes disponibles." },
  slow: {
    color: "#d98a00",
    text: "Les serveurs de cartes sont un peu chargés : ça peut prendre un peu plus de temps que d’habitude.",
  },
  down: {
    color: "#d98a00",
    text: "Les serveurs de cartes sont très sollicités : on réessaie automatiquement pour toi, tu n’as rien à faire.",
  },
};

export default function ServiceStatus({ status }) {
  const info = status ? STATES[status.state] : null;
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
    fontSize: 12.5,
    color: "var(--text-soft)",
    lineHeight: 1.45,
  },
  dot: {
    flexShrink: 0,
    width: 9,
    height: 9,
    marginTop: 5,
    borderRadius: "50%",
  },
};
