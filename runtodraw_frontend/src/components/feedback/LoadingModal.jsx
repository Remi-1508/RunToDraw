// LoadingModal est une surcouche plein écran de chargement.
//
// Elle sert à informer l’utilisateur qu’une étape importante est en cours,
// par exemple :
// - extraction du graphe
// - génération d’itinéraires
// - changement de thème
// - récupération de la position
//
// Elle peut fonctionner en deux modes :
// - mode progression : un pourcentage est affiché
// - mode indéterminé : une barre animée est affichée quand la progression exacte est inconnue

export default function LoadingModal({
  open,
  progress = 0,
  title = "Génération du graphe en cours",
  kicker = "OpenStreetMap",
  description = "Extraction des données puis construction du graphe…",
  indeterminate = false,
  onCancel,
}) {
  // Si la modal n’est pas ouverte, rien n’est affiché.
  if (!open) return null;

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        {/* Petit libellé au-dessus du titre principal, utile pour préciser le contexte ou la source. */}
        <div style={styles.kicker}>{kicker}</div>

        {/* Titre principal du chargement affiché à l’utilisateur. */}
        <div style={styles.title}>{title}</div>

        <div style={styles.row}>
          <div style={styles.barOuter}>
            <div
              style={{
                ...styles.barInner,
                ...(indeterminate
                  ? styles.barInnerIndeterminate
                  : { width: `${progress}%` }),
              }}
            />
          </div>

          {/*
             Quand la progression est connue, on affiche un pourcentage arrondi.
             Sinon, on affiche simplement un indicateur générique.
          */}
          <div style={styles.pct}>
            {indeterminate ? "…" : `${Math.round(progress)}%`}
          </div>
        </div>

        {/* Explication complémentaire affichée sous la barre de progression. */}
        <div style={styles.small}>{description}</div>

        {/* Bouton facultatif pour interrompre l'opération en cours. */}
        {onCancel ? (
          <button type="button" style={styles.cancelButton} onClick={onCancel}>
            Annuler
          </button>
        ) : null}
      </div>
    </div>
  );
}

// Ces styles définissent :
// - l’arrière-plan sombre transparent,
// - la carte centrée,
// - la barre de progression,
// - et la hiérarchie visuelle du texte.
//
// L’objectif est de rendre l’état de chargement visible et lisible,
// sans rendre l’interface trop agressive.
const styles = {
  cancelButton: {
    marginTop: 14,
    padding: "8px 16px",
    border: "1px solid var(--border)",
    borderRadius: 999,
    background: "var(--chip)",
    color: "var(--text)",
    fontWeight: 700,
    cursor: "pointer",
  },

  backdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(0, 0, 0, 0.22)",
    backdropFilter: "blur(10px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999,
  },

  modal: {
    width: 440,
    maxWidth: "calc(100vw - 32px)",
    background: "var(--overlay-strong)",
    color: "var(--text)",
    borderRadius: 28,
    padding: 20,
    border: "1px solid var(--border)",
    boxShadow: "var(--shadow-strong)",
    backdropFilter: "blur(20px)",
  },

  kicker: {
    fontSize: 12,
    color: "var(--text-soft)",
    marginBottom: 6,
    fontWeight: 700,
  },

  title: {
    fontWeight: 800,
    fontSize: 20,
    letterSpacing: -0.4,
    marginBottom: 14,
  },

  row: {
    display: "flex",
    gap: 12,
    alignItems: "center",
  },

  barOuter: {
    flex: 1,
    height: 12,
    background: "var(--chip)",
    borderRadius: 999,
    overflow: "hidden",
    position: "relative",
  },

  // Style par défaut de la barre quand la progression
  // est connue.
  barInner: {
    height: "100%",
    background: "linear-gradient(90deg, var(--accent-strong), #6fb8ff)",
    borderRadius: 999,
    transition: "width 120ms linear",
  },

  // Barre animée utilisée quand la progression
  // exacte n’est pas connue.
  barInnerIndeterminate: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: "-35%",
    width: "35%",
    animation: "rtd-indeterminate 1.15s ease-in-out infinite",
  },

  pct: {
    width: 54,
    textAlign: "right",
    color: "var(--text-soft)",
    fontWeight: 800,
  },

  small: {
    marginTop: 12,
    fontSize: 13,
    color: "var(--text-soft)",
    lineHeight: 1.5,
    whiteSpace: "pre-line",
  },
};