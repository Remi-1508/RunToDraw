/*
============================================================
EN:
This small helper converts a distance in meters into a readable
string in kilometers.

FR:
Cette petite fonction transforme une distance en mètres
en une chaîne lisible en kilomètres.
============================================================
*/
function formatKm(meters) {
  return `${(meters / 1000).toFixed(2)} km`;
}

/*
============================================================
EN:
RouteResultsPanel displays the route proposals returned by the backend.

It has two main roles:
1) let the user compare and choose one generated route
2) let the user export the selected route to a GPS-friendly format

This component does not compute routes itself.
It only displays the results in a clear and usable way.

FR:
RouteResultsPanel affiche les propositions d’itinéraires renvoyées par le backend.

Il a deux rôles principaux :
1) permettre à l’utilisateur de comparer et choisir un itinéraire généré
2) permettre à l’utilisateur d’exporter l’itinéraire sélectionné dans un format utilisable

Ce composant ne calcule pas lui-même les trajets.
Il se contente d’afficher les résultats de manière claire et exploitable.
============================================================
*/
export default function RouteResultsPanel({
  routePlan,
  selectedRouteId,
  onSelectRoute,
  onExportRoute,
}) {
  /*
  EN:
  If no route generation has been launched yet,
  we display a muted placeholder card.

  FR:
  Si aucune génération d’itinéraire n’a encore été lancée,
  on affiche une carte d’attente plus discrète.
  */
  if (!routePlan) {
    return (
      <section style={styles.cardMuted}>
        <div style={styles.cardLabel}>Étape 5</div>
        <div style={styles.cardTitle}>Choix de l’itinéraire</div>
        <div style={styles.helperText}>
          Lance une génération pour afficher ici les propositions d’itinéraires et les exports.
        </div>
      </section>
    );
  }

  return (
    <section style={styles.card}>
      {/* 
      EN: General introduction for the route selection step.
      FR: Présentation générale de l’étape de sélection d’itinéraire.
      */}
      <div style={styles.cardLabel}>Étape 5</div>
      <div style={styles.cardTitle}>Choisir un itinéraire</div>
      <div style={styles.helperText}>{routePlan.summary}</div>

      {/*
      EN:
      Each route is displayed as a clickable card.
      The currently selected route is visually highlighted.

      FR:
      Chaque itinéraire est affiché sous forme de carte cliquable.
      L’itinéraire actuellement sélectionné est visuellement mis en avant.
      */}
      <div style={styles.routesColumn}>
        {routePlan.routes.map((route) => {
          const active = route.id === selectedRouteId;

          return (
            <button
              key={route.id}
              type="button"
              onClick={() => onSelectRoute(route.id)}
              style={active ? styles.routeCardActive : styles.routeCard}
            >
              <div style={styles.routeHeader}>
                <div>
                  {/* 
                  EN: Main label of the route, for example a shape or a text mode.
                  FR: Libellé principal du trajet, par exemple une forme ou un mode texte.
                  */}
                  <div style={styles.routeLabel}>{route.label}</div>

                  {/* 
                  EN: Secondary information describing the route variant.
                  FR: Information secondaire décrivant la variante de l’itinéraire.
                  */}
                  <div style={styles.routeMeta}>{route.variant}</div>
                </div>

                {/* 
                EN: Main distance badge shown on the right.
                FR: Badge principal de distance affiché à droite.
                */}
                <div style={styles.distanceBadge}>{formatKm(route.total_distance_m)}</div>
              </div>

              {/* 
              EN:
              These quick metrics help compare routes without opening anything else.
              We keep them simple:
              - distance gap
              - shape error

              FR:
              Ces métriques rapides aident à comparer les trajets sans ouvrir autre chose.
              On reste sur des infos simples :
              - écart à la cible
              - erreur de forme
              */}
              <div style={styles.routeStatsRow}>
                <span>Écart cible : {Math.round(route.length_gap_m)} m</span>
                <span>Erreur forme : {route.shape_error.toFixed(1)}</span>
              </div>

              {/*
              EN:
              In text mode, a route may contain one result per letter.
              These small pills make the letter-by-letter distances easier to read.

              FR:
              En mode texte, un itinéraire peut contenir un résultat par lettre.
              Ces petites pastilles rendent la lecture des distances lettre par lettre plus simple.
              */}
              {route.letters?.length ? (
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
        })}
      </div>

      {/*
      EN:
      Export section.
      The selected route can be downloaded or opened in different formats
      depending on the target application.

      FR:
      Zone d’export.
      L’itinéraire sélectionné peut être téléchargé ou ouvert dans différents formats
      selon l’application cible.
      */}
      <div style={styles.exportZone}>
        <div style={styles.cardLabel}>Étape 6</div>
        <div style={styles.cardTitle}>Exporter pour une application GPS</div>

        <div style={styles.exportButtons}>
          <button
            type="button"
            style={styles.exportButton}
            onClick={() => onExportRoute("gpx")}
          >
            GPX (Strava)
          </button>

          <button
            type="button"
            style={styles.exportButton}
            onClick={() => onExportRoute("kml")}
          >
            KML (Google My Maps)
          </button>

          <button
            type="button"
            style={styles.exportButton}
            onClick={() => onExportRoute("google_maps")}
          >
            Lien Google Maps
          </button>
        </div>
      </div>
    </section>
  );
}

/*
============================================================
EN:
These styles define the card layout, route cards,
small metric pills, and export buttons.

The goal is to make comparison quick and readable,
without overloading the sidebar.

FR:
Ces styles définissent la mise en forme de la carte,
des cartes d’itinéraires, des petites pastilles de métriques,
et des boutons d’export.

L’objectif est de rendre la comparaison rapide et lisible,
sans surcharger la sidebar.
============================================================
*/
const styles = {
  card: {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 28,
    padding: 18,
    boxShadow: "var(--shadow-soft)",
    backdropFilter: "blur(18px)",
  },

  cardMuted: {
    background: "var(--card-muted)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 28,
    padding: 18,
    boxShadow: "var(--shadow-soft)",
  },

  cardLabel: {
    color: "var(--text-soft)",
    fontWeight: 700,
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
  },

  cardTitle: {
    fontSize: 19,
    fontWeight: 800,
    letterSpacing: -0.3,
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

  /*
  EN:
  Default style for one route proposal card.

  FR:
  Style par défaut d’une carte de proposition d’itinéraire.
  */
  routeCard: {
    width: "100%",
    border: "1px solid var(--border-subtle)",
    background: "var(--overlay)",
    borderRadius: 22,
    padding: 14,
    color: "var(--text)",
    cursor: "pointer",
    textAlign: "left",
  },

  /*
  EN:
  Highlighted style for the currently selected route.

  FR:
  Style mis en avant pour l’itinéraire actuellement sélectionné.
  */
  routeCardActive: {
    width: "100%",
    border: "1px solid transparent",
    background: "linear-gradient(135deg, rgba(10,132,255,0.14), rgba(111,184,255,0.18))",
    borderRadius: 22,
    padding: 14,
    color: "var(--text)",
    cursor: "pointer",
    textAlign: "left",
    boxShadow: "0 12px 24px rgba(0,122,255,0.16)",
  },

  routeHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "center",
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
    color: "var(--accent-strong)",
    fontWeight: 800,
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
    background: "var(--button-blue)",
    color: "white",
    borderRadius: 18,
    padding: "14px 16px",
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: "0 12px 24px rgba(0,122,255,0.22)",
  },
};