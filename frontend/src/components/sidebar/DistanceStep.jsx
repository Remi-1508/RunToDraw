import { useEffect, useState } from "react";
import { MIN_DISTANCE_KM } from "../../config";
import StepHeader from "./StepHeader";
import { styles } from "./styles";

// Durée d'affichage du message « limite atteinte ».
const LIMIT_NOTICE_MS = 5000;

// Étape 2 : distance à parcourir, bornée entre le minimum et le maximum accepté par le serveur.
// Quand la personne essaie de dépasser le maximum (clic sur +, ou valeur saisie trop grande), un message
// explique la limite au lieu de ne rien faire.
export default function DistanceStep({ distanceKm, setDistanceKm, maxDistanceKm }) {
  const [limitHit, setLimitHit] = useState(false);

  useEffect(() => {
    if (!limitHit) return undefined;
    const timer = setTimeout(() => setLimitHit(false), LIMIT_NOTICE_MS);
    return () => clearTimeout(timer);
  }, [limitHit]);

  const atMax = distanceKm >= maxDistanceKm;

  function change(value) {
    const rounded = Math.round(value) || MIN_DISTANCE_KM;
    setLimitHit(rounded > maxDistanceKm);
    setDistanceKm(Math.min(Math.max(rounded, MIN_DISTANCE_KM), maxDistanceKm));
  }

  return (
    <section style={styles.card}>
      <StepHeader step={2} title="Distance à parcourir">
        <div style={styles.distanceBadge}>{distanceKm} km</div>
      </StepHeader>

      <div style={styles.stepperRow}>
        <button style={styles.stepperButton} onClick={() => change(distanceKm - 1)} aria-label="Diminuer la distance">
          −
        </button>

        <input
          style={styles.inputCenter}
          type="number"
          min={MIN_DISTANCE_KM}
          max={maxDistanceKm}
          step={1}
          value={distanceKm}
          onChange={(event) => change(Number(event.target.value))}
        />

        {/* Au maximum, le bouton + reste cliquable (pour afficher le message) mais prend l'aspect d'un bouton grisé. */}
        <button
          style={{ ...styles.stepperButton, ...(atMax ? styles.stepperButtonLimit : null) }}
          onClick={() => change(distanceKm + 1)}
          aria-label="Augmenter la distance"
          aria-disabled={atMax}
        >
          +
        </button>
      </div>

      {limitHit ? (
        <div style={styles.limitNotice} role="status">
          Tu as atteint la distance maximale : {maxDistanceKm} km. Au-delà, le calcul dépasserait les capacités du
          serveur.
        </div>
      ) : null}
    </section>
  );
}
