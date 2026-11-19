import { useRef, useState } from "react";
import { DRAW_AREA_SIZE, MAX_DRAW_POINTS, MIN_DRAW_POINTS } from "../../config";
import { styles } from "./styles";

// Distance minimale (dans le repère de la zone de dessin) entre deux points enregistrés :
// un tracé à la souris produit des dizaines de points par centimètre, inutiles pour le moteur.
const MIN_POINT_SPACING = 3;

// Transforme les points en tracé SVG ("M x y L x y …").
function toPath(points) {
  return points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
}

// Zone de dessin libre : l'utilisateur trace UN seul trait continu (le parcours sera un seul chemin).
// Commencer un nouveau trait remplace le précédent. Souris, doigt et stylet passent par les mêmes événements
// « pointer ». Pendant le tracé les points restent locaux à ce composant ; ils ne sont transmis au reste de
// l'application qu'à la fin du trait, pour ne pas redessiner toute l'interface à chaque mouvement.
export default function DrawingCanvas({ points, onChange }) {
  const svgRef = useRef(null);
  const strokeRef = useRef(null); // trait en cours (tableau de points), null si on ne dessine pas
  const [live, setLive] = useState(null);

  const shown = live ?? points ?? [];

  // Position du pointeur dans le repère de la zone de dessin (indépendant de sa taille à l'écran).
  function toLocal(event) {
    const rect = svgRef.current.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * DRAW_AREA_SIZE;
    const y = ((event.clientY - rect.top) / rect.height) * DRAW_AREA_SIZE;
    return [Math.min(Math.max(x, 0), DRAW_AREA_SIZE), Math.min(Math.max(y, 0), DRAW_AREA_SIZE)];
  }

  function handlePointerDown(event) {
    if (event.button !== undefined && event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    strokeRef.current = [toLocal(event)];
    setLive([...strokeRef.current]);
  }

  function handlePointerMove(event) {
    const stroke = strokeRef.current;
    if (!stroke || stroke.length >= MAX_DRAW_POINTS) return;
    const point = toLocal(event);
    const last = stroke[stroke.length - 1];
    if (Math.hypot(point[0] - last[0], point[1] - last[1]) < MIN_POINT_SPACING) return;
    stroke.push(point);
    setLive([...stroke]);
  }

  function handlePointerUp() {
    const stroke = strokeRef.current;
    strokeRef.current = null;
    setLive(null);
    // Un simple clic (un seul point) n'efface pas un dessin existant.
    if (stroke && stroke.length > 1) onChange(stroke);
  }

  const enough = shown.length >= MIN_DRAW_POINTS;

  return (
    <div style={styles.drawBlock}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${DRAW_AREA_SIZE} ${DRAW_AREA_SIZE}`}
        style={styles.drawArea}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onContextMenu={(event) => event.preventDefault()}
        role="img"
        aria-label="Zone de dessin : trace ta forme d'un seul trait avec la souris ou le doigt."
      >
        {/* Repères discrets : croix centrale. */}
        <path
          d={`M${DRAW_AREA_SIZE / 2} 0V${DRAW_AREA_SIZE}M0 ${DRAW_AREA_SIZE / 2}H${DRAW_AREA_SIZE}`}
          stroke="var(--border)"
          strokeWidth="1"
          strokeDasharray="4 6"
          fill="none"
        />
        {shown.length > 1 ? (
          <>
            <path d={toPath(shown)} fill="none" stroke="var(--route-casing)" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
            <path d={toPath(shown)} fill="none" stroke="var(--accent)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
          </>
        ) : null}
        {shown.length > 0 ? <circle cx={shown[0][0]} cy={shown[0][1]} r="6" fill="var(--text)" stroke="var(--route-casing)" strokeWidth="3" /> : null}
      </svg>

      <div style={styles.drawFooter}>
        <span style={styles.textHint} role="status">
          {shown.length === 0
            ? "Dessine ta forme d'un seul trait, sans lever le doigt. Un nouveau trait remplace le précédent."
            : enough
              ? "Dessin prêt. Les formes simples (peu de détails) donnent les meilleurs parcours."
              : "Trait trop court : dessine une forme un peu plus grande."}
        </span>
        <button type="button" style={styles.drawClear} onClick={() => onChange([])} disabled={shown.length === 0}>
          Effacer
        </button>
      </div>
    </div>
  );
}
