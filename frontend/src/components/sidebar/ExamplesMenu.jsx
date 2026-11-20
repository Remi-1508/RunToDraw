import { useEffect, useRef, useState } from "react";
import { EXAMPLES } from "../../config";
import { styles } from "./styles";

// Petit bouton « i » de l'en-tête : il ouvre la liste des exemples (départ, distance et dessin déjà réglés).
// Choisir un exemple ferme la liste et lance la génération. Un clic ailleurs ou Échap la ferme aussi.
export default function ExamplesMenu({ onRunExample, disabled }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef}>
      <button
        type="button"
        className="rtd-collapse rtd-info"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label="Voir des exemples"
        title="Voir des exemples"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 11v5" />
          <circle cx="12" cy="7.8" r="0.6" fill="currentColor" />
        </svg>
      </button>

      {open ? (
        <div style={styles.examplesPopover} role="menu" aria-label="Exemples">
          {EXAMPLES.map((example) => (
            <button
              key={example.id}
              type="button"
              role="menuitem"
              style={styles.exampleButton}
              disabled={disabled}
              onClick={() => {
                setOpen(false);
                onRunExample(example);
              }}
            >
              <span style={styles.exampleName}>{example.title}</span>
              <span style={styles.exampleDetail}>{example.detail}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
