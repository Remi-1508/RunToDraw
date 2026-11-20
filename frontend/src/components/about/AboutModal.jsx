import { useEffect, useRef } from "react";

const GITHUB_URL = "https://github.com/Remi-1508/RunToDraw";
const LINKEDIN_URL = "https://www.linkedin.com/in/remi-monier-ensc";

// Technologies listées dans la présentation (une ligne chacune, pour rester lisible).
const STACK = [
  ["Interface", "React, Vite, Leaflet"],
  ["Serveur", "Python, FastAPI, NetworkX, NumPy"],
  ["Données", "OpenStreetMap (via l’API Overpass)"],
  ["Hébergement", "Vercel (interface) et Render (serveur)"],
];

// Fenêtre « À propos » : présentation du projet, du cadre P2I, et informations de confidentialité.
// Se ferme avec la croix, la touche Échap ou un clic à côté.
export default function AboutModal({ open, onClose }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div style={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div style={styles.panel} role="dialog" aria-modal="true" aria-labelledby="rtd-about-title">
        <div style={styles.header}>
          <h2 id="rtd-about-title" className="rtd-display" style={styles.title}>
            À propos de RunToDraw
          </h2>
          <button ref={closeRef} type="button" style={styles.close} onClick={onClose} aria-label="Fermer">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div style={styles.body}>
          <section style={styles.section}>
            <h3 style={styles.heading}>Le projet</h3>
            <p style={styles.text}>
              RunToDraw génère des itinéraires de course à pied ou de marche qui dessinent une forme, un dessin libre ou
              un mot sur la carte, en n’empruntant que des routes et des chemins qui existent vraiment. Tu choisis un
              départ, une distance et un dessin : l’application propose plusieurs parcours, avec à chaque fois un
              compromis entre ressemblance au dessin et distance parcourue, puis tu les exportes en GPX pour les
              suivre avec ta montre ou ton application de sport.
            </p>
          </section>

          <section style={styles.section}>
            <h3 style={styles.heading}>Comment ça marche</h3>
            <p style={styles.text}>
              Le réseau routier autour de ton départ est récupéré dans OpenStreetMap et transformé en graphe
              (carrefours et tronçons). Le dessin est ensuite placé, tourné et mis à l’échelle sur ce graphe, puis
              relié par des plus courts chemins. L’application teste de nombreuses positions et orientations et garde
              les parcours qui collent le mieux au dessin, à la distance demandée.
            </p>
          </section>

          <section style={styles.section}>
            <h3 style={styles.heading}>Un projet P2I</h3>
            <p style={styles.text}>
              RunToDraw est un Projet Informatique Individuel (P2I), réalisé par Rémi Monier pendant ses études
              d’ingénieur à l’ENSC (École nationale supérieure de cognitique, Bordeaux INP). L’objectif : concevoir
              de bout en bout une application complète, de l’algorithme de graphes à l’interface publiée en ligne.
            </p>
            <dl style={styles.stack}>
              {STACK.map(([label, value]) => (
                <div key={label} style={styles.stackRow}>
                  <dt style={styles.stackLabel}>{label}</dt>
                  <dd style={styles.stackValue}>{value}</dd>
                </div>
              ))}
            </dl>
            <p style={styles.links}>
              <a href={GITHUB_URL} target="_blank" rel="noreferrer" style={styles.link}>
                Code source sur GitHub
              </a>
              <a href={LINKEDIN_URL} target="_blank" rel="noreferrer" style={styles.link}>
                Rémi Monier sur LinkedIn
              </a>
            </p>
          </section>

          <section style={styles.section}>
            <h3 style={styles.heading}>Confidentialité</h3>
            <ul style={styles.list}>
              <li>Pas de compte, pas de publicité, pas de traceur : ton navigateur ne garde que tes préférences d’affichage.</li>
              <li>
                Ta position n’est utilisée que si tu la demandes, ou si tu choisis un départ sur la carte. Elle sert à
                calculer le parcours et n’est pas enregistrée : le serveur ne garde la zone calculée que quelques
                minutes en mémoire.
              </li>
              <li>
                Pour fonctionner, l’application interroge des services tiers : la recherche d’adresse (Géoplateforme
                de l’IGN, Photon, Geoapify), le relief (IGN, Open-Meteo), les fonds de carte (OpenStreetMap) et les
                polices (Google Fonts).
              </li>
            </ul>
          </section>

          <section style={styles.section}>
            <h3 style={styles.heading}>Crédits</h3>
            <p style={styles.text}>
              Cartes et routes : ©{" "}
              <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" style={styles.link}>
                contributeurs OpenStreetMap
              </a>
              , données sous licence ODbL. Les parcours sont donnés à titre indicatif : vérifie toujours que le chemin
              est praticable et respecte le code de la route.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

const styles = {
  backdrop: {
    position: "fixed",
    inset: 0,
    zIndex: 3100,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    background: "rgba(8, 12, 18, 0.55)",
  },

  panel: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    maxWidth: 560,
    maxHeight: "min(88vh, 760px)",
    borderRadius: "var(--radius)",
    border: "1px solid var(--border)",
    background: "var(--bg-elevated)",
    boxShadow: "var(--shadow-strong)",
    color: "var(--text)",
  },

  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    padding: "16px 18px 12px",
    borderBottom: "1px solid var(--border-subtle)",
  },

  title: { margin: 0, fontSize: 22, fontWeight: 900 },

  close: {
    display: "grid",
    placeItems: "center",
    width: 36,
    height: 36,
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "transparent",
    color: "var(--text)",
    cursor: "pointer",
  },

  body: { overflowY: "auto", padding: "6px 18px 18px" },
  section: { marginTop: 16 },
  heading: { margin: "0 0 6px", fontSize: 15, fontWeight: 800 },
  text: { margin: 0, fontSize: 14, lineHeight: 1.55, color: "var(--text-soft)" },

  stack: { margin: "12px 0 0", display: "grid", gap: 6 },
  stackRow: { display: "flex", gap: 10, fontSize: 13.5 },
  stackLabel: { flex: "0 0 96px", margin: 0, fontWeight: 700 },
  stackValue: { margin: 0, color: "var(--text-soft)" },

  links: { display: "flex", flexWrap: "wrap", gap: 16, margin: "12px 0 0", fontSize: 14 },
  link: { color: "var(--accent-text)", fontWeight: 700 },

  list: { margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 14, lineHeight: 1.55, color: "var(--text-soft)" },
};
