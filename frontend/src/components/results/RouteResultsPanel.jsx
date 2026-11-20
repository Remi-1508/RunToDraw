import { useState } from "react";
import StepHeader from "../sidebar/StepHeader";
import ElevationStat from "./ElevationStat";
import RouteThumbnail from "./RouteThumbnail";

// Cette petite fonction transforme une distance en mètres
// en une chaîne lisible en kilomètres.
function formatKm(meters) {
  return `${(meters / 1000).toFixed(2)} km`;
}

// RouteResultsPanel affiche les propositions d’itinéraires renvoyées par le backend.
//
// Il a deux rôles principaux :
// 1) permettre à l’utilisateur de comparer et choisir un itinéraire généré
// 2) permettre à l’utilisateur d’exporter l’itinéraire sélectionné dans un format utilisable
//
// Ce composant ne calcule pas lui-même les trajets.
// Il se contente d’afficher les résultats de manière claire et exploitable.
export default function RouteResultsPanel({
  routePlan,
  selectedRouteId,
  onSelectRoute,
  onExportRoute,
  onClearRoute,
  onShareRoute,
}) {
  const selectedRoute = routePlan?.routes?.find((route) => route.id === selectedRouteId) ?? null;
  // Lettres séparées : un fichier GPX par lettre (chaque lettre est un itinéraire distinct).
  const letterSegments = selectedRoute?.separate ? selectedRoute.segments : null;
  // Propositions secondaires (ex. « mot entier » en mode texte) : repliées par défaut.
  const [showOthers, setShowOthers] = useState(false);
  // Si aucune génération d’itinéraire n’a encore été lancée,
  // on affiche une carte d’attente plus discrète.
  if (!routePlan) {
    return (
      <section style={styles.cardMuted}>
        <StepHeader step={5} title="Choix de l’itinéraire" />
        <div style={styles.helperText}>
          Lance une génération pour afficher ici les propositions d’itinéraires et les exports.
        </div>
      </section>
    );
  }

  const primaryRoutes = routePlan.routes.filter((route) => !route.secondary);
  const secondaryRoutes = routePlan.routes.filter((route) => route.secondary);
  const othersOpen = showOthers;

  function renderRouteCard(route) {
    const active = route.id === selectedRouteId;

    return (
      <button
        key={route.id}
        type="button"
        onClick={() => onSelectRoute(route.id)}
        style={active ? styles.routeCardActive : styles.routeCard}
      >
        <div style={styles.routeHeader}>
          <RouteThumbnail segments={route.segments} />
          <div style={styles.routeInfo}>
            {/* Libellé principal du trajet, par exemple une forme ou un mode texte. */}
            <div style={styles.routeLabel}>{route.label}</div>
            {route.includes_start ? (
              <div style={styles.startBadge}>Part et revient à ton point de départ</div>
            ) : null}
            {route.edited ? <div style={styles.startBadge}>Modifié à la main</div> : null}

            {/* Information secondaire décrivant la variante de l’itinéraire. */}
            <div style={styles.routeMeta}>{route.variant}</div>
          </div>

          {/* Distance affichée à droite, en grand. */}
          <div style={styles.distanceBadge}>{formatKm(route.total_distance_m)}</div>
        </div>

        {/* Dénivelé positif du tracé (estimé à partir d'un modèle de terrain, voir api/elevation.js). */}
        <div style={styles.routeStatsRow}>
          <ElevationStat route={route} />
        </div>

        {/*
           En mode texte, un itinéraire peut contenir un résultat par lettre.
           Ces petites pastilles rendent la lecture des distances lettre par lettre plus simple.
        */}
        {route.letters?.length && !route.edited ? (
          <div style={styles.lettersWrap}>
            {route.letters.map((letter, index) => (
              <div key={`${letter.letter}-${index}`} style={styles.letterPill}>
                {letter.letter} · {formatKm(letter.distance_m)}
              </div>
            ))}
          </div>
        ) : null}
      </button>
    );
  }

  return (
    <section style={styles.card}>
      {/* Présentation générale de l’étape de sélection d’itinéraire. */}
      <StepHeader step={5} title="Choisir un itinéraire" />
      <div style={styles.helperText}>{routePlan.summary}</div>
      <div style={styles.secondaryActions}>
        {onShareRoute ? (
          <button type="button" style={styles.secondaryButton} onClick={onShareRoute}>
            Partager ce parcours
          </button>
        ) : null}
        <button type="button" style={styles.secondaryButton} onClick={onClearRoute}>
          Effacer le tracé
        </button>
      </div>

      {/*
         Chaque itinéraire est affiché sous forme de carte cliquable.
         L’itinéraire actuellement sélectionné est visuellement mis en avant.
      */}
      <div style={styles.routesColumn}>{primaryRoutes.map(renderRouteCard)}</div>

      {secondaryRoutes.length ? (
        <div style={styles.othersZone}>
          <button
            type="button"
            style={styles.othersToggle}
            onClick={() => setShowOthers(!othersOpen)}
            aria-expanded={othersOpen}
          >
            <span>
              {othersOpen ? "Masquer" : "Voir"} les autres propositions ({secondaryRoutes.length})
            </span>
            <span style={styles.othersChevron}>{othersOpen ? "▴" : "▾"}</span>
          </button>
          {othersOpen ? (
            <>
              <div style={styles.othersHint}>
                Le mot entier dessiné en un seul itinéraire de la distance demandée : plus court,
                mais les lettres sont plus petites et moins lisibles.
              </div>
              <div style={styles.routesColumn}>{secondaryRoutes.map(renderRouteCard)}</div>
            </>
          ) : null}
        </div>
      ) : null}


      {/*
         Zone d’export.
         L’itinéraire sélectionné peut être téléchargé dans différents formats
         selon l’application cible.
      */}
      <div style={styles.exportZone}>
        <StepHeader step={6} title="Exporter vers ton appli GPS" />

        {letterSegments ? (
          <div style={styles.exportHint}>
            Un fichier GPX par lettre : chaque lettre est un itinéraire à part.
          </div>
        ) : null}

        <div style={styles.exportButtons}>
          {letterSegments && letterSegments.length > 1 ? (
            <button
              type="button"
              style={{ ...styles.exportButton, ...styles.exportButtonWide }}
              onClick={() => onExportRoute("zip")}
            >
              Toutes les lettres (ZIP)
            </button>
          ) : null}

          {letterSegments ? (
            letterSegments.map((segment, index) => (
              <button
                key={`${segment.label}-${index}`}
                type="button"
                style={styles.exportButton}
                onClick={() => onExportRoute("gpx", index)}
              >
                GPX lettre {segment.label}
              </button>
            ))
          ) : (
            <button
              type="button"
              style={styles.exportButton}
              onClick={() => onExportRoute("gpx")}
            >
              GPX (Strava)
            </button>
          )}

          <button
            type="button"
            style={styles.exportButton}
            onClick={() => onExportRoute("kml")}
          >
            KML (Google My Maps)
          </button>
        </div>
      </div>
    </section>
  );
}

// Ces styles définissent la mise en forme de la carte,
// des cartes d’itinéraires, des petites pastilles de métriques,
// et des boutons d’export.
//
// L’objectif est de rendre la comparaison rapide et lisible,
// sans surcharger la sidebar.
const styles = {
  card: {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: 18,
    boxShadow: "var(--shadow-soft)",
  },

  // Actions secondaires sous la liste : partager le lien, ou effacer les propositions (le départ est conservé).
  secondaryActions: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 12,
  },

  secondaryButton: {
    flex: "1 1 140px",
    minHeight: "var(--control-h)",
    border: "2px solid var(--border-strong)",
    borderRadius: "var(--radius-sm)",
    background: "transparent",
    color: "var(--text)",
    fontWeight: 700,
    fontSize: 14,
    cursor: "pointer",
  },

  cardMuted: {
    background: "var(--card-muted)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "var(--radius)",
    padding: 18,
    boxShadow: "var(--shadow-soft)",
  },

  helperText: {
    marginTop: 8,
    color: "var(--text-soft)",
    lineHeight: 1.5,
    fontSize: 13.5,
  },

  routesColumn: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    marginTop: 14,
  },

  // Style par défaut d’une carte de proposition d’itinéraire.
  routeCard: {
    width: "100%",
    border: "1px solid var(--border-subtle)",
    background: "var(--overlay)",
    borderRadius: "var(--radius)",
    padding: 14,
    color: "var(--text)",
    cursor: "pointer",
    textAlign: "left",
  },

  // Style mis en avant pour l’itinéraire actuellement sélectionné.
  routeCardActive: {
    width: "100%",
    border: "2px solid var(--accent)",
    background: "var(--bg-elevated)",
    borderRadius: "var(--radius)",
    padding: 14,
    color: "var(--text)",
    cursor: "pointer",
    textAlign: "left",
  },

  routeHeader: {
    display: "flex",
    gap: 12,
    alignItems: "center",
  },

  routeInfo: {
    flex: 1,
    minWidth: 0,
  },

  routeLabel: {
    fontWeight: 800,
    fontSize: 15,
  },

  routeMeta: {
    fontSize: 12.5,
    color: "var(--text-soft)",
    marginTop: 4,
  },

  distanceBadge: {
    borderRadius: 999,
    padding: "8px 10px",
    background: "var(--chip)",
    color: "var(--accent-text)",
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontStretch: "112%",
    fontWeight: 900,
    fontSize: 17,
    whiteSpace: "nowrap",
  },

  routeStatsRow: {
    marginTop: 10,
    display: "flex",
    flexWrap: "wrap",
    gap: 10,
    fontSize: 12.5,
    color: "var(--text-soft)",
  },

  startBadge: {
    marginTop: 6,
    display: "inline-block",
    fontSize: 12,
    fontWeight: 700,
    color: "var(--success-strong)",
    background: "var(--success-soft)",
    borderRadius: 999,
    padding: "3px 10px",
  },

  othersZone: {
    marginTop: 12,
  },

  othersToggle: {
    width: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
    padding: "10px 14px",
    borderRadius: "var(--radius-sm)",
    border: "1px dashed var(--border-strong)",
    background: "transparent",
    color: "var(--text-soft)",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },

  othersChevron: {
    fontSize: 12,
  },

  othersHint: {
    margin: "10px 2px",
    fontSize: 12,
    color: "var(--text-soft)",
    lineHeight: 1.45,
  },

  exportHint: {
    fontSize: 13,
    color: "var(--text-soft)",
    marginTop: 6,
  },

  lettersWrap: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 12,
  },

  letterPill: {
    borderRadius: 999,
    padding: "8px 10px",
    background: "var(--chip)",
    fontSize: 12,
    fontWeight: 700,
  },

  exportZone: {
    marginTop: 18,
  },

  exportButtons: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: 10,
    marginTop: 12,
  },

  exportButton: {
    width: "100%",
    border: "none",
    background: "var(--accent)",
    color: "var(--on-accent)",
    borderRadius: "var(--radius-sm)",
    padding: "14px 16px",
    fontWeight: 800,
    cursor: "pointer",
  },

  // « Toutes les lettres » : l'action principale de l'export d'un mot, mise en avant.
  exportButtonWide: {
    minHeight: "var(--control-h)",
    fontSize: 16,
  },
};