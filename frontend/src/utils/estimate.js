/*
============================================================
Estimation de la durée d'une génération.

Deux étapes, deux estimations :
- étape 1 (téléchargement du réseau routier) : proportionnelle à la surface de la zone ;
- étape 2 (calcul des tracés) : proportionnelle au nombre de nœuds du graphe et au nombre de recherches à
  faire (une par forme ; pour un mot, une par lettre plus le mot entier).

Les coefficients de départ sont prudents. Après chaque génération réussie, on mesure la durée réelle et on
rapproche les coefficients de ce qui a été observé (moyenne glissante, mémorisée dans le navigateur) : les
estimations deviennent donc plus justes avec l'usage, sur l'appareil et la connexion de la personne.
============================================================
*/
import { readStorage, writeStorage } from "./storage";

const STORAGE_KEY = "runtodraw.timing.v1";
const DEFAULTS = { graphSecPerKm2: 2, planSecPerKNodeUnit: 0.2 };
const SMOOTHING = 0.5; // poids de la mesure la plus récente

function loadRates() {
  try {
    const saved = JSON.parse(readStorage(STORAGE_KEY) || "{}");
    return {
      graphSecPerKm2: Number(saved.graphSecPerKm2) > 0 ? Number(saved.graphSecPerKm2) : DEFAULTS.graphSecPerKm2,
      planSecPerKNodeUnit: Number(saved.planSecPerKNodeUnit) > 0 ? Number(saved.planSecPerKNodeUnit) : DEFAULTS.planSecPerKNodeUnit,
    };
  } catch {
    return { ...DEFAULTS };
  }
}

// Nombre de recherches à faire : 1 pour une forme ou un dessin ; pour un mot, une par lettre + le mot entier.
export function planUnits(drawing) {
  if (drawing?.mode === "text") {
    const letters = (drawing.text || "").replace(/[^A-Z0-9]/gi, "").length;
    return Math.max(letters, 1) + 1;
  }
  return 1;
}

export function estimateGraphSeconds(radiusKm) {
  const areaKm2 = Math.PI * radiusKm * radiusKm;
  return Math.max(4, loadRates().graphSecPerKm2 * areaKm2);
}

export function estimatePlanSeconds(nodeCount, drawing) {
  return Math.max(3, (loadRates().planSecPerKNodeUnit * nodeCount * planUnits(drawing)) / 1000);
}

// Enregistre la durée réellement mesurée d'une étape. Les très courtes (réseau déjà en cache sur le serveur)
// ne sont pas retenues : elles feraient croire que le téléchargement est toujours instantané.
export function recordGraphDuration(radiusKm, seconds) {
  const areaKm2 = Math.PI * radiusKm * radiusKm;
  if (seconds < 3 || areaKm2 <= 0) return;
  const rates = loadRates();
  const measured = seconds / areaKm2;
  rates.graphSecPerKm2 = rates.graphSecPerKm2 * (1 - SMOOTHING) + measured * SMOOTHING;
  writeStorage(STORAGE_KEY, JSON.stringify(rates));
}

export function recordPlanDuration(nodeCount, drawing, seconds) {
  const denominator = (nodeCount * planUnits(drawing)) / 1000;
  if (seconds < 1 || denominator <= 0) return;
  const rates = loadRates();
  const measured = seconds / denominator;
  rates.planSecPerKNodeUnit = rates.planSecPerKNodeUnit * (1 - SMOOTHING) + measured * SMOOTHING;
  writeStorage(STORAGE_KEY, JSON.stringify(rates));
}

// « 45 s », « 1 min 20 s » : durée lisible, arrondie à 5 s au-delà d'une minute.
export function formatDuration(seconds) {
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total} s`;
  const rounded = Math.round(total / 5) * 5;
  const minutes = Math.floor(rounded / 60);
  const rest = rounded % 60;
  return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
}

// Chronomètre « 0:23 ».
export function formatClock(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}
