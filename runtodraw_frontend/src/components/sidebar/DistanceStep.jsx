import { MIN_DISTANCE_KM } from "../../config";
import { styles } from "./styles";

// Étape 2 : distance à parcourir, bornée entre le minimum et le maximum accepté par le serveur.
export default function DistanceStep({ distanceKm, setDistanceKm, maxDistanceKm }) {
  const clamp = (value) => Math.min(Math.max(Math.round(value) || MIN_DISTANCE_KM, MIN_DISTANCE_KM), maxDistanceKm);

  return (
    <section style={styles.card}>
      <div style={styles.cardHeader}>
        <div>
          <div style={styles.cardLabel}>Étape 2</div>
          <div style={styles.cardTitle}>Distance à parcourir</div>
        </div>
        <div style={styles.distanceBadge}>{distanceKm} km</div>
      </div>

      <div style={styles.stepperRow}>
        <button style={styles.stepperButton} onClick={() => setDistanceKm(clamp(distanceKm - 1))}>
          −
        </button>

        <input
          style={styles.inputCenter}
          type="number"
          min={MIN_DISTANCE_KM}
          max={maxDistanceKm}
          step={1}
          value={distanceKm}
          onChange={(event) => setDistanceKm(clamp(Number(event.target.value)))}
        />

        <button style={styles.stepperButton} onClick={() => setDistanceKm(clamp(distanceKm + 1))}>
          +
        </button>
      </div>

      <div style={styles.infoPill}>
        Rayon d’extraction maximal : <strong>{(distanceKm / 2).toFixed(1)} km</strong>
        {" · "}distance maximale : {maxDistanceKm} km
      </div>
    </section>
  );
}
