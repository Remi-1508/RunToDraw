import { useMemo, useState } from "react";
import { MAX_TEXT_LENGTH, SHAPES } from "../../config";
import { useIsMobile } from "../../hooks/useIsMobile";
import DrawingCanvas from "./DrawingCanvas";
import DrawingModal from "./DrawingModal";
import ShapeIcon from "./ShapeIcon";
import StepHeader from "./StepHeader";
import { styles } from "./styles";

// Texte en majuscules sans accents : ce que le moteur dessinera réellement (seuls A-Z et 0-9 existent).
function toDrawableText(value) {
  return value.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
}

// Étape 3 : choix d'une forme prédéfinie ou d'un texte à dessiner.
export default function DrawingStep({ drawing, setDrawing }) {
  const isMobile = useIsMobile();
  const [fullscreen, setFullscreen] = useState(false);
  const setPoints = (points) => setDrawing((current) => ({ ...current, mode: "custom", points }));

  // Aide dynamique : indique si la longueur du mot saisi est raisonnable pour le calcul.
  const textHelper = useMemo(() => {
    const clean = (drawing.text || "").trim();
    const letterCount = clean.replace(/\s+/g, "").length;

    if (!clean) return "Mieux vaut viser un mot très court, idéalement 3 lettres maximum.";
    if (letterCount <= 3) return `${letterCount} lettre${letterCount > 1 ? "s" : ""} · bon compromis pour le calcul.`;
    return `${letterCount} lettres · au-delà de 3, le temps peut devenir très long et le résultat moins bon.`;
  }, [drawing.text]);

  return (
    <section style={styles.card}>
      <StepHeader step={3} title="Forme, texte ou dessin" />

      <div style={styles.modeTabs}>
        <button
          type="button"
          style={drawing.mode === "shape" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setDrawing((current) => ({ ...current, mode: "shape" }))}
        >
          Forme
        </button>

        <button
          type="button"
          style={drawing.mode === "text" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setDrawing((current) => ({ ...current, mode: "text" }))}
        >
          Texte
        </button>

        <button
          type="button"
          style={drawing.mode === "custom" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setDrawing((current) => ({ ...current, mode: "custom" }))}
        >
          Dessin
        </button>
      </div>

      {drawing.mode === "shape" ? (
        <div style={styles.shapeGrid}>
          {SHAPES.map((shape) => {
            const active = drawing.shape === shape.id;

            return (
              <button
                key={shape.id}
                type="button"
                style={active ? styles.shapeButtonActive : styles.shapeButton}
                onClick={() => setDrawing((current) => ({ ...current, mode: "shape", shape: shape.id }))}
              >
                <span style={styles.shapeIcon}>
                  <ShapeIcon shape={shape.id} />
                </span>
                <span style={styles.shapeLabel}>{shape.label}</span>
              </button>
            );
          })}
        </div>
      ) : drawing.mode === "custom" ? (
        <>
          <DrawingCanvas points={drawing.points} onChange={setPoints} />
          {isMobile ? (
            <button type="button" style={styles.drawFullscreen} onClick={() => setFullscreen(true)}>
              Dessiner en plein écran
            </button>
          ) : null}
          {fullscreen ? (
            <DrawingModal points={drawing.points} onChange={setPoints} onClose={() => setFullscreen(false)} />
          ) : null}
        </>
      ) : (
        <div style={styles.textBlock}>
          <input
            style={styles.input}
            value={drawing.text}
            maxLength={MAX_TEXT_LENGTH}
            onChange={(event) =>
              setDrawing((current) => ({ ...current, mode: "text", text: toDrawableText(event.target.value) }))
            }
            placeholder="Ex : P2I"
          />

          <div style={styles.textHintStrong}>Conseil : privilégie des mots de 3 lettres maximum.</div>

          <div style={styles.textHint}>{textHelper}</div>
        </div>
      )}
    </section>
  );
}
