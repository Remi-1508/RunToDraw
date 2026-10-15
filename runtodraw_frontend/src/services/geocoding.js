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
2) Pour le reste du monde :
   - Geoapify (api.geoapify.com) si une clé est configurée (VITE_GEOAPIFY_KEY) :
     rapide, gratuit jusqu'à 3 000 requêtes/jour, clé limitable à son propre site ;
   - sinon Photon (photon.komoot.io), sans clé mais serveur public souvent très lent
     (jusqu'à 30 s mesurées).

Classement : l'IGN renvoie toujours des résultats, même pour une recherche étrangère
(« times square new york » donne des « Rue de New-York » françaises, avec un score faible).
On s'appuie donc sur son score de pertinence (0 à 1) :
  1) résultats IGN fiables (score >= 0,6), au plus 5, pour laisser de la place au reste du monde,
  2) résultats internationaux (Geoapify ou Photon),
  3) résultats IGN faibles, en dernier.
Les doublons (même nom à moins de 150 m) sont retirés.

Nominatim n'est plus utilisé : sa politique d'utilisation interdit
l'autocomplétion (« search-as-you-type ») côté client.

Les réponses sont gardées en cache pendant la session, et chaque requête peut être
annulée (AbortController) quand l'utilisateur continue de taper.
============================================================
*/

const IGN_URL = "https://data.geopf.fr/geocodage/search";
const PHOTON_URL = "https://photon.komoot.io/api/";
const GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/autocomplete";
const GEOAPIFY_KEY = import.meta.env?.VITE_GEOAPIFY_KEY || "";
const MAX_RESULTS = 7;
const MAX_STRONG_IGN = 5;
const IGN_STRONG_SCORE = 0.6;
const CACHE_SIZE = 60;
// Le service international n'est interrogé qu'une fois la saisie stabilisée, une seule requête
// à la fois, avec un délai maximal : cela économise le quota gratuit de Geoapify et évite que
// Photon (serveur public lent) empile les requêtes.
const WORLD_EXTRA_DELAY_MS = 350;
// Photon peut mettre ~30 s quand son serveur public est chargé : on lui laisse 45 s.
const WORLD_TIMEOUT_MS = GEOAPIFY_KEY ? 8000 : 45000;

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

// Deuxième ligne d'une suggestion : « Ville · Code postal » (le drapeau est ajouté par l'interface).
function placeLine(city, postcode) {
  return [city, postcode].filter(Boolean).join(" · ");
}

function fromIgn(feature) {
  const p = feature.properties ?? {};
  const [lon, lat] = feature.geometry?.coordinates ?? [];
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  if (p._type === "poi") {
    const city = first(p.city);
    // Un lieu peut couvrir plusieurs codes postaux : on n'en affiche un que s'il est unique.
    const postcodes = Array.isArray(p.postcode) ? p.postcode : [p.postcode].filter(Boolean);
    const postcode = postcodes.length === 1 ? postcodes[0] : "";
    return {
      id: `ign-poi-${p.extrafields?.cleabs ?? `${lat},${lon}`}`,
      title: first(p.toponym) || first(p.name),
      city,
      postcode,
      subtitle: placeLine(city, postcode),
      kind: "Lieu",
      countryCode: "fr",
      country: "France",
      score: p.score ?? 0,
      lat,
      lon,
    };
  }

  // Adresse, rue, lieu-dit ou commune (Base Adresse Nationale)
  const city = p.city || p.name;
  return {
    id: `ign-${p.id ?? `${lat},${lon}`}`,
    title: p.name || p.label,
    city,
    postcode: p.postcode || "",
    subtitle: placeLine(city, p.postcode),
    kind: ADDRESS_KIND[p.type] ?? "Adresse",
    countryCode: "fr",
    country: "France",
    score: p.score ?? 0,
    lat,
    lon,
  };
}

function fromPhoton(feature) {
  const p = feature.properties ?? {};
  const [lon, lat] = feature.geometry?.coordinates ?? [];
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  const streetLine = [p.housenumber, p.street].filter(Boolean).join(" ");
  const isPlaceName = ["city", "town", "village"].includes(p.type);
  const title = p.name || streetLine || p.city || p.country;
  // Pour une commune, la « ville » de la deuxième ligne est sa région ; sinon la ville elle-même.
  const city = isPlaceName ? p.state || p.county || "" : p.city || p.county || p.state || "";

  let kind = "Lieu";
  if (isPlaceName) kind = "Commune";
  else if (p.type === "street") kind = "Rue";
  else if (p.housenumber) kind = "Adresse";

  return {
    id: `photon-${p.osm_type ?? ""}${p.osm_id ?? `${lat},${lon}`}`,
    title,
    city,
    postcode: p.postcode || "",
    subtitle: placeLine(city, p.postcode),
    kind,
    countryCode: (p.countrycode || "").toLowerCase(),
    country: p.country || "",
    lat,
    lon,
  };
}

const GEOAPIFY_KIND = {
  amenity: "Lieu",
  building: "Adresse",
  street: "Rue",
  suburb: "Quartier",
  district: "Quartier",
  postcode: "Code postal",
  city: "Commune",
  county: "Région",
  state: "Région",
  country: "Pays",
};

function fromGeoapify(r) {
  const lat = Number(r.lat);
  const lon = Number(r.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  const city = r.result_type === "city" ? r.state || r.county || "" : r.city || r.county || r.state || "";
  return {
    id: `geoapify-${r.place_id ?? `${lat},${lon}`}`,
    title: r.address_line1 || r.name || r.formatted,
    city,
    postcode: r.postcode || "",
    subtitle: placeLine(city, r.postcode),
    kind: GEOAPIFY_KIND[r.result_type] ?? "Lieu",
    countryCode: (r.country_code || "").toLowerCase(),
    country: r.country || "",
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

const photonCache = new Map();
let photonInFlight = null;

function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    }, { once: true });
  });
}

function worldRequest(query, bias) {
  if (GEOAPIFY_KEY) {
    const params = new URLSearchParams({ text: query, limit: "5", lang: "fr", format: "json", apiKey: GEOAPIFY_KEY });
    if (bias) params.set("bias", `proximity:${bias[1].toFixed(2)},${bias[0].toFixed(2)}`);
    return {
      url: `${GEOAPIFY_URL}?${params}`,
      parse: (data) => (data.results ?? data.features?.map((f) => f.properties) ?? []).map(fromGeoapify).filter(Boolean),
    };
  }
  const params = new URLSearchParams({ q: query, limit: "5", lang: "fr" });
  if (bias) {
    params.set("lat", bias[0].toFixed(2));
    params.set("lon", bias[1].toFixed(2));
  }
  return {
    url: `${PHOTON_URL}?${params}`,
    parse: (data) => (data.features ?? []).map(fromPhoton).filter(Boolean),
  };
}

export const WORLD_SERVICE = GEOAPIFY_KEY ? "Geoapify" : "Photon";

async function searchWorld(query, bias, signal, onPhase) {
  const { url, parse } = worldRequest(query, bias);
  if (photonCache.has(url)) return photonCache.get(url);

  // Attendre que la saisie soit stable : si l'utilisateur tape encore, cette recherche est annulée
  // avant même d'avoir sollicité le service.
  await wait(WORLD_EXTRA_DELAY_MS, signal);

  // Une seule requête à la fois : la précédente (devenue inutile) est interrompue.
  photonInFlight?.abort();
  const controller = new AbortController();
  photonInFlight = controller;
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort, { once: true });
  const timer = setTimeout(() => controller.abort(), WORLD_TIMEOUT_MS);
  onPhase?.("world-start");

  try {
    const data = await fetchJson(url, controller.signal);
    const results = parse(data);
    photonCache.set(url, results);
    if (photonCache.size > CACHE_SIZE) photonCache.delete(photonCache.keys().next().value);
    return results;
  } catch (error) {
    if (error?.name === "AbortError" && !signal?.aborted) {
      const error = new Error(`${WORLD_SERVICE} : pas de réponse après ${WORLD_TIMEOUT_MS / 1000} s`);
      error.name = "WorldTimeout";
      throw error;
    }
    throw error;
  } finally {
    onPhase?.("world-end");
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
    if (photonInFlight === controller) photonInFlight = null;
  }
}

function merge(ign, world) {
  const strong = ign.filter((r) => r.score >= IGN_STRONG_SCORE);
  const weak = ign.filter((r) => r.score < IGN_STRONG_SCORE);
  const ordered = [...strong.slice(0, MAX_STRONG_IGN), ...world, ...strong.slice(MAX_STRONG_IGN), ...weak];

  const out = [];
  for (const s of ordered) {
    const duplicate = out.some(
      (o) => normalizeName(o.title) === normalizeName(s.title) && distanceMeters(o, s) < 150
    );
    if (!duplicate) out.push(s);
    if (out.length === MAX_RESULTS) break;
  }
  return out;
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
 * @param {{ bias?: [number, number], signal?: AbortSignal, onUpdate?: Function, onPhase?: Function }} options
 *   bias : [lat, lon] pour favoriser les résultats proches
 *   onPhase("world-start" | "world-end") : début et fin de la recherche internationale
 *   (plus lente), pour l'indiquer à l'utilisateur
 * @returns {Promise<Array<{id, title, city, postcode, subtitle, kind, countryCode, country, lat, lon}>>} la liste finale ;
 *   countryCode : code pays ISO 3166 en minuscules ("fr", "gb"…), vide si inconnu
 *   rejette seulement si les deux services échouent.
 */
export function searchPlaces(query, { bias, signal, onUpdate, onPhase } = {}) {
  const q = query.trim();
  const key = `${q.toLowerCase()}|${bias ? bias.map((v) => v.toFixed(2)).join(",") : ""}`;
  if (cache.has(key)) {
    const cached = cache.get(key);
    onUpdate?.(cached);
    return Promise.resolve(cached);
  }

  let ign = null;
  let world = null;
  let pending = 2;
  let failures = 0;
  let firstError = null;

  return new Promise((resolve, reject) => {
    const settle = () => {
      pending -= 1;
      if (pending > 0) return;
      if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
      if (failures === 2) return reject(firstError);
      const results = merge(ign ?? [], world ?? []);
      // Rien trouvé en France et le service international n'a pas répondu : ce n'est pas
      // « aucun résultat », on le signale (sans mettre en cache).
      if (!results.length && worldError) return reject(worldError);
      cache.set(key, results);
      if (cache.size > CACHE_SIZE) cache.delete(cache.keys().next().value);
      resolve(results);
    };
    const onResult = (setter) => (value) => {
      setter(value);
      if (!signal?.aborted) onUpdate?.(merge(ign ?? [], world ?? []));
    };
    let worldError = null;
    const onError = (error) => {
      failures += 1;
      firstError = firstError ?? error;
    };
    const onWorldError = (error) => {
      worldError = error;
      onError(error);
    };

    timed("IGN", searchIgn(q, bias, signal))
      .then(onResult((v) => { ign = v; }), onError)
      .finally(settle);
    timed(WORLD_SERVICE, searchWorld(q, bias, signal, onPhase))
      .then(onResult((v) => { world = v; }), onWorldError)
      .finally(settle);
  });
}
