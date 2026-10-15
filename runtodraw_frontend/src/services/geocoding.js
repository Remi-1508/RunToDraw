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

function timed(label, promise) {
  const start = performance.now();
  return promise.then(
    (value) => {
      console.debug(`[recherche] ${label} : ${Math.round(performance.now() - start)} ms, ${value.length} résultat(s)`);
      return value;
    },
    (error) => {
      if (error?.name !== "AbortError") {
        console.debug(`[recherche] ${label} : échec après ${Math.round(performance.now() - start)} ms`, error);
      }
      throw error;
    }
  );
}

/**
 * Cherche des adresses et des lieux correspondant à `query`.
 *
 * Affichage progressif : `onUpdate(résultats)` est appelé dès que l'un des deux services
 * répond, puis de nouveau quand l'autre complète la liste. On n'attend donc jamais le plus
 * lent des deux pour montrer les premières suggestions.
 *
 * @param {string} query texte saisi (au moins 3 caractères conseillés)
 * @param {{ bias?: [number, number], signal?: AbortSignal, onUpdate?: Function }} options
 *   bias : [lat, lon] pour favoriser les résultats proches
 * @returns {Promise<Array<{id, title, subtitle, kind, lat, lon}>>} la liste finale ;
 *   rejette seulement si les deux services échouent.
 */
export function searchPlaces(query, { bias, signal, onUpdate } = {}) {
  const q = query.trim();
  const key = `${q.toLowerCase()}|${bias ? bias.map((v) => v.toFixed(2)).join(",") : ""}`;
  if (cache.has(key)) {
    const cached = cache.get(key);
    onUpdate?.(cached);
    return Promise.resolve(cached);
  }

  let ign = null;
  let photon = null;
  let pending = 2;
  let failures = 0;
  let firstError = null;

  return new Promise((resolve, reject) => {
    const settle = () => {
      pending -= 1;
      if (pending > 0) return;
      if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
      if (failures === 2) return reject(firstError);
      const results = merge(ign ?? [], photon ?? []);
      cache.set(key, results);
      if (cache.size > CACHE_SIZE) cache.delete(cache.keys().next().value);
      resolve(results);
    };
    const onResult = (setter) => (value) => {
      setter(value);
      if (!signal?.aborted) onUpdate?.(merge(ign ?? [], photon ?? []));
    };
    const onError = (error) => {
      failures += 1;
      firstError = firstError ?? error;
    };

    timed("IGN", searchIgn(q, bias, signal))
      .then(onResult((v) => { ign = v; }), onError)
      .finally(settle);
    timed("Photon", searchPhoton(q, bias, signal))
      .then(onResult((v) => { photon = v; }), onError)
      .finally(settle);
  });
}
