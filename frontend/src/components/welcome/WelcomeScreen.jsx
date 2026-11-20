import logoDay from "../../assets/logo_runtodraw_day.png";
import logoNight from "../../assets/logo_runtodraw_night.png";

// Écran d'accueil, affiché à la première visite : on entre en invité (la connexion arrivera plus tard).
export default function WelcomeScreen({ theme, onGuest }) {
  return (
    <div style={styles.backdrop} role="dialog" aria-modal="true" aria-label="Bienvenue sur RunToDraw">
      <div style={styles.panel}>
        <img src={theme === "dark" ? logoNight : logoDay} alt="RunToDraw" style={styles.logo} />
        <h1 className="rtd-display" style={styles.title}>
          Dessine sur la carte en courant
        </h1>

        <div style={styles.actions}>
          <button type="button" style={styles.primary} onClick={onGuest}>
            Continuer en invité
          </button>
          <button type="button" style={styles.disabled} disabled>
            Se connecter
            <span style={styles.soon}>Bientôt</span>
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  backdrop: {
    position: "fixed",
    inset: 0,
    zIndex: 3000,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    overflowY: "auto",
    background: "var(--bg)",
  },

  panel: {
    width: "100%",
    maxWidth: 520,
    margin: "auto",
    padding: "28px 24px",
    borderRadius: "var(--radius)",
    border: "1px solid var(--border)",
    background: "var(--bg-elevated)",
    boxShadow: "var(--shadow-strong)",
    color: "var(--text)",
  },

  logo: {
    display: "block",
    height: 52,
    width: "auto",
    marginBottom: 22,
  },

  title: {
    margin: "0 0 26px",
    fontSize: 28,
    lineHeight: 1.15,
    fontWeight: 900,
  },


  actions: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },

  primary: {
    minHeight: 52,
    border: "none",
    borderRadius: "var(--radius-sm)",
    background: "var(--accent)",
    color: "var(--on-accent)",
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontSize: 17,
    fontWeight: 800,
    cursor: "pointer",
  },

  disabled: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    minHeight: 48,
    border: "2px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "transparent",
    color: "var(--text-soft)",
    fontWeight: 700,
    fontSize: 15,
    cursor: "not-allowed",
    opacity: 0.8,
  },

  soon: {
    padding: "2px 8px",
    borderRadius: 999,
    background: "var(--chip)",
    color: "var(--accent-text)",
    fontSize: 12,
    fontWeight: 800,
  },






};
