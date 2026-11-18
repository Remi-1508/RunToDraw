import { styles } from "./styles";

// En-tête d'une étape de la barre latérale : pastille numérotée + titre.
// La numérotation a du sens ici : les étapes se suivent vraiment (point de départ → distance → dessin → génération).
export default function StepHeader({ step, title, children }) {
  return (
    <div style={styles.cardHeader}>
      <div style={styles.stepHeader}>
        <span style={styles.stepBadge} aria-hidden="true">
          {step}
        </span>
        <h2 style={{ ...styles.cardTitle, margin: 0 }}>{title}</h2>
      </div>
      {children}
    </div>
  );
}
