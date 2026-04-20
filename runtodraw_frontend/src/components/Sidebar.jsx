import { useEffect, useMemo, useRef, useState } from "react";
import logoRunToDrawDay from "../assets/logo_runtodraw_day.png";
import logoRunToDrawNight from "../assets/logo_runtodraw_night.png";
import RouteResultsPanel from "./RouteResultsPanel";

/*
============================================================
EN:
This list defines the available predefined shapes shown
in the interface.

Each shape has:
- an internal id used in the code
- a readable label for the user
- an emoji to make the UI more visual

FR:
Cette liste définit les formes prédéfinies disponibles
dans l’interface.

Chaque forme possède :
- un identifiant interne utilisé dans le code
- un label lisible pour l’utilisateur
- un emoji pour rendre l’interface plus visuelle
============================================================
*/
const SHAPES = [
  { id: "square", label: "Carré", emoji: "⬜" },
  { id: "circle", label: "Rond", emoji: "⚪" },
  { id: "heart", label: "Cœur", emoji: "💙" },
  { id: "star", label: "Étoile", emoji: "⭐" },
  { id: "infinity", label: "Infini", emoji: "♾️" },
];

/*
============================================================
EN:
ToggleRow is a reusable small setting block with:
- a label
- an optional description
- an optional info tooltip
- a switch button

It is used here for options such as showing or hiding the graph.

FR:
ToggleRow est un petit bloc réutilisable avec :
- un label
- une description optionnelle
- une info complémentaire optionnelle
- un bouton type interrupteur

Il est utilisé ici pour des options comme l’affichage ou non du graphe.
============================================================
*/
function ToggleRow({ label, description, checked, onChange, infoText, disabled = false }) {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <div style={{ ...styles.toggleBlock, opacity: disabled ? 0.56 : 1 }}>
      <div style={styles.toggleTextWrap}>
        <div style={styles.toggleLabelRow}>
          <span style={styles.toggleLabel}>{label}</span>

          {infoText ? (
            <button
              type="button"
              onClick={() => setShowInfo((current) => !current)}
              style={styles.infoButton}
              aria-label={`Informations sur ${label}`}
              title="Informations"
            >
              i
            </button>
          ) : null}
        </div>

        {description ? <div style={styles.toggleDescription}>{description}</div> : null}
        {showInfo && infoText ? <div style={styles.infoTooltip}>{infoText}</div> : null}
      </div>

      <button
        type="button"
        onClick={disabled ? undefined : onChange}
        disabled={disabled}
        style={{
          ...styles.switchButton,
          justifyContent: checked ? "flex-end" : "flex-start",
          background: checked ? "var(--accent-strong)" : "var(--switch-off)",
          cursor: disabled ? "not-allowed" : "pointer",
        }}
        aria-pressed={checked}
        aria-label={label}
        title={checked ? "Activé" : "Désactivé"}
      >
        <span style={styles.switchThumb} />
      </button>
    </div>
  );
}

/*
============================================================
EN:
These two helpers format geocoding results coming from
different services.

The goal is simply to generate a readable label for the user.

FR:
Ces deux fonctions servent à formater les résultats de géocodage
venant de services différents.

L’objectif est simplement de produire un libellé lisible
pour l’utilisateur.
============================================================
*/
function formatPhotonLabel(properties) {
  const firstLine = [properties.name, properties.street, properties.housenumber].filter(Boolean).join(" ");
  const secondLine = [properties.postcode, properties.city, properties.state].filter(Boolean).join(" · ");
  const full = [firstLine, secondLine, properties.country].filter(Boolean).join(", ");
  return full || properties.name || properties.city || properties.country || "Adresse trouvée";
}

function formatNominatimLabel(item) {
  const address = item.address || {};
  const firstLine = [
    address.road || address.pedestrian || address.path || address.cycleway || item.name,
    address.house_number,
  ]
    .filter(Boolean)
    .join(" ");
  const secondLine = [address.postcode, address.city || address.town || address.village || address.municipality]
    .filter(Boolean)
    .join(" · ");
  const full = [firstLine, secondLine, address.country].filter(Boolean).join(", ");
  return full || item.display_name || "Adresse trouvée";
}

/*
============================================================
EN:
Sidebar is the main control panel of the application.

It guides the full user flow:
1) choose a starting location
2) choose a running distance
3) choose a shape or a text
4) generate the routes
5) review the route results
6) export a selected route

This component is mostly responsible for interface logic,
form state, and address search.

FR:
Sidebar est le panneau principal de contrôle de l’application.

Il guide tout le parcours utilisateur :
1) choisir un point de départ
2) choisir une distance
3) choisir une forme ou un texte
4) générer les itinéraires
5) consulter les résultats
6) exporter un itinéraire sélectionné

Ce composant gère surtout la logique d’interface,
l’état du formulaire et la recherche d’adresse.
============================================================
*/
export default function Sidebar({
  theme,
  center,
  showFullGraph,
  onToggleShowFullGraph,
  canToggleGraph,
  distanceKm,
  setDistanceKm,
  drawing,
  setDrawing,
  onUseMyLocation,
  onPickSuggestion,
  onGenerateRoutes,
  canGenerate,
  routePlan,
  selectedRouteId,
  onSelectRoute,
  onExportRoute,
}) {
  const [address, setAddress] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [searchStatus, setSearchStatus] = useState("");

  /*
  EN:
  These refs are used to control address search behavior:
  - debounceRef delays requests while the user is typing
  - abortRef cancels the previous request if a new one starts

  FR:
  Ces refs servent à contrôler le comportement de la recherche d’adresse :
  - debounceRef retarde les requêtes pendant la saisie
  - abortRef annule la requête précédente si une nouvelle démarre
  */
  const debounceRef = useRef(null);
  const abortRef = useRef(null);

  const radiusKm = distanceKm / 2;
  const currentLogo = theme === "dark" ? logoRunToDrawNight : logoRunToDrawDay;

  /*
  EN:
  This helper text explains whether the typed word length is reasonable.
  We keep it dynamic so the user gets feedback while typing.

  FR:
  Ce texte d’aide explique si la longueur du mot saisi est raisonnable.
  On le garde dynamique pour que l’utilisateur ait un retour pendant la saisie.
  */
  const textHelper = useMemo(() => {
    const clean = (drawing.text || "").trim();
    const letterCount = clean.replace(/\s+/g, "").length;

    if (!clean) return "Mieux vaut viser un mot très court, idéalement 3 lettres maximum.";
    if (letterCount <= 3) return `${letterCount} lettre${letterCount > 1 ? "s" : ""} · bon compromis pour le calcul.`;
    return `${letterCount} lettres · au-delà de 3, le temps peut devenir très long et le résultat moins bon.`;
  }, [drawing.text]);

  /*
  ============================================================
  EN:
  Address search effect.

  We:
  - wait a little before sending requests
  - query Photon first
  - use Nominatim as a fallback if needed
  - remove duplicates
  - update the suggestions list and the status text

  This keeps the experience smoother and avoids too many requests.

  FR:
  Effet de recherche d’adresse.

  On :
  - attend un petit délai avant d’envoyer une requête
  - interroge Photon en premier
  - utilise Nominatim en secours si besoin
  - supprime les doublons
  - met à jour la liste des suggestions et le statut

  Cela rend l’expérience plus fluide et évite trop de requêtes.
  ============================================================
  */
  useEffect(() => {
    const query = address
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");

    if (query.length < 3) {
      setSuggestions([]);
      setSearchStatus(query.length === 0 ? "" : "Tape au moins 3 caractères");
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setLoadingSuggest(true);
      setSearchStatus("Recherche d’adresses…");

      try {
        if (abortRef.current) abortRef.current.abort();
        abortRef.current = new AbortController();

        const [latBias, lonBias] = center ?? [44.8378, -0.5792];
        const photonUrl =
          `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}` +
          `&limit=7&lang=fr&lat=${latBias}&lon=${lonBias}`;

        const photonResponse = await fetch(photonUrl, {
          signal: abortRef.current.signal,
          headers: { Accept: "application/json" },
        });
        const photonData = await photonResponse.json();

        let nextSuggestions = (photonData.features ?? []).map((feature) => {
          const [lonValue, latValue] = feature.geometry.coordinates;
          return {
            id: `photon-${feature.properties.osm_id ?? `${latValue}-${lonValue}`}`,
            display: formatPhotonLabel(feature.properties),
            lat: latValue,
            lon: lonValue,
            source: "Photon",
          };
        });

        /*
        EN:
        If Photon does not return enough results,
        we ask Nominatim to complete the suggestions.

        FR:
        Si Photon ne renvoie pas assez de résultats,
        on interroge aussi Nominatim pour compléter les suggestions.
        */
        if (nextSuggestions.length < 4) {
          const nominatimUrl =
            `https://nominatim.openstreetmap.org/search?format=jsonv2&accept-language=fr&limit=5&q=${encodeURIComponent(query)}`;

          const nominatimResponse = await fetch(nominatimUrl, {
            signal: abortRef.current.signal,
            headers: { Accept: "application/json" },
          });
          const nominatimData = await nominatimResponse.json();

          const fallback = (nominatimData ?? []).map((item) => ({
            id: `nominatim-${item.place_id}`,
            display: formatNominatimLabel(item),
            lat: Number(item.lat),
            lon: Number(item.lon),
            source: "OSM",
          }));

          nextSuggestions = [...nextSuggestions, ...fallback];
        }

        /*
        EN:
        Deduplicate suggestions to avoid showing the same place twice.

        FR:
        Déduplication des suggestions pour éviter d’afficher deux fois
        le même lieu.
        */
        const unique = [];
        const seen = new Set();

        for (const suggestion of nextSuggestions) {
          const key = `${suggestion.display}|${suggestion.lat.toFixed(5)}|${suggestion.lon.toFixed(5)}`;
          if (seen.has(key)) continue;
          seen.add(key);
          unique.push(suggestion);
        }

        setSuggestions(unique.slice(0, 7));
        setSearchStatus(
          unique.length > 0
            ? `${unique.length} résultat${unique.length > 1 ? "s" : ""}`
            : "Aucun résultat"
        );
      } catch (error) {
        if (error.name !== "AbortError") {
          console.log(error);
          setSuggestions([]);
          setSearchStatus("Recherche indisponible");
        }
      } finally {
        setLoadingSuggest(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [address, center]);

  return (
    <div style={styles.sidebar}>
      {/* 
      EN:
      Sticky logo area so the project branding stays visible
      even when the sidebar is scrolled.

      FR:
      Zone de logo sticky pour que l’identité visuelle du projet
      reste visible même quand la sidebar défile.
      */}
      <div style={styles.logoStickyWrap}>
        <div style={styles.logoZone}>
          <img src={currentLogo} alt="RunToDraw" style={styles.logoImage} />
        </div>
      </div>

      {/* 
      EN:
      Intro card explaining the overall feature flow.

      FR:
      Carte d’introduction expliquant le fonctionnement global.
      */}
      <section style={styles.heroCard}>
        <div style={styles.heroEyebrow}>Run planner</div>
        <h1 style={styles.heroTitle}>Prépare ton dessin de course</h1>
        <p style={styles.heroText}>
          Choisis une zone, une distance, puis une forme ou un texte. L’application extrait le
          graphe, l’envoie au moteur Python et te propose ensuite les meilleurs itinéraires à
          exporter.
        </p>
      </section>

      {/* ============================================================
          EN: Step 1 — starting point
          FR: Étape 1 — point de départ
          ============================================================ */}
      <section style={styles.card}>
        <div style={styles.cardHeader}>
          <div>
            <div style={styles.cardLabel}>Étape 1</div>
            <div style={styles.cardTitle}>Point de départ</div>
          </div>
        </div>

        <button style={styles.locationButton} onClick={onUseMyLocation}>
          Utiliser ma position actuelle
        </button>

        <div style={styles.inputHeaderRow}>
          <span style={styles.inputLabel}>Adresse ou lieu</span>
          <span style={styles.inlineStatus}>
            {loadingSuggest ? "Recherche d’adresses…" : searchStatus}
          </span>
        </div>

        <div style={{ position: "relative" }}>
          <input
            style={styles.input}
            placeholder="Entrer une adresse ou un lieu"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
          />

          {suggestions.length > 0 ? (
            <div style={styles.suggestBox}>
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion.id}
                  style={styles.suggestItem}
                  onClick={() => {
                    /*
                    EN:
                    When a suggestion is selected:
                    - we notify the parent component
                    - we fill the input with the chosen label
                    - we close the suggestion list

                    FR:
                    Quand une suggestion est choisie :
                    - on informe le composant parent
                    - on remplit l’input avec le texte choisi
                    - on ferme la liste des suggestions
                    */
                    onPickSuggestion([suggestion.lat, suggestion.lon], suggestion.display);
                    setAddress(suggestion.display);
                    setSuggestions([]);
                    setSearchStatus("Adresse sélectionnée");
                  }}
                  title={suggestion.display}
                >
                  <span style={styles.suggestMain}>{suggestion.display}</span>
                  <span style={styles.suggestMeta}>{suggestion.source} · Choisir ce point</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      {/* ============================================================
          EN: Step 2 — running distance
          FR: Étape 2 — distance à parcourir
          ============================================================ */}
      <section style={styles.card}>
        <div style={styles.cardHeader}>
          <div>
            <div style={styles.cardLabel}>Étape 2</div>
            <div style={styles.cardTitle}>Distance à parcourir</div>
          </div>
          <div style={styles.distanceBadge}>{distanceKm} km</div>
        </div>

        <div style={styles.stepperRow}>
          <button style={styles.stepperButton} onClick={() => setDistanceKm(Math.max(1, distanceKm - 1))}>
            −
          </button>

          <input
            style={styles.inputCenter}
            type="number"
            min={1}
            step={1}
            value={distanceKm}
            onChange={(event) => setDistanceKm(Number(event.target.value || 1))}
          />

          <button style={styles.stepperButton} onClick={() => setDistanceKm(distanceKm + 1)}>
            +
          </button>
        </div>

        <div style={styles.infoPill}>
          Rayon d’extraction estimé : <strong>{radiusKm.toFixed(1)} km</strong>
        </div>
      </section>

      {/* ============================================================
          EN: Step 3 — shape or text choice
          FR: Étape 3 — choix de la forme ou du texte
          ============================================================ */}
      <section style={styles.card}>
        <div style={styles.cardHeaderSimple}>
          <div style={styles.cardLabel}>Étape 3</div>
          <div style={styles.cardTitle}>Forme ou texte</div>
        </div>

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
                  onClick={() =>
                    setDrawing((current) => ({
                      ...current,
                      mode: "shape",
                      shape: shape.id,
                    }))
                  }
                >
                  <span style={styles.shapeEmoji}>{shape.emoji}</span>
                  <span style={styles.shapeLabel}>{shape.label}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <div style={styles.textBlock}>
            <input
              style={styles.input}
              value={drawing.text}
              maxLength={10}
              onChange={(event) =>
                setDrawing((current) => ({
                  ...current,
                  mode: "text",
                  text: event.target.value.toUpperCase(),
                }))
              }
              placeholder="Ex : P2I"
            />

            <div style={styles.textHintStrong}>
              Conseil : privilégie des mots de 3 lettres maximum.
            </div>

            <div style={styles.textHint}>{textHelper}</div>
          </div>
        )}
      </section>

      {/* ============================================================
          EN: Step 4 — generation actions
          FR: Étape 4 — actions de génération
          ============================================================ */}
      <section style={styles.card}>
        <div style={styles.cardLabel}>Étape 4</div>

        <div style={styles.actionsColumn}>
          <button
            style={{
              ...styles.primaryButton,
              opacity: canGenerate ? 1 : 0.5,
              cursor: canGenerate ? "pointer" : "not-allowed",
            }}
            disabled={!canGenerate}
            onClick={onGenerateRoutes}
          >
            Générer les propositions d’itinéraires
          </button>

          <div style={styles.infoPillSoft}>
            Le graphe est extrait automatiquement puis envoyé au moteur Python. Si le calcul
            détaillé ne peut pas être remonté en temps réel, prévois un ordre de grandeur pouvant
            aller jusqu’à environ 15 minutes sur les cas lourds.
          </div>

          <ToggleRow
            label="Afficher le graphe complet"
            description={
              canToggleGraph
                ? showFullGraph
                  ? "Le graphe extrait est actuellement affiché sur la carte."
                  : "Le graphe a déjà été calculé, mais reste masqué pour garder une carte plus légère et plus fluide."
                : "Lance d’abord une génération pour calculer le graphe, puis active cet affichage si besoin."
            }
            checked={showFullGraph}
            onChange={onToggleShowFullGraph}
            disabled={!canToggleGraph}
            infoText="L’affichage du graphe complet peut alourdir le rendu. Il reste facultatif : le choix d’itinéraire fonctionne aussi sans l’afficher."
          />
        </div>
      </section>

      {/* 
      EN:
      Final result and export block.

      FR:
      Bloc final des résultats et des exports.
      */}
      <RouteResultsPanel
        routePlan={routePlan}
        selectedRouteId={selectedRouteId}
        onSelectRoute={onSelectRoute}
        onExportRoute={onExportRoute}
      />
    </div>
  );
}

/*
============================================================
EN:
These styles define the full visual structure of the sidebar:
- cards
- buttons
- tabs
- suggestion list
- text hints
- toggles

The goal is to keep the flow very guided and easy to follow.

FR:
Ces styles définissent toute la structure visuelle de la sidebar :
- cartes
- boutons
- onglets
- liste de suggestions
- aides textuelles
- interrupteurs

L’objectif est de garder un parcours très guidé et simple à suivre.
============================================================
*/
const styles = {
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

  suggestMain: {
    fontWeight: 700,
    lineHeight: 1.35,
  },

  suggestMeta: {
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

  toggleBlock: {
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: 12,
    alignItems: "flex-start",
    background: "var(--overlay)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 22,
    padding: 14,
  },

  toggleTextWrap: {
    minWidth: 0,
  },

  toggleLabelRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },

  toggleLabel: {
    fontWeight: 800,
  },

  toggleDescription: {
    marginTop: 5,
    fontSize: 13,
    lineHeight: 1.5,
    color: "var(--text-soft)",
  },

  infoButton: {
    width: 22,
    height: 22,
    borderRadius: 999,
    border: "1px solid var(--border)",
    background: "transparent",
    color: "var(--text-soft)",
    cursor: "pointer",
    fontWeight: 800,
  },

  infoTooltip: {
    marginTop: 9,
    fontSize: 12.5,
    color: "var(--text-soft)",
    lineHeight: 1.5,
  },

  switchButton: {
    width: 52,
    minWidth: 52,
    height: 30,
    borderRadius: 999,
    border: "none",
    display: "flex",
    alignItems: "center",
    padding: 3,
  },

  switchThumb: {
    width: 24,
    height: 24,
    borderRadius: 999,
    background: "white",
  },
};