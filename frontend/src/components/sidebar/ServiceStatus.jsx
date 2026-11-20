// Message discret quand les serveurs de cartes (OpenStreetMap) sont chargés. Rien n'est affiché quand tout va bien,
// et le ton reste rassurant : on prévient d'une attente possible, pas d'un risque d'échec (la génération réessaie
// toute seule, voir useRoutePlanning).
const TEXTS = {
  slow: "Les serveurs de cartes sont un peu chargés : ça peut prendre un peu plus de temps que d’habitude.",
  down: "Les serveurs de cartes sont très sollicités : on réessaie automatiquement pour toi, tu n’as rien à faire.",
};

export default function ServiceStatus({ status }) {
  const text = status ? TEXTS[status.state] : null;
  if (!text) return null;
  return (
    <div style={styles.row} role="status">
      {text}
    </div>
  );
}

const styles = {
  row: {
    fontSize: 12.5,
    color: "var(--text-soft)",
    lineHeight: 1.45,
    textAlign: "center",
  },
};
