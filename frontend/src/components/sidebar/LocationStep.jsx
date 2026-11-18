import { useAddressSearch } from "../../hooks/useAddressSearch";
import CountryFlag from "./CountryFlag";
import StepHeader from "./StepHeader";
import { styles } from "./styles";

// Étape 1 : point de départ (position actuelle ou recherche d'adresse avec suggestions).
export default function LocationStep({ center, onUseMyLocation, onPickSuggestion }) {
  const search = useAddressSearch({ center, onPick: onPickSuggestion });

  return (
    <section style={styles.card}>
      <StepHeader step={1} title="Point de départ" />

      <button style={styles.locationButton} onClick={onUseMyLocation}>
        Utiliser ma position actuelle
      </button>

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
    </section>
  );
}
