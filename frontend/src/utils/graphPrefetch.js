// Préchargement du réseau routier.
//
// Télécharger le réseau routier est la phase la plus longue d'une génération. Le serveur le garde en mémoire :
// si on le lui demande dès que le départ, la distance et le dessin sont choisis, il est déjà prêt quand la
// personne clique sur « Générer ». La demande part donc en arrière-plan ; son résultat n'est pas utilisé ici.
// Ce fichier retient seulement quelles zones sont prêtes, pour afficher une estimation de durée réaliste.
import { fetchGraph } from "../api/runtodraw";

// Le serveur garde peu de zones en mémoire et finit par les oublier : au-delà de ce délai, on ne s'y fie plus.
const READY_TTL_MS = 10 * 60 * 1000;

const ready = new Map(); // clé de la zone -> instant où elle est devenue prête
let current = null; // préchargement en cours : { key, controller }

// Empreinte d'un dessin libre : nombre de points et somme de leurs coordonnées (deux tracés différents ont
// pratiquement toujours des empreintes différentes ; au pire, la zone est simplement redemandée au serveur).
function pointsSignature(points) {
  const list = points ?? [];
  const sum = list.reduce((total, [x, y]) => total + Math.round(x) + Math.round(y), 0);
  return `${list.length}:${sum}`;
}

// Même zone côté serveur : départ au mètre près, distance, et dessin quand il change le rayon (texte, dessin libre).
function keyOf({ lat, lon, distanceKm, drawing }) {
  const mode = drawing?.mode ?? "shape";
  let detail = "";
  if (mode === "text") detail = String(drawing.text || "").toUpperCase();
  if (mode === "custom") detail = pointsSignature(drawing.points);
  return [lat.toFixed(5), lon.toFixed(5), distanceKm, mode, detail].join("|");
}

// Vrai si le réseau de cette zone a déjà été téléchargé par le serveur il y a peu.
export function isGraphReady(params) {
  const at = ready.get(keyOf(params));
  return at !== undefined && Date.now() - at < READY_TTL_MS;
}

// À appeler quand une génération vient de récupérer le réseau : la zone est prête pour la suivante.
export function markGraphReady(params) {
  ready.set(keyOf(params), Date.now());
}

// Lance le téléchargement en arrière-plan. Une zone déjà prête ou déjà demandée n'est pas redemandée ;
// une demande pour une autre zone remplace la précédente (le serveur termine la sienne tranquillement).
export async function prefetchGraph(params) {
  const key = keyOf(params);
  if (isGraphReady(params) || current?.key === key) return;
  current?.controller.abort();
  const controller = new AbortController();
  const mine = { key, controller };
  current = mine;
  try {
    await fetchGraph(params, { signal: controller.signal });
    markGraphReady(params);
  } catch {
    // Silencieux : c'est un bonus. Si ça échoue, la vraie génération refera la demande et affichera l'erreur.
  } finally {
    if (current === mine) current = null;
  }
}
