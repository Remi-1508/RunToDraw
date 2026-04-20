/*
============================================================
EN:
LoadingModal is a simple full-screen loading overlay.

It is used to inform the user that an important step is running,
for example:
- graph extraction
- route generation
- theme transition
- location recovery

It can work in two modes:
- progress mode: a percentage is displayed
- indeterminate mode: a moving bar is displayed when the exact progress is unknown

FR:
LoadingModal est une surcouche plein écran de chargement.

Elle sert à informer l’utilisateur qu’une étape importante est en cours,
par exemple :
- extraction du graphe
- génération d’itinéraires
- changement de thème
- récupération de la position

Elle peut fonctionner en deux modes :
- mode progression : un pourcentage est affiché
- mode indéterminé : une barre animée est affichée quand la progression exacte est inconnue
============================================================
*/

export default function LoadingModal({
  open,
  progress = 0,
  title = "Génération du graphe en cours",
  kicker = "OpenStreetMap",
  description = "Extraction des données puis construction du graphe…",
  indeterminate = false,
}) {
  /*
  EN:
  If the modal is not open, nothing is rendered.

  FR:
  Si la modal n’est pas ouverte, rien n’est affiché.
  */
  if (!open) return null;

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        {/* 
        EN: Small label above the main title, useful to indicate the current context or source.
        FR: Petit libellé au-dessus du titre principal, utile pour préciser le contexte ou la source.
        */}
        <div style={styles.kicker}>{kicker}</div>

        {/* 
        EN: Main loading title shown to the user.
        FR: Titre principal du chargement affiché à l’utilisateur.
        */}
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
          EN:
          When progress is known, we display a rounded percentage.
          Otherwise, we display a simple placeholder.

          FR:
          Quand la progression est connue, on affiche un pourcentage arrondi.
          Sinon, on affiche simplement un indicateur générique.
          */}
          <div style={styles.pct}>
            {indeterminate ? "…" : `${Math.round(progress)}%`}
          </div>
        </div>

        {/* 
        EN: Additional explanation shown under the progress bar.
        FR: Explication complémentaire affichée sous la barre de progression.
        */}
        <div style={styles.small}>{description}</div>
      </div>
    </div>
  );
}

/*
============================================================
EN:
These styles define:
- the dark transparent background,
- the centered modal card,
- the progress bar,
- and the text hierarchy.

The goal is to keep the loading state visible and readable,
without making the interface too aggressive.

FR:
Ces styles définissent :
- l’arrière-plan sombre transparent,
- la carte centrée,
- la barre de progression,
- et la hiérarchie visuelle du texte.

L’objectif est de rendre l’état de chargement visible et lisible,
sans rendre l’interface trop agressive.
============================================================
*/
const styles = {
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

  /*
  EN:
  Default progress bar style when the percentage is known.

  FR:
  Style par défaut de la barre quand la progression
  est connue.
  */
  barInner: {
    height: "100%",
    background: "linear-gradient(90deg, var(--accent-strong), #6fb8ff)",
    borderRadius: 999,
    transition: "width 120ms linear",
  },

  /*
  EN:
  Animated bar used when the progress is unknown.

  FR:
  Barre animée utilisée quand la progression
  exacte n’est pas connue.
  */
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