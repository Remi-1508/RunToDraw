// Styles partagés par les composants de la barre latérale.
// Ces styles définissent toute la structure visuelle de la sidebar :
// - cartes
// - boutons
// - onglets
// - liste de suggestions
// - aides textuelles
// - interrupteurs
//
// L’objectif est de garder un parcours très guidé et simple à suivre.
export const styles = {
  sidebar: {
    minHeight: "100%",
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 14,
    background: "var(--bg-elevated)",
    color: "var(--text)",
  },

  logoStickyWrap: {
    position: "sticky",
    top: 0,
    zIndex: 20,
    paddingTop: 2,
    background: "var(--bg-elevated)",
  },

  logoZone: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: "2px 0 8px",
  },

  logoImage: {
    width: "100%",
    maxWidth: 255,
    height: "auto",
    display: "block",
    objectFit: "contain",
  },

  card: {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: 18,
    boxShadow: "var(--shadow-soft)",
  },

  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 16,
    marginBottom: 14,
  },

  cardHeaderSimple: {
    marginBottom: 14,
  },

  // En-tête d'une étape : pastille numérotée (c'est une vraie séquence) + titre.
  stepHeader: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },

  stepBadge: {
    flexShrink: 0,
    width: 26,
    height: 26,
    borderRadius: "50%",
    background: "var(--text)",
    color: "var(--bg-elevated)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 800,
  },

  cardTitle: {
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontStretch: "112%",
    fontSize: 19,
    fontWeight: 800,
  },

  inputHeaderRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 8,
    marginTop: 14,
  },

  inputLabel: {
    fontSize: 13,
    fontWeight: 700,
    color: "var(--text-soft)",
  },

  inlineStatus: {
    fontSize: 12,
    color: "var(--accent-text)",
    whiteSpace: "nowrap",
    textAlign: "right",
  },

  locationButton: {
    width: "100%",
    border: "2px solid var(--text)",
    background: "transparent",
    color: "var(--text)",
    borderRadius: "var(--radius)",
    padding: "12px 18px",
    fontWeight: 800,
    cursor: "pointer",
  },

  input: {
    width: "100%",
    borderRadius: "var(--radius-sm)",
    border: "2px solid var(--input-border)",
    background: "var(--input)",
    padding: "12px 14px",
    color: "var(--text)",
    outline: "none",
  },

  suggestBox: {
    marginTop: 10,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },

  suggestItem: {
    width: "100%",
    textAlign: "left",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-subtle)",
    background: "var(--overlay)",
    color: "var(--text)",
    padding: "12px 14px",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },

  worldPending: {
    marginTop: 10,
    borderRadius: "var(--radius-sm)",
    border: "1px dashed var(--accent)",
    background: "var(--accent-soft)",
    padding: "12px 14px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },

  worldPendingRow: {
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: 10,
  },

  worldPendingTitle: {
    fontWeight: 700,
    color: "var(--text)",
  },

  worldPendingTime: {
    fontVariantNumeric: "tabular-nums",
    fontSize: 13,
    color: "var(--text-soft)",
  },

  worldPendingText: {
    fontSize: 13,
    lineHeight: 1.45,
    color: "var(--text-soft)",
  },

  worldPendingTrack: {
    position: "relative",
    height: 4,
    borderRadius: 999,
    overflow: "hidden",
    background: "var(--border)",
  },

  worldPendingBar: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "30%",
    height: "100%",
    borderRadius: 999,
    background: "var(--accent)",
  },

  suggestItemActive: {
    borderColor: "var(--accent)",
    background: "var(--accent-soft)",
  },

  suggestRow: {
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: 10,
  },

  suggestMain: {
    fontWeight: 700,
    lineHeight: 1.35,
  },

  suggestPlace: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 12,
    color: "var(--text-soft)",
  },

  flag: {
    flexShrink: 0,
    width: 20,
    height: 15,
    borderRadius: 3,
    objectFit: "cover",
    boxShadow: "0 0 0 1px var(--border-strong)",
  },

  flagFallback: {
    flexShrink: 0,
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 0.4,
    padding: "1px 4px",
    borderRadius: 3,
    color: "var(--text-soft)",
    boxShadow: "0 0 0 1px var(--border-strong)",
  },

  suggestKind: {
    flexShrink: 0,
    fontSize: 12,
    color: "var(--text-soft)",
  },


  distanceBadge: {
    minWidth: 68,
    textAlign: "center",
    borderRadius: 999,
    background: "var(--chip)",
    color: "var(--accent-text)",
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontStretch: "112%",
    fontWeight: 900,
    fontSize: 18,
    padding: "8px 14px",
  },

  stepperRow: {
    display: "grid",
    gridTemplateColumns: "56px 1fr 56px",
    gap: 10,
    alignItems: "center",
  },

  stepperButton: {
    height: 52,
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
    background: "var(--overlay)",
    color: "var(--text)",
    fontSize: 28,
    cursor: "pointer",
  },

  inputCenter: {
    height: 52,
    textAlign: "center",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--input-border)",
    background: "var(--input)",
    color: "var(--text)",
    fontWeight: 800,
    fontSize: 18,
    outline: "none",
  },

  infoPill: {
    marginTop: 12,
    padding: "12px 14px",
    borderRadius: "var(--radius-sm)",
    background: "var(--chip)",
    color: "var(--text)",
    fontSize: 13,
  },

  infoPillSoft: {
    padding: "12px 14px",
    borderRadius: "var(--radius-sm)",
    background: "var(--overlay)",
    color: "var(--text-soft)",
    fontSize: 13,
    lineHeight: 1.5,
    border: "1px solid var(--border-subtle)",
  },

  modeTabs: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
    marginBottom: 12,
  },

  modeTab: {
    border: "1px solid var(--border)",
    background: "var(--overlay)",
    color: "var(--text)",
    borderRadius: "var(--radius-sm)",
    padding: "12px 14px",
    fontWeight: 800,
    cursor: "pointer",
  },

  modeTabActive: {
    border: "1px solid transparent",
    background: "var(--accent)",
    color: "var(--on-accent)",
    borderRadius: "var(--radius-sm)",
    padding: "12px 14px",
    fontWeight: 800,
    cursor: "pointer",
  },

  shapeGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(78px, 1fr))",
    gap: 8,
  },

  shapeButton: {
    border: "1px solid var(--border)",
    background: "var(--overlay)",
    color: "var(--text)",
    borderRadius: "var(--radius)",
    padding: "12px 6px 10px",
    minHeight: 44,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    cursor: "pointer",
  },

  shapeButtonActive: {
    border: "2px solid var(--accent)",
    background: "var(--accent)",
    color: "var(--on-accent)",
    borderRadius: "var(--radius)",
    padding: "12px 6px 10px",
    minHeight: 44,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    cursor: "pointer",
  },

  shapeIcon: {
    display: "flex",
  },

  shapeLabel: {
    fontWeight: 800,
  },

  textBlock: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },

  textHintStrong: {
    fontWeight: 800,
    fontSize: 13,
    color: "var(--text)",
  },

  textHint: {
    fontSize: 12.5,
    color: "var(--text-soft)",
    lineHeight: 1.45,
  },

  actionsColumn: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    marginTop: 10,
  },

  primaryButton: {
    width: "100%",
    height: 56,
    border: "none",
    background: "var(--accent)",
    color: "var(--on-accent)",
    borderRadius: "var(--radius)",
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontStretch: "112%",
    fontSize: 19,
    fontWeight: 900,
  },
};
