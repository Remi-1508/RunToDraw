/*
============================================================
Recherche d'adresses et de lieux (autocomplétion).

Deux services sont interrogés EN PARALLÈLE, avec la saisie telle quelle
(majuscules et accents conservés, ils aident au classement) :

1) Géoplateforme de l'IGN (data.geopf.fr/geocodage/search) : le géocodeur
   officiel français, qui a remplacé api-adresse.data.gouv.fr. Il s'appuie sur
   la Base Adresse Nationale (adresses, rues, communes) et la BD TOPO (lieux :
   gares, parcs, stades…). Très pertinent en France, autocomplétion incluse,
   limité à 50 requêtes/s par adresse IP.
2) Photon (photon.komoot.io), basé sur OpenStreetMap : couvre le reste du monde
   et les lieux absents des données IGN.

Les résultats IGN passent en premier quand il y en a ; ceux de Photon complètent
la liste en évitant les doublons (même lieu à moins de 150 m, même nom).

Nominatim n'est plus utilisé : sa politique d'utilisation interdit
l'autocomplétion (« search-as-you-type ») côté client.

Les réponses sont gardées en cache pendant la session, et chaque requête peut être
annulée (AbortController) quand l'utilisateur continue de taper.
============================================================
*/

const IGN_URL = "https://data.geopf.fr/geocodage/search";
const PHOTON_URL = "https://photon.komoot.io/api/";
const MAX_RESULTS = 7;
const CACHE_SIZE = 60;

const cache = new Map();

// Types IGN (BAN) -> libellé lisible
const ADDRESS_KIND = {
  housenumber: "Adresse",
  street: "Rue",
  locality: "Lieu-dit",
  municipality: "Commune",
};

function first(value) {
  return Array.isArray(value) ? value[0] : value;
}

function distanceMeters(a, b) {
  const toRad = (d) => (d * Math.PI) / 180;
  const x = toRad(b.lon - a.lon) * Math.cos(toRad((a.lat + b.lat) / 2));
  const y = toRad(b.lat - a.lat);
  return Math.hypot(x, y) * 6371000;
}

function normalizeName(text) {
  return String(text ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function fromIgn(feature) {
  const p = feature.properties ?? {};
  const [lon, lat] = feature.geometry?.coordinates ?? [];
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  if (p._type === "poi") {
    const name = first(p.toponym) || first(p.name);
    const category = first(p.category);
    const city = first(p.city);
    return {
      id: `ign-poi-${p.extrafields?.cleabs ?? `${lat},${lon}`}`,
      title: name,
      subtitle: [city, category].filter(Boolean).join(" · "),
      kind: "Lieu",
      lat,
      lon,
    };
  }

  // Adresse, rue ou commune (Base Adresse Nationale)
  const isMunicipality = p.type === "municipality";
  return {
    id: `ign-${p.id ?? `${lat},${lon}`}`,
    title: p.name || p.label,
    subtitle: isMunicipality
      ? [p.postcode, p.context].filter(Boolean).join(" · ")
      : [p.postcode, p.city].filter(Boolean).join(" "),
    kind: ADDRESS_KIND[p.type] ?? "Adresse",
    lat,
    lon,
  };
}

function fromPhoton(feature) {
  const p = feature.properties ?? {};
  const [lon, lat] = feature.geometry?.coordinates ?? [];
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  const streetLine = [p.housenumber, p.street].filter(Boolean).join(" ");
  const title = p.name || streetLine || p.city || p.country;
  const place = [p.postcode, p.city || p.county].filter(Boolean).join(" ");
  const subtitle = [p.name && streetLine ? streetLine : null, place, p.countrycode !== "FR" ? p.country : null]
    .filter(Boolean)
    .join(" · ");

  let kind = "Lieu";
  if (["city", "town", "village"].includes(p.type)) kind = "Commune";
  else if (p.type === "street") kind = "Rue";
  else if (p.housenumber) kind = "Adresse";

  return {
    id: `photon-${p.osm_type ?? ""}${p.osm_id ?? `${lat},${lon}`}`,
    title,
    subtitle,
    kind,
    lat,
    lon,
  };
}

async function fetchJson(url, signal) {
  const res = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function searchIgn(query, bias, signal) {
  const params = new URLSearchParams({
    q: query,
    index: "address,poi",
    limit: String(MAX_RESULTS),
    autocomplete: "1",
  });
  if (bias) {
    params.set("lat", bias[0].toFixed(5));
    params.set("lon", bias[1].toFixed(5));
  }
  return fetchJson(`${IGN_URL}?${params}`, signal).then((data) =>
    (data.features ?? []).map(fromIgn).filter(Boolean)
  );
}

function searchPhoton(query, bias, signal) {
  const params = new URLSearchParams({ q: query, limit: "5", lang: "fr" });
  if (bias) {
    params.set("lat", bias[0].toFixed(5));
    params.set("lon", bias[1].toFixed(5));
  }
  return fetchJson(`${PHOTON_URL}?${params}`, signal).then((data) =>
    (data.features ?? []).map(fromPhoton).filter(Boolean)
  );
}

function merge(primary, secondary) {
  const out = [...primary];
  for (const s of secondary) {
    const duplicate = out.some(
      (o) => normalizeName(o.title) === normalizeName(s.title) && distanceMeters(o, s) < 150
    );
    if (!duplicate) out.push(s);
  }
  return out.slice(0, MAX_RESULTS);
}

/**
 * Cherche des adresses et des lieux correspondant à `query`.
 * @param {string} query texte saisi (au moins 3 caractères conseillés)
 * @param {{ bias?: [number, number], signal?: AbortSignal }} options
 *   bias : [lat, lon] pour favoriser les résultats proches
 * @returns {Promise<Array<{id, title, subtitle, kind, lat, lon}>>}
 *   Rejette seulement si les deux services échouent.
 */
export async function searchPlaces(query, { bias, signal } = {}) {
  const q = query.trim();
  const key = `${q.toLowerCase()}|${bias ? bias.map((v) => v.toFixed(2)).join(",") : ""}`;
  if (cache.has(key)) return cache.get(key);

  const [ign, photon] = await Promise.allSettled([
    searchIgn(q, bias, signal),
    searchPhoton(q, bias, signal),
  ]);

  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
  if (ign.status === "rejected" && photon.status === "rejected") {
    throw ign.reason;
  }

  const results = merge(
    ign.status === "fulfilled" ? ign.value : [],
    photon.status === "fulfilled" ? photon.value : []
  );

  cache.set(key, results);
  if (cache.size > CACHE_SIZE) cache.delete(cache.keys().next().value);
  return results;
}
