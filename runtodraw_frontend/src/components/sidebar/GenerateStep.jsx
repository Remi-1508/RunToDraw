import { styles } from "./styles";

// Étape 4 : lancement de la génération des itinéraires.
export default function GenerateStep({ canGenerate, onGenerateRoutes }) {
  return (
    <section style={styles.card}>
      <div style={styles.cardLabel}>Étape 4</div>

      <div style={styles.actionsColumn}>
        <button
          style={{
            ...styles.primaryButton,
            opacity: canGenerate ? 1 : 0.5,
            cursor: canGenerate ? "pointer" : "not-allowed",
          }}
          disabled={!canGenerate}
          onClick={onGenerateRoutes}
        >
          Générer les propositions d’itinéraires
        </button>

        <div style={styles.infoPillSoft}>
          Le réseau routier est téléchargé depuis OpenStreetMap, c’est l’étape la plus longue
          (souvent une à deux minutes). Il reste ensuite en mémoire : une nouvelle génération
          au même endroit avec la même distance est quasi immédiate.
        </div>
      </div>
    </section>
  );
}
