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
    background: "linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg-elevated) 78%, transparent 100%)",
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

  heroCard: {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 28,
    padding: 18,
    boxShadow: "var(--shadow-soft)",
    backdropFilter: "blur(18px)",
  },

  heroEyebrow: {
    color: "var(--text-soft)",
    fontSize: 12,
    fontWeight: 700,
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },

  heroTitle: {
    margin: 0,
    fontSize: 27,
    lineHeight: 1.05,
    letterSpacing: -0.7,
  },

  heroText: {
    margin: "12px 0 0",
    color: "var(--text-soft)",
    fontSize: 14,
    lineHeight: 1.58,
  },

  card: {
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 28,
    padding: 18,
    boxShadow: "var(--shadow-soft)",
    backdropFilter: "blur(18px)",
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
    color: "var(--accent-strong)",
    whiteSpace: "nowrap",
    textAlign: "right",
  },

  locationButton: {
    width: "100%",
    border: "none",
    background: "var(--button-green)",
    color: "white",
    borderRadius: 20,
    padding: "15px 18px",
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: "0 12px 24px rgba(52,199,89,0.26)",
  },

  input: {
    width: "100%",
    borderRadius: 18,
    border: "1px solid var(--input-border)",
    background: "var(--input)",
    padding: "14px 16px",
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
    borderRadius: 18,
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
    borderRadius: 18,
    border: "1px dashed var(--accent-strong)",
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
    background: "var(--accent-strong)",
  },

  suggestItemActive: {
    borderColor: "var(--accent-strong)",
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
    color: "var(--accent-strong)",
    fontWeight: 800,
    padding: "10px 12px",
  },

  stepperRow: {
    display: "grid",
    gridTemplateColumns: "56px 1fr 56px",
    gap: 10,
    alignItems: "center",
  },

  stepperButton: {
    height: 52,
    borderRadius: 18,
    border: "1px solid var(--border)",
    background: "var(--overlay)",
    color: "var(--text)",
    fontSize: 28,
    cursor: "pointer",
  },

  inputCenter: {
    height: 52,
    textAlign: "center",
    borderRadius: 18,
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
    borderRadius: 18,
    background: "var(--chip)",
    color: "var(--text)",
    fontSize: 13,
  },

  infoPillSoft: {
    padding: "12px 14px",
    borderRadius: 18,
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
    borderRadius: 18,
    padding: "12px 14px",
    fontWeight: 800,
    cursor: "pointer",
  },

  modeTabActive: {
    border: "1px solid transparent",
    background: "var(--button-blue)",
    color: "white",
    borderRadius: 18,
    padding: "12px 14px",
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: "0 12px 24px rgba(0,122,255,0.22)",
  },

  shapeGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
  },

  shapeButton: {
    border: "1px solid var(--border)",
    background: "var(--overlay)",
    color: "var(--text)",
    borderRadius: 20,
    padding: "14px 12px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
  },

  shapeButtonActive: {
    border: "1px solid transparent",
    background: "linear-gradient(135deg, var(--accent-strong), #6fb8ff)",
    color: "white",
    borderRadius: 20,
    padding: "14px 12px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
    boxShadow: "0 12px 24px rgba(0,122,255,0.22)",
  },

  shapeEmoji: {
    fontSize: 22,
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
    border: "none",
    background: "var(--button-blue)",
    color: "white",
    borderRadius: 20,
    padding: "15px 18px",
    fontWeight: 800,
    boxShadow: "0 12px 24px rgba(0,122,255,0.22)",
  },









};
