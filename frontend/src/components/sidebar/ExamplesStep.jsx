import { EXAMPLES } from "../../config";
import { styles } from "./styles";

// Exemples en un clic : remplissent départ, distance et dessin, puis lancent la génération.
export default function ExamplesStep({ onRunExample, disabled }) {
  return (
    <section style={styles.card}>
      <div style={styles.exampleTitle}>Essayer un exemple</div>
      <div style={styles.exampleList}>
        {EXAMPLES.map((example) => (
          <button
            key={example.id}
            type="button"
            style={styles.exampleButton}
            disabled={disabled}
            onClick={() => onRunExample(example)}
          >
            <span style={styles.exampleName}>{example.title}</span>
            <span style={styles.exampleDetail}>{example.detail}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
