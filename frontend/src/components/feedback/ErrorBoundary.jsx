import { Component } from "react";

// Filet de sécurité : si un composant plante pendant son affichage, React démonte toute l'application et la page
// devient blanche. Ce composant attrape l'erreur et affiche à la place un message clair avec un bouton pour recharger.
// (Les erreurs réseau, elles, sont déjà gérées à part : voir useRoutePlanning.)
export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    // Trace dans la console du navigateur : utile pour comprendre le problème en cas de signalement.
    console.error("RunToDraw : erreur d'affichage", error, info?.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" style={styles.page}>
        <div style={styles.card}>
          <h1 style={styles.title}>Oups, quelque chose s’est mal passé</h1>
          <p style={styles.text}>
            L’affichage a rencontré un problème inattendu. Recharge la page pour reprendre : tes réglages de départ
            seront à refaire, mais rien n’est perdu côté serveur.
          </p>
          <button type="button" style={styles.button} onClick={() => window.location.reload()}>
            Recharger la page
          </button>
        </div>
      </div>
    );
  }
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: 16,
    background: "var(--bg, #eef1f4)",
    color: "var(--text, #1b2430)",
    fontFamily: "var(--font-body, system-ui, sans-serif)",
  },
  card: {
    maxWidth: 440,
    padding: "28px 24px",
    borderRadius: 14,
    border: "1px solid var(--border, #dce1e7)",
    background: "var(--bg-elevated, #fff)",
  },
  title: { margin: "0 0 10px", fontSize: 22, fontWeight: 800 },
  text: { margin: "0 0 20px", fontSize: 15, lineHeight: 1.5, color: "var(--text-soft, #556072)" },
  button: {
    minHeight: 48,
    padding: "0 22px",
    border: "none",
    borderRadius: 10,
    background: "var(--accent, #fc4c02)",
    color: "var(--on-accent, #1b2430)",
    fontSize: 16,
    fontWeight: 800,
    cursor: "pointer",
  },
};
