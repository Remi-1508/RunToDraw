/*
============================================================
Dénivelé d'un itinéraire.

Le tracé est ré-échantillonné tous les ~50 m, puis les altitudes sont demandées au service gratuit
Open-Meteo (modèle numérique de terrain, maille d'environ 90 m, 100 points par requête, sans clé).
Le dénivelé positif/négatif est ensuite calculé sur des altitudes lissées, en ignorant les variations
inférieures à quelques mètres (le bruit du modèle gonflerait sinon le total).

Les résultats sont gardés en mémoire : le même tracé n'est jamais demandé deux fois, même si plusieurs
composants l'affichent en même temps. Si le service est injoignable, la fonction renvoie `null` et
l'interface n'affiche simplement pas le dénivelé.
============================================================
*/
import { flattenRoutePoints, haversineMeters } from "../utils/routeExport";

const ELEVATION_URL = "https://api.open-meteo.com/v1/elevation";
const SAMPLE_STEP_M = 50;
const MAX_SAMPLES = 600; // au-delà, on espace les échantillons (6 requêtes au plus)
const BATCH_SIZE = 100; // maximum accepté par le service
const NOISE_THRESHOLD_M = 3; // variation minimale comptée comme une montée ou une descente

const cache = new Map(); // clé de tracé -> promesse du résultat

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

async function fetchAltitudes(samples) {
  const altitudes = [];
  for (let i = 0; i < samples.length; i += BATCH_SIZE) {
    const batch = samples.slice(i, i + BATCH_SIZE);
    const params = new URLSearchParams({
      latitude: batch.map((p) => p[0].toFixed(5)).join(","),
      longitude: batch.map((p) => p[1].toFixed(5)).join(","),
    });
    const response = await fetch(`${ELEVATION_URL}?${params}`);
    if (!response.ok) throw new Error(`Altitudes indisponibles (${response.status})`);
    const data = await response.json();
    if (!Array.isArray(data.elevation) || data.elevation.length !== batch.length) {
      throw new Error("Réponse d'altitudes inattendue");
    }
    altitudes.push(...data.elevation);
  }
  return altitudes;
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
  if (!cache.has(key)) {
    const step = Math.max(SAMPLE_STEP_M, (route.total_distance_m || 0) / MAX_SAMPLES);
    const promise = fetchAltitudes(resampleRoute(points, step))
      .then((altitudes) => computeGainLoss(smooth(altitudes)))
      .catch(() => {
        cache.delete(key); // un échec ne doit pas être mémorisé : on pourra réessayer
        return null;
      });
    cache.set(key, promise);
  }
  return cache.get(key);
}
