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
          style={editMode ? styles.mainButtonDone : styles.mainButton}
          aria-pressed={editMode}
          title="Déplacer, ajouter ou supprimer des points du tracé"
        >
          <Icon>{editMode ? CHECK : PENCIL}</Icon>
          {editMode ? "Terminer" : "Modifier le tracé"}
        </button>

        {editMode && (
          <>
            <button type="button" onClick={onUndo} disabled={!canUndo || pending} style={styles.button} title="Annuler (Ctrl+Z)" aria-label="Annuler">
              <Icon>{UNDO}</Icon>
            </button>
            <button type="button" onClick={onRedo} disabled={!canRedo || pending} style={styles.button} title="Rétablir (Ctrl+Y)" aria-label="Rétablir">
              <Icon>{REDO}</Icon>
            </button>
            <button
              type="button"
              onClick={onDeleteSelected}
              disabled={!hasSelection || pending}
              style={styles.button}
              title="Supprimer le point sélectionné (Suppr)"
              aria-label="Supprimer le point sélectionné"
            >
              <Icon>{TRASH}</Icon>
            </button>
            <button type="button" onClick={onReset} disabled={!canReset || pending} style={styles.button} title="Revenir au tracé généré">
              <Icon>{RESET}</Icon>
              Origine
            </button>
          </>
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
    justifyContent: "center",
    gap: 4,
    padding: 4,
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay-strong)",
    boxShadow: "var(--shadow-soft)",
  },

  button: {
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    background: "var(--card)",
    color: "var(--text)",
    minHeight: 40,
    minWidth: 40,
    padding: "7px 10px",
    fontSize: 13,
    fontWeight: 700,
    whiteSpace: "nowrap",
  },

  buttonActive: {
    background: "var(--accent)",
    color: "var(--on-accent)",
    borderColor: "var(--accent)",
  },

  hint: {
    padding: "6px 12px",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay-strong)",
    border: "1px solid var(--border)",
    color: "var(--text-soft)",
    fontSize: 12,
    textAlign: "center",
  },
};
