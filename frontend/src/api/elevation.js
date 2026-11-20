/*
============================================================
Dénivelé d'un itinéraire.

Le tracé est ré-échantillonné à intervalles réguliers, puis les altitudes sont demandées :
1. à l'IGN (service d'altimétrie de la Géoplateforme, gratuit, sans clé, très précis en France) ;
2. à défaut (hors de France, ou service injoignable), à Open-Meteo (modèle mondial d'une maille d'environ 90 m).
Le dénivelé positif/négatif est calculé sur des altitudes lissées, en ignorant les variations inférieures
à quelques mètres (le bruit du modèle gonflerait sinon le total).

Open-Meteo limite le nombre de points demandés par minute (chaque point compte) : on n'y envoie donc qu'un
échantillon réduit, et un nombre limité de requêtes part en même temps. Les résultats sont gardés en mémoire :
le même tracé n'est jamais demandé deux fois, même si plusieurs composants l'affichent. Si aucun service ne
répond, la fonction renvoie `null` et l'interface n'affiche simplement pas de chiffre.
============================================================
*/
import { flattenRoutePoints, haversineMeters } from "../utils/routeExport.js";

const IGN_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json";
const IGN_STEP_M = 40;
const SAMPLE_STEP_M = IGN_STEP_M; // pas par défaut du ré-échantillonnage
const IGN_MAX_SAMPLES = 450;
const IGN_BATCH_SIZE = 150; // l'adresse de la requête contient toutes les coordonnées : on la garde courte
const IGN_NO_DATA = -9000; // l'IGN renvoie -99999 hors de sa couverture

const METEO_URL = "https://api.open-meteo.com/v1/elevation";
const METEO_STEP_M = 100;
const METEO_MAX_SAMPLES = 80; // une seule requête, pour ménager la limite de points par minute

const NOISE_THRESHOLD_M = 2; // variation minimale comptée comme une montée ou une descente
const FAILURE_RETRY_MS = 60_000; // après un échec, on ne redemande pas avant une minute

const cache = new Map(); // clé de tracé -> { promise, failedAt }

// Au plus 2 requêtes en même temps, même si plusieurs tracés demandent leur dénivelé simultanément.
const MAX_PARALLEL = 2;
let running = 0;
const waiting = [];
function limited(task) {
  return new Promise((resolve, reject) => {
    const run = () => {
      running += 1;
      task()
        .then(resolve, reject)
        .finally(() => {
          running -= 1;
          waiting.shift()?.();
        });
    };
    if (running < MAX_PARALLEL) run();
    else waiting.push(run);
  });
}

// Points du tracé espacés régulièrement le long de la ligne (interpolation linéaire).
export function resampleRoute(points, stepM = SAMPLE_STEP_M) {
  if (points.length < 2) return points.slice();
  const out = [points[0]];
  let carried = 0; // distance parcourue depuis le dernier échantillon
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    const length = haversineMeters(a, b);
    let travelled = stepM - carried;
    while (travelled <= length) {
      const t = travelled / length;
      out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
      travelled += stepM;
    }
    carried = length - (travelled - stepM);
  }
  out.push(points[points.length - 1]);
  return out;
}

// Moyenne glissante sur 5 valeurs : adoucit les marches d'escalier du modèle de terrain.
export function smooth(values, radius = 2) {
  return values.map((_, i) => {
    let sum = 0;
    let count = 0;
    for (let j = Math.max(0, i - radius); j <= Math.min(values.length - 1, i + radius); j += 1) {
      sum += values[j];
      count += 1;
    }
    return sum / count;
  });
}

// Dénivelé positif et négatif : une montée ou une descente n'est comptée qu'une fois dépassé le seuil de bruit.
export function computeGainLoss(altitudes, threshold = NOISE_THRESHOLD_M) {
  if (altitudes.length < 2) return { gainM: 0, lossM: 0 };
  let gain = 0;
  let loss = 0;
  let reference = altitudes[0];
  for (const altitude of altitudes) {
    const delta = altitude - reference;
    if (delta >= threshold) {
      gain += delta;
      reference = altitude;
    } else if (delta <= -threshold) {
      loss -= delta;
      reference = altitude;
    }
  }
  return { gainM: Math.round(gain), lossM: Math.round(loss) };
}

// Altitudes IGN, ou null si un point sort de leur couverture (hors de France).
async function fetchIgnAltitudes(samples) {
  const altitudes = [];
  for (let i = 0; i < samples.length; i += IGN_BATCH_SIZE) {
    const batch = samples.slice(i, i + IGN_BATCH_SIZE);
    const params = new URLSearchParams({
      lon: batch.map((p) => p[1].toFixed(5)).join("|"),
      lat: batch.map((p) => p[0].toFixed(5)).join("|"),
      resource: "ign_rge_alti_wld",
      zonly: "true",
    });
    const response = await limited(() => fetch(`${IGN_URL}?${params}`));
    if (!response.ok) throw new Error(`Altimétrie IGN indisponible (${response.status})`);
    const data = await response.json();
    if (!Array.isArray(data.elevations) || data.elevations.length !== batch.length) {
      throw new Error("Réponse d'altimétrie inattendue");
    }
    if (data.elevations.some((value) => value <= IGN_NO_DATA)) return null;
    altitudes.push(...data.elevations);
  }
  return altitudes;
}

async function fetchMeteoAltitudes(samples) {
  const params = new URLSearchParams({
    latitude: samples.map((p) => p[0].toFixed(5)).join(","),
    longitude: samples.map((p) => p[1].toFixed(5)).join(","),
  });
  const response = await limited(() => fetch(`${METEO_URL}?${params}`));
  if (!response.ok) throw new Error(`Altitudes indisponibles (${response.status})`);
  const data = await response.json();
  if (!Array.isArray(data.elevation) || data.elevation.length !== samples.length) {
    throw new Error("Réponse d'altitudes inattendue");
  }
  return data.elevation;
}

// Altitudes IGN d'abord ; sinon (hors de France, service en panne) Open-Meteo avec un échantillon réduit.
async function fetchAltitudes(points, totalDistanceM) {
  try {
    const step = Math.max(IGN_STEP_M, totalDistanceM / IGN_MAX_SAMPLES);
    const ign = await fetchIgnAltitudes(resampleRoute(points, step));
    if (ign) return ign;
  } catch {
    // on essaie le service mondial
  }
  const step = Math.max(METEO_STEP_M, totalDistanceM / METEO_MAX_SAMPLES);
  return fetchMeteoAltitudes(resampleRoute(points, step));
}

// Clé d'un tracé : assez précise pour distinguer deux tracés différents, sans stocker tous les points.
function routeKey(route, points) {
  const first = points[0];
  const last = points[points.length - 1];
  return [route.id, points.length, Math.round(route.total_distance_m), first, last].join("|");
}

/** Dénivelé de l'itinéraire : `{ gainM, lossM }`, ou `null` si les altitudes ne sont pas disponibles. */
export function getRouteElevation(route) {
  const points = flattenRoutePoints(route);
  if (points.length < 2) return Promise.resolve(null);
  const key = routeKey(route, points);
  const entry = cache.get(key);
  if (entry && !(entry.failedAt && Date.now() - entry.failedAt > FAILURE_RETRY_MS)) return entry.promise;

  const record = { failedAt: 0 };
  record.promise = fetchAltitudes(points, route.total_distance_m || 0)
    .then((altitudes) => computeGainLoss(smooth(altitudes)))
    .catch(() => {
      record.failedAt = Date.now(); // on pourra réessayer plus tard, pas immédiatement
      return null;
    });
  cache.set(key, record);
  return record.promise;
}
