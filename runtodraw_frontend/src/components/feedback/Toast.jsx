// Toast est une petite notification flottante affichée
// dans un coin de l’écran.
//
// Elle sert à donner un retour rapide à l’utilisateur, par exemple :
// - succès d’une action (propositions prêtes, export généré)
// - message d’erreur
// - information générale
//
// Ce composant est volontairement simple :
// il affiche un message et permet à l’utilisateur de le fermer.
export default function Toast({ open, message, type = "success", onClose }) {
  // Si le toast n’est pas ouvert, rien n’est affiché.
  if (!open) return null;

  // La couleur d’accent dépend du type de message.
  // Cela permet de comprendre rapidement la nature de la notification.
  const accent =
    type === "success" ? "#34c759" : type === "error" ? "#ff3b30" : "#ff9500";

  // Un titre court est aussi choisi selon le type de notification.
  const title =
    type === "success" ? "C’est fait" : type === "error" ? "Erreur" : "Information";

  return (
    <div style={{ ...styles.wrap, borderColor: accent }}>
      <div style={styles.titleRow}>
        {/* Petit point coloré servant de repère visuel de statut. */}
        <div style={{ ...styles.dot, background: accent }} />

        {/* Titre principal du toast. */}
        <div style={styles.title}>{title}</div>

        {/* Bouton de fermeture pour que l’utilisateur puisse masquer la notification. */}
        <button style={styles.close} onClick={onClose} aria-label="Fermer">
          ✕
        </button>
      </div>

      {/* Contenu principal du message. */}
      <div style={styles.msg}>{message}</div>
    </div>
  );
}

// Ces styles définissent une petite carte flottante :
// - fixée en bas à droite
// - assez visible pour être repérée rapidement
// - mais assez légère pour ne pas trop perturber l’interface
const styles = {
  wrap: {
    position: "fixed",
    bottom: 18,
    right: 18,
    width: 360,
    maxWidth: "calc(100vw - 32px)",
    background: "var(--overlay-strong)",
    color: "var(--text)",
    border: "1px solid var(--border)",
    borderLeftWidth: 4,
    borderRadius: 22,
    padding: 14,
    zIndex: 10000,
    boxShadow: "var(--shadow-strong)",
    backdropFilter: "blur(16px)",
    whiteSpace: "pre-line",
  },

  titleRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },

  dot: {
    width: 10,
    height: 10,
    borderRadius: 999,
  },

  title: {
    fontWeight: 800,
    letterSpacing: -0.2,
  },

  close: {
    marginLeft: "auto",
    border: "none",
    background: "transparent",
    color: "var(--text-soft)",
    cursor: "pointer",
    fontSize: 14,
  },

  msg: {
    marginTop: 8,
    fontSize: 13,
    color: "var(--text-soft)",
    lineHeight: 1.45,
  },
};