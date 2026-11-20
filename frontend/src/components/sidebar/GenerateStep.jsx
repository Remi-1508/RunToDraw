import ServiceStatus from "./ServiceStatus";
import StepHeader from "./StepHeader";
import { styles } from "./styles";

// Étape 4 : lancement de la génération des itinéraires.
export default function GenerateStep({ canGenerate, onGenerateRoutes, serviceStatus }) {
  return (
    <section style={styles.card}>
      <StepHeader step={4} title="Lancer le calcul" />

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
          Générer le parcours
        </button>

        <div style={styles.infoPillSoft}>
          Le réseau routier est téléchargé depuis OpenStreetMap, c’est l’étape la plus longue
          (souvent une à deux minutes). Il reste ensuite en mémoire : une nouvelle génération
          au même endroit avec la même distance est quasi immédiate.
        </div>

        <ServiceStatus status={serviceStatus} />
      </div>
    </section>
  );
}
