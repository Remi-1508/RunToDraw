import { useEffect, useRef, useState } from "react";

export default function Sidebar({
  distanceKm,
  setDistanceKm,
  onUseMyLocation,
  onPickSuggestion,
  onValidateZone,
  canValidate,
  onExportFullGraph,
  canExport,
}) {

  const [address, setAddress] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggest, setLoadingSuggest] = useState(false);

  const debounceRef = useRef(null);
  const abortRef = useRef(null);

  const radiusKm = distanceKm / 2;

  useEffect(() => {

    const q = address
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");

    if (q.length < 3) {
      setSuggestions([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {

      try {

        setLoadingSuggest(true);

        if (abortRef.current) abortRef.current.abort();
        abortRef.current = new AbortController();

        // centre France pour prioriser les résultats FR
        const lat = 46.6;
        const lon = 2.4;

        const url =
          `https://photon.komoot.io/api/?` +
          `q=${encodeURIComponent(q)}` +
          `&limit=6` +
          `&lang=fr` +
          `&lat=${lat}` +
          `&lon=${lon}`;

        const res = await fetch(url, {
          signal: abortRef.current.signal,
        });

        const data = await res.json();

        const list = (data.features ?? []).map((f) => {

          const lon = f.geometry.coordinates[0];
          const lat = f.geometry.coordinates[1];

          const p = f.properties;

          const label = [
            p.name,
            p.street,
            p.housenumber,
            p.city,
            p.country
          ]
            .filter(Boolean)
            .join(", ");

          return {
            display: label,
            lat,
            lon
          };

        });

        setSuggestions(list);

      } catch (e) {

        if (e.name !== "AbortError") {
          console.log(e);
        }

      } finally {

        setLoadingSuggest(false);

      }

    }, 220); // debounce rapide

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };

  }, [address]);

  return (
    <div style={styles.sidebar}>

      <div style={styles.logoBox}>RunToDraw</div>

      <h3 style={styles.sectionTitle}>Position</h3>

      <button style={styles.greenButton} onClick={onUseMyLocation}>
        Utiliser ma position actuelle
      </button>

      <div style={{ height: 10 }} />

      <input
        style={styles.input}
        placeholder="Entrer une position de départ (adresse)"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />

      {loadingSuggest && (
        <div style={styles.suggestHint}>
          Recherche...
        </div>
      )}

      {suggestions.length > 0 && (

        <div style={styles.suggestBox}>

          {suggestions.map((s, i) => (

            <button
              key={i}
              style={styles.suggestItem}
              onClick={() => {
                onPickSuggestion([s.lat, s.lon], s.display);
                setAddress(s.display);
                setSuggestions([]);
              }}
              title={s.display}
            >
              {s.display}
            </button>

          ))}

        </div>

      )}

      <h3 style={styles.sectionTitle}>Distance (km)</h3>

      <div style={styles.row}>

        <button
          style={styles.smallButton}
          onClick={() =>
            setDistanceKm(Math.max(1, distanceKm - 1))
          }
        >
          −
        </button>

        <input
          style={styles.inputCenter}
          type="number"
          min={1}
          step={1}
          value={distanceKm}
          onChange={(e) =>
            setDistanceKm(Number(e.target.value || 1))
          }
        />

        <button
          style={styles.smallButton}
          onClick={() => setDistanceKm(distanceKm + 1)}
        >
          +
        </button>

      </div>

      <p style={styles.hint}>
        Rayon d’extraction du graphe ≈ {radiusKm.toFixed(1)} km (distance / 2)
        <br />
        {distanceKm < 10
          ? "Conseil : vise plutôt ≥ 10 km pour dessiner confortablement."
          : null}
      </p>

      <button
        style={{
          ...styles.actionButton,
          opacity: canValidate ? 1 : 0.55,
          cursor: canValidate ? "pointer" : "not-allowed",
        }}
        disabled={!canValidate}
        onClick={onValidateZone}
      >
        ✅ Valider la zone (obtenir le graphe)
      </button>

      <button
        style={{
          ...styles.actionButton,
          opacity: canExport ? 1 : 0.55,
          cursor: canExport ? "pointer" : "not-allowed",
        }}
        disabled={!canExport}
        onClick={onExportFullGraph}
      >
        ⬇️ Exporter graphe complet
      </button>

      <hr style={styles.hr} />

      <h3 style={styles.sectionTitle}>Image à dessiner (plus tard)</h3>

      <input
        style={styles.input}
        placeholder="Ex: LOVE"
      />

      <button style={styles.disabledButton} disabled>
        Choisir le symbole
      </button>

    </div>
  );
}

const styles = {
  sidebar: {
    padding: 16,
    borderRight: "1px solid var(--border)",
    height: "100%",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    background: "var(--panel)",
    color: "var(--text)",
  },
  logoBox: {
    background: "linear-gradient(135deg,#ffb7b7,#f6c7c7)",
    color: "#171a21",
    borderRadius: 12,
    padding: 12,
    fontWeight: 900,
    textAlign: "center",
  },
  sectionTitle: { margin: "10px 0 0 0" },
  row: { display: "flex", gap: 8, alignItems: "center" },
  input: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid var(--border)",
    background: "var(--panel2)",
    color: "var(--text)",
  },
  inputCenter: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid var(--border)",
    background: "var(--panel2)",
    textAlign: "center",
    color: "var(--text)",
  },
  smallButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    border: "1px solid var(--border)",
    background: "var(--panel2)",
    cursor: "pointer",
  },
  greenButton: {
    padding: "10px 12px",
    borderRadius: 12,
    border: "1px solid rgba(98,209,143,.35)",
    background: "rgba(98,209,143,.18)",
    cursor: "pointer",
  },
  actionButton: {
    padding: "11px 12px",
    borderRadius: 12,
    border: "1px solid rgba(122,162,255,.55)",
    background: "rgba(122,162,255,.16)",
    fontWeight: 800,
  },
  disabledButton: {
    padding: "10px 12px",
    borderRadius: 12,
    border: "1px solid rgba(122,162,255,.35)",
    background: "rgba(122,162,255,.12)",
    cursor: "not-allowed",
  },
  hint: { fontSize: 12 },
  hr: { margin: "12px 0" },
  suggestHint: { fontSize: 12 },
  suggestBox: {
    border: "1px solid var(--border)",
    borderRadius: 12,
    overflow: "hidden",
    background: "var(--panel2)",
  },
  suggestItem: {
    textAlign: "left",
    width: "100%",
    border: "none",
    padding: "10px 12px",
    background: "transparent",
    cursor: "pointer",
    fontSize: 12,
  },
};