import ServiceStatus from "./ServiceStatus";
import StepHeader from "./StepHeader";
import { styles } from "./styles";

// Étape 4 : lancement de la génération des itinéraires.
export default function GenerateStep({
  canGenerate,
  onGenerateRoutes,
  serviceStatus,
  showThroughStart,
  throughStart,
  onThroughStartChange,
}) {
  return (
    <section style={styles.card}>
      <StepHeader step={4} title="Lancer le calcul" />

      <div style={styles.actionsColumn}>
        {/* Formes et dessin libre : imposer le départ. Les mots ne sont pas concernés (une lettre part où elle veut). */}
        {showThroughStart ? (
          <label style={styles.checkRow}>
            <input
              type="checkbox"
              style={styles.checkBox}
              checked={Boolean(throughStart)}
              onChange={(event) => onThroughStartChange(event.target.checked)}
            />
            <span>
              <strong>Passer par mon point de départ</strong>
              <span style={styles.checkHint}>
                Le parcours part et revient de ton départ. Sans la case, le meilleur tracé est proposé en premier, même
                s’il ne passe pas par là.
              </span>
            </span>
          </label>
        ) : null}

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
          Le réseau routier est préchargé depuis OpenStreetMap dès que tu as choisi le départ, la distance
          et le dessin : la génération est plus rapide si tu patientes quelques secondes avant de cliquer.
        </div>

        <ServiceStatus status={serviceStatus} />
      </div>
    </section>
  );
}
