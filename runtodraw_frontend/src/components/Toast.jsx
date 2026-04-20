/*
============================================================
EN:
Toast is a small floating notification shown in the corner
of the screen.

It is used to give quick feedback to the user, for example:
- export success
- error message
- general information

This component is intentionally simple:
it only displays a message and lets the user close it.

FR:
Toast est une petite notification flottante affichée
dans un coin de l’écran.

Elle sert à donner un retour rapide à l’utilisateur, par exemple :
- succès d’un export
- message d’erreur
- information générale

Ce composant est volontairement simple :
il affiche un message et permet à l’utilisateur de le fermer.
============================================================
*/
export default function Toast({ open, message, type = "success", onClose }) {
  /*
  EN:
  If the toast is not open, nothing is rendered.

  FR:
  Si le toast n’est pas ouvert, rien n’est affiché.
  */
  if (!open) return null;

  /*
  EN:
  The accent color depends on the message type.
  This gives a quick visual meaning to the notification.

  FR:
  La couleur d’accent dépend du type de message.
  Cela permet de comprendre rapidement la nature de la notification.
  */
  const accent =
    type === "success" ? "#34c759" : type === "error" ? "#ff3b30" : "#ff9500";

  /*
  EN:
  A short title is also chosen depending on the notification type.

  FR:
  Un titre court est aussi choisi selon le type de notification.
  */
  const title =
    type === "success" ? "Export réussi" : type === "error" ? "Erreur" : "Information";

  return (
    <div style={{ ...styles.wrap, borderColor: accent }}>
      <div style={styles.titleRow}>
        {/* 
        EN: Small colored dot used as a visual status marker.
        FR: Petit point coloré servant de repère visuel de statut.
        */}
        <div style={{ ...styles.dot, background: accent }} />

        {/* 
        EN: Main toast title.
        FR: Titre principal du toast.
        */}
        <div style={styles.title}>{title}</div>

        {/* 
        EN: Close button so the user can dismiss the notification.
        FR: Bouton de fermeture pour que l’utilisateur puisse masquer la notification.
        */}
        <button style={styles.close} onClick={onClose} aria-label="Fermer">
          ✕
        </button>
      </div>

      {/* 
      EN: Main message content.
      FR: Contenu principal du message.
      */}
      <div style={styles.msg}>{message}</div>
    </div>
  );
}

/*
============================================================
EN:
These styles define a compact floating card:
- fixed in the bottom-right corner
- strong enough to be visible
- but still light enough to avoid disturbing the interface too much

FR:
Ces styles définissent une petite carte flottante :
- fixée en bas à droite
- assez visible pour être repérée rapidement
- mais assez légère pour ne pas trop perturber l’interface
============================================================
*/
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