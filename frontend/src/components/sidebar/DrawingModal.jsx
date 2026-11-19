import { useEffect } from "react";
import DrawingCanvas from "./DrawingCanvas";
import { styles } from "./styles";

// Dessin en plein écran (smartphone) : la zone de dessin du tiroir est trop petite pour tracer au doigt
// avec précision. On affiche la même zone en grand, par-dessus tout, avec un bouton pour terminer.
export default function DrawingModal({ points, onChange, onClose }) {
  // Empêche la page située dessous de défiler pendant qu'on dessine.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  return (
    <div style={styles.drawModal} role="dialog" aria-modal="true" aria-label="Dessin en plein écran">
      <div style={styles.drawModalHeader}>
        <span className="rtd-display" style={styles.drawModalTitle}>
          Dessine ton parcours
        </span>
        <button type="button" style={styles.drawModalDone} onClick={onClose}>
          Terminer
        </button>
      </div>
      <div style={styles.drawModalBody}>
        <DrawingCanvas points={points} onChange={onChange} />
      </div>
    </div>
  );
}
