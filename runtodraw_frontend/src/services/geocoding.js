// Recherche d'adresses pour l'autocomplétion.
//
// Deux sources, interrogées EN PARALLÈLE (pas l'une après l'autre comme
// avant, ce qui doublait la latence quand la première ne suffisait pas) :
// - la Base Adresse Nationale (api-adresse.data.gouv.fr), officielle et
//   pensée pour l'autocomplétion, pour les adresses françaises précises ;
// - Photon (photon.komoot.io), pour les lieux et l'international.
// Nominatim a été retiré : sa politique d'utilisation interdit
// l'autocomplétion (des requêtes à chaque frappe), ce que ce composant fait.
//
// La requête tapée par l'utilisateur est envoyée telle quelle (juste
// nettoyée des espaces en trop) : les deux API gèrent déjà correctement les
// accents et la casse, la mise en minuscules + suppression des accents
// pratiquée avant appauvrissait les résultats sans raison.

function formatBanLabel(properties) {
  return (
    properties.label ||
    [properties.name, properties.city].filter(Boolean).join(", ") ||
    "Adresse trouvée"
  );
}

function formatPhotonLabel(properties) {
  const firstLine = [properties.name, properties.street, properties.housenumber].filter(Boolean).join(" ");
  const secondLine = [properties.postcode, properties.city, properties.state].filter(Boolean).join(" · ");
  const full = [firstLine, secondLine, properties.country].filter(Boolean).join(", ");
  return full || properties.name || properties.city || properties.country || "Adresse trouvée";
}

function withBias(params, lat, lon) {
  if (Number.isFinite(lat) && Number.isFinite(lon)) {
    params.set("lat", String(lat));
    params.set("lon", String(lon));
  }
  return params;
}

async function searchBan(query, { lat, lon, limit = 6, signal }) {
  const params = withBias(new URLSearchParams({ q: query, limit: String(limit), autocomplete: "1" }), lat, lon);
  const res = await fetch(`https://api-adresse.data.gouv.fr/search/?${params}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`BAN HTTP ${res.status}`);
  const data = await res.json();

  return (data.features ?? []).map((feature) => {
    const [lonValue, latValue] = feature.geometry.coordinates;
    return {
      id: `ban-${feature.properties.id ?? `${latValue}-${lonValue}`}`,
      display: formatBanLabel(feature.properties),
      lat: latValue,
      lon: lonValue,
      source: "Adresse (BAN)",
    };
  });
}

async function searchPhoton(query, { lat, lon, limit = 6, signal }) {
  const params = withBias(new URLSearchParams({ q: query, limit: String(limit), lang: "fr" }), lat, lon);
  const res = await fetch(`https://photon.komoot.io/api/?${params}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`Photon HTTP ${res.status}`);
  const data = await res.json();

  return (data.features ?? []).map((feature) => {
    const [lonValue, latValue] = feature.geometry.coordinates;
    return {
      id: `photon-${feature.properties.osm_id ?? `${latValue}-${lonValue}`}`,
      display: formatPhotonLabel(feature.properties),
      lat: latValue,
      lon: lonValue,
      source: "Lieu (Photon)",
    };
  });
}

function dedupe(suggestions) {
  const unique = [];
  const seen = new Set();

  for (const suggestion of suggestions) {
    const key = `${suggestion.display}|${suggestion.lat.toFixed(5)}|${suggestion.lon.toFixed(5)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(suggestion);
  }

  return unique;
}

// lat/lon: point utilisé pour privilégier les résultats proches (biais de
// proximité), typiquement le centre actuellement choisi sur la carte.
export async function searchAddresses(query, { lat, lon, signal } = {}) {
  const [banResult, photonResult] = await Promise.allSettled([
    searchBan(query, { lat, lon, signal }),
    searchPhoton(query, { lat, lon, signal }),
  ]);

  if (banResult.status === "rejected" && photonResult.status === "rejected") {
    throw banResult.reason;
  }
  if (banResult.status === "rejected" && banResult.reason?.name !== "AbortError") {
    console.warn("Recherche BAN indisponible:", banResult.reason);
  }
  if (photonResult.status === "rejected" && photonResult.reason?.name !== "AbortError") {
    console.warn("Recherche Photon indisponible:", photonResult.reason);
  }

  const banSuggestions = banResult.status === "fulfilled" ? banResult.value : [];
  const photonSuggestions = photonResult.status === "fulfilled" ? photonResult.value : [];

  // BAN en premier : pour une adresse française précise, une base officielle
  // est généralement plus fiable que les résultats de Photon.
  return dedupe([...banSuggestions, ...photonSuggestions]).slice(0, 7);
}
