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
          style={{ ...styles.button, ...(editMode ? styles.buttonActive : null) }}
          aria-pressed={editMode}
          title="Déplacer, ajouter ou supprimer des points du tracé"
        >
          ✏️ {editMode ? "Terminer" : "Modifier le tracé"}
        </button>

        {editMode && (
          <>
            <button type="button" onClick={onUndo} disabled={!canUndo || pending} style={styles.button} title="Annuler (Ctrl+Z)" aria-label="Annuler">
              ↶
            </button>
            <button type="button" onClick={onRedo} disabled={!canRedo || pending} style={styles.button} title="Rétablir (Ctrl+Y)" aria-label="Rétablir">
              ↷
            </button>
            <button
              type="button"
              onClick={onDeleteSelected}
              disabled={!hasSelection || pending}
              style={styles.button}
              title="Supprimer le point sélectionné (Suppr)"
              aria-label="Supprimer le point sélectionné"
            >
              🗑
            </button>
            <button type="button" onClick={onReset} disabled={!canReset || pending} style={styles.button} title="Revenir au tracé généré">
              ⟲ Origine
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
    flexWrap: "nowrap",
    justifyContent: "center",
    gap: 4,
    padding: 4,
    border: "1px solid var(--border)",
    borderRadius: 18,
    background: "var(--overlay-strong)",
    boxShadow: "var(--shadow-soft)",
    backdropFilter: "blur(16px)",
  },

  button: {
    border: "1px solid var(--border)",
    borderRadius: 12,
    background: "var(--card)",
    color: "var(--text)",
    padding: "7px 10px",
    fontSize: 13,
    fontWeight: 700,
    whiteSpace: "nowrap",
  },

  buttonActive: {
    background: "var(--accent-strong)",
    color: "#fff",
    borderColor: "var(--accent-strong)",
  },

  hint: {
    padding: "6px 12px",
    borderRadius: 12,
    background: "var(--overlay-strong)",
    border: "1px solid var(--border)",
    color: "var(--text-soft)",
    fontSize: 12,
    textAlign: "center",
    backdropFilter: "blur(16px)",
  },
};
