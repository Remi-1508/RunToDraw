// Icônes en traits (même famille que le reste de l'interface, à la place des emojis).
function Icon({ children }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  );
}

const PENCIL = <path d="M4 20l1-4L16.5 4.5a2 2 0 0 1 3 3L8 19zM14.5 6.5l3 3" />;
const CHECK = <path d="M5 12.5l4.5 4.5L19 7.5" />;
const UNDO = <path d="M9 8L5 12l4 4M5 12h9a5 5 0 0 1 0 8" />;
const REDO = <path d="M15 8l4 4-4 4M19 12h-9a5 5 0 0 0 0 8" />;
const TRASH = <path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12" />;
const RESET = <path d="M4 12a8 8 0 1 0 2.6-5.9M4 4v4h4" />;

// Barre d'outils d'édition, posée en bas de la carte : active le mode « Modifier » puis donne accès à
// annuler / rétablir, à la suppression du point sélectionné et au retour au tracé d'origine.
export default function RouteEditToolbar({
  editMode,
  onToggleEditMode,
  pending,
  canUndo,
  canRedo,
  canReset,
  hasSelection,
  isEdited,
  onUndo,
  onRedo,
  onReset,
  onDeleteSelected,
}) {
  return (
    <div style={styles.wrap}>
      <div style={styles.bar}>
        <button
          type="button"
          onClick={onToggleEditMode}
          style={editMode ? { ...styles.main, ...styles.mainActive } : styles.main}
          aria-pressed={editMode}
          title="Déplacer, ajouter ou supprimer des points du tracé"
        >
          <Icon>{editMode ? CHECK : PENCIL}</Icon>
          {editMode ? "Terminer" : "Modifier le tracé"}
        </button>

        {editMode && (
          <div style={styles.group} role="group" aria-label="Outils de modification">
            <button type="button" onClick={onUndo} disabled={!canUndo || pending} style={styles.tool} title="Annuler (Ctrl+Z)" aria-label="Annuler">
              <Icon>{UNDO}</Icon>
            </button>
            <button type="button" onClick={onRedo} disabled={!canRedo || pending} style={{ ...styles.tool, ...styles.toolSeparated }} title="Rétablir (Ctrl+Y)" aria-label="Rétablir">
              <Icon>{REDO}</Icon>
            </button>
            <button
              type="button"
              onClick={onDeleteSelected}
              disabled={!hasSelection || pending}
              style={{ ...styles.tool, ...styles.toolSeparated }}
              title="Supprimer le point sélectionné (Suppr)"
              aria-label="Supprimer le point sélectionné"
            >
              <Icon>{TRASH}</Icon>
            </button>
            <button type="button" onClick={onReset} disabled={!canReset || pending} style={{ ...styles.tool, ...styles.toolSeparated }} title="Revenir au tracé généré">
              <Icon>{RESET}</Icon>
              Origine
            </button>
          </div>
        )}
      </div>

      {editMode && (
        <div style={styles.hint} role="status">
          {pending
            ? "Recalcul du tracé sur les routes…"
            : isEdited
              ? "Tracé modifié · glisse un point pour le déplacer, tire sur le tracé pour en ajouter un."
              : "Glisse un point pour le déplacer, tire sur le tracé pour en ajouter un, clique sur un point puis Suppr pour l’enlever."}
        </div>
      )}
    </div>
  );
}

// Même famille visuelle que les boutons posés sur la carte (MapView) : bordure de 2 px, ombre forte,
// hauteur de 44 px, texte en gras. Le bouton principal passe à l'orange quand le mode édition est actif.
const controlBase = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 8,
  minHeight: 44,
  fontSize: 14,
  fontWeight: 700,
  whiteSpace: "nowrap",
  color: "var(--text)",
};

const styles = {
  wrap: {
    position: "absolute",
    left: "50%",
    bottom: 24,
    transform: "translateX(-50%)",
    zIndex: 1000,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    width: "max-content",
    maxWidth: "calc(100% - 32px)",
  },

  bar: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },

  main: {
    ...controlBase,
    padding: "0 16px",
    border: "2px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay-strong)",
    boxShadow: "var(--shadow-strong)",
    cursor: "pointer",
  },

  mainActive: {
    background: "var(--accent)",
    borderColor: "var(--accent)",
    color: "var(--on-accent)",
  },

  // Les outils sont regroupés dans une seule capsule : ils se lisent comme un ensemble.
  group: {
    display: "inline-flex",
    overflow: "hidden",
    border: "2px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay-strong)",
    boxShadow: "var(--shadow-strong)",
  },

  tool: {
    ...controlBase,
    minWidth: 44,
    padding: "0 12px",
    border: "none",
    borderRadius: 0,
    background: "transparent",
    cursor: "pointer",
  },

  toolSeparated: {
    borderLeft: "1px solid var(--border)",
  },

  hint: {
    maxWidth: 420,
    padding: "8px 14px",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay-strong)",
    border: "2px solid var(--border)",
    boxShadow: "var(--shadow-strong)",
    color: "var(--text-soft)",
    fontSize: 13,
    fontWeight: 600,
    lineHeight: 1.4,
    textAlign: "center",
  },
};
