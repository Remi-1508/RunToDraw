import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import DrawingCanvas from "./DrawingCanvas";
import { styles } from "./styles";

// Dessin en plein écran (smartphone) : la zone du tiroir est trop petite pour tracer au doigt avec précision.
// La fenêtre est rendue dans <body> (portail) : le tiroir est animé par une transformation CSS, et à
// l'intérieur d'un élément transformé, « position: fixed » se réfère au tiroir et non à l'écran, ce qui
// faisait déborder la fenêtre et cachait ses boutons.
// On en sort de trois façons naturelles : « Terminer », la croix, ou le geste/bouton « retour » du téléphone.
export default function DrawingModal({ points, onChange, onClose }) {
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  });

  // Empêche la page située dessous de défiler pendant qu'on dessine.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  // Le retour du téléphone ferme la fenêtre au lieu de quitter la page : on ajoute une entrée d'historique à
  // l'ouverture, et on la retire à la fermeture si c'est un autre moyen que « retour » qui a fermé.
  useEffect(() => {
    let closedByBack = false;
    window.history.pushState({ rtdDrawing: true }, "");
    const onPopState = () => {
      closedByBack = true;
      closeRef.current();
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") closeRef.current();
    };
    window.addEventListener("popstate", onPopState);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("popstate", onPopState);
      window.removeEventListener("keydown", onKeyDown);
      if (!closedByBack && window.history.state?.rtdDrawing) window.history.back();
    };
  }, []);

  return createPortal(
    <div style={styles.drawModal} role="dialog" aria-modal="true" aria-label="Dessin en plein écran">
      <div style={styles.drawModalHeader}>
        <button type="button" style={styles.drawModalClose} onClick={onClose} aria-label="Fermer le dessin">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
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
    </div>,
    document.body
  );
}
