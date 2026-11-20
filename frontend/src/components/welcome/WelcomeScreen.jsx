import logoDay from "../../assets/logo_runtodraw_day.png";
import logoNight from "../../assets/logo_runtodraw_night.png";
import { EXAMPLES } from "../../config";

// Écran d'accueil, affiché à la première visite : on entre en invité (la connexion arrivera plus tard) ou
// on essaie directement un exemple. Il ne bloque rien : « Continuer en invité » ouvre l'application.
export default function WelcomeScreen({ theme, onGuest, onExample }) {
  return (
    <div style={styles.backdrop} role="dialog" aria-modal="true" aria-labelledby="welcome-title">
      <div style={styles.panel}>
        <img src={theme === "dark" ? logoNight : logoDay} alt="RunToDraw" style={styles.logo} />

        <h1 id="welcome-title" className="rtd-display" style={styles.title}>
          Dessine sur la carte avec tes jambes
        </h1>
        <p style={styles.lead}>
          Choisis un départ, une distance et une forme ou un mot : RunToDraw trace un parcours sur les vraies rues,
          prêt à exporter vers Strava ou ta montre.
        </p>

        <div style={styles.actions}>
          <button type="button" style={styles.primary} onClick={onGuest}>
            Continuer en invité
          </button>
          <button type="button" style={styles.disabled} disabled aria-describedby="welcome-login-note">
            Se connecter
            <span style={styles.soon}>Bientôt</span>
          </button>
        </div>
        <p id="welcome-login-note" style={styles.note}>
          Les comptes (parcours favoris, historique) arriveront plus tard. En invité, tout fonctionne déjà.
        </p>

        <div style={styles.examplesTitle}>Ou essaie un exemple</div>
        <div style={styles.examples}>
          {EXAMPLES.map((example) => (
            <button key={example.id} type="button" style={styles.example} onClick={() => onExample(example)}>
              <span style={styles.exampleName}>{example.title}</span>
              <span style={styles.exampleDetail}>{example.detail}</span>
            </button>
          ))}
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
    margin: 0,
    fontSize: 28,
    lineHeight: 1.15,
    fontWeight: 900,
  },

  lead: {
    margin: "12px 0 22px",
    fontSize: 15,
    lineHeight: 1.55,
    color: "var(--text-soft)",
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

  note: {
    margin: "10px 0 0",
    fontSize: 12.5,
    lineHeight: 1.45,
    color: "var(--text-soft)",
  },

  examplesTitle: {
    marginTop: 26,
    marginBottom: 10,
    fontSize: 13.5,
    fontWeight: 800,
    color: "var(--text-soft)",
  },

  examples: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },

  example: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 2,
    minHeight: "var(--control-h)",
    padding: "9px 14px",
    border: "2px solid var(--border-strong)",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay)",
    color: "var(--text)",
    textAlign: "left",
    cursor: "pointer",
  },

  exampleName: {
    fontSize: 15,
    fontWeight: 800,
  },

  exampleDetail: {
    fontSize: 12.5,
    fontWeight: 600,
    color: "var(--text-soft)",
  },
};
