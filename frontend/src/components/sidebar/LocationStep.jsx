import { useState } from "react";
import { useAddressSearch } from "../../hooks/useAddressSearch";
import CountryFlag from "./CountryFlag";
import StepHeader from "./StepHeader";
import { styles } from "./styles";

// Étape 1 : point de départ (position actuelle, recherche d'adresse avec suggestions, ou clic sur la carte).
export default function LocationStep({
  center,
  startLabel,
  onUseMyLocation,
  onPickSuggestion,
  pickingOnMap,
  onTogglePickOnMap,
  onClearStart,
}) {
  const search = useAddressSearch({ center, onPick: onPickSuggestion });
  // Mode de choix mis en avant : un onglet est actif tant qu'on n'en a pas choisi un autre.
  const [method, setMethod] = useState("address");

  // Passer d'un mode à l'autre annule un choix sur la carte en attente.
  function selectMethod(next) {
    if (pickingOnMap && next !== "map") onTogglePickOnMap();
    setMethod(next);
    if (next === "position") onUseMyLocation();
    if (next === "map") onTogglePickOnMap();
  }

  const tab = (id, label) => (
    <button
      type="button"
      style={method === id ? styles.modeTabActive : styles.modeTab}
      onClick={() => selectMethod(id)}
      aria-pressed={method === id}
    >
      {label}
    </button>
  );

  return (
    <section style={styles.card}>
      <StepHeader step={1} title="Point de départ" />

      <div style={styles.modeTabs}>
        {tab("position", "Ma position")}
        {tab("address", "Adresse")}
        {tab("map", "Sur la carte")}
      </div>

      {method === "address" ? (
        <>
        <div style={styles.inputHeaderRow}>
          <span style={styles.inputLabel}>Adresse ou lieu</span>
          <span style={styles.inlineStatus}>
            {search.loading ? "Recherche d’adresses…" : search.status}
          </span>
        </div>

        <div style={{ position: "relative" }}>
          <input
            style={styles.input}
            placeholder="Adresse, rue, ville ou lieu"
            value={search.address}
            onChange={(event) => search.changeAddress(event.target.value)}
            onKeyDown={search.handleKeyDown}
            role="combobox"
            aria-expanded={search.suggestions.length > 0}
            aria-controls="address-suggestions"
            aria-autocomplete="list"
            aria-activedescendant={search.activeIndex >= 0 ? `address-option-${search.activeIndex}` : undefined}
            autoComplete="off"
          />

          {search.worldSearchStart !== null ? (
            <div style={styles.worldPending} role="status" aria-live="polite">
              <div style={styles.worldPendingRow}>
                <span style={styles.worldPendingTitle}>
                  {search.suggestions.length > 0
                    ? "Recherche d’autres résultats à l’étranger…"
                    : "Recherche dans le monde entier…"}
                </span>
                <span style={styles.worldPendingTime}>{search.worldElapsed} s</span>
              </div>
              <div style={styles.worldPendingText}>
                {search.worldElapsed < 5
                  ? "Ta recherche est bien prise en compte."
                  : "Les adresses hors de France prennent plus de temps (jusqu’à 30 s environ). Tu peux patienter, la liste se complètera toute seule."}
              </div>
              <div style={styles.worldPendingTrack} aria-hidden="true">
                <div className="rtd-search-progress" style={styles.worldPendingBar} />
              </div>
            </div>
          ) : null}

          {search.suggestions.length > 0 ? (
            <div style={styles.suggestBox} role="listbox" id="address-suggestions">
              {search.suggestions.map((suggestion, index) => (
                <button
                  key={suggestion.id}
                  id={`address-option-${index}`}
                  type="button"
                  role="option"
                  aria-selected={index === search.activeIndex}
                  style={{
                    ...styles.suggestItem,
                    ...(index === search.activeIndex ? styles.suggestItemActive : null),
                  }}
                  onMouseEnter={() => search.setActiveIndex(index)}
                  onClick={() => search.pickSuggestion(suggestion)}
                  title={[suggestion.title, suggestion.subtitle].filter(Boolean).join(", ")}
                >
                  <span style={styles.suggestRow}>
                    <span style={styles.suggestMain}>{suggestion.title}</span>
                    <span style={styles.suggestKind}>{suggestion.kind}</span>
                  </span>
                  <span style={styles.suggestPlace}>
                    <CountryFlag code={suggestion.countryCode} country={suggestion.country} />
                    <span>{suggestion.subtitle || suggestion.country}</span>
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
        </>
      ) : method === "position" ? (
        <p style={styles.textHint}>Ta position est demandée au navigateur : autorise la localisation si on te le propose.</p>
      ) : (
        <p style={styles.textHint}>
          {pickingOnMap
            ? "Touche la carte à l’endroit où tu veux partir. Touche « Sur la carte » pour annuler."
            : "Touche « Sur la carte » pour choisir un autre point."}
        </p>
      )}

      <div style={center ? styles.startBox : { ...styles.startBox, ...styles.startBoxEmpty }} role="status">
        <div style={styles.startBoxContent}>
          <span style={styles.startBoxLabel}>Adresse de départ</span>
          <span style={styles.startBoxText}>
            {!center ? "Aucun point choisi pour l’instant" : startLabel === null ? "Recherche de l’adresse…" : startLabel}
          </span>
        </div>
        {center ? (
          <button type="button" style={styles.startBoxClear} onClick={onClearStart} aria-label="Supprimer l’adresse de départ" title="Supprimer l’adresse de départ">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        ) : null}
      </div>
    </section>
  );
}
