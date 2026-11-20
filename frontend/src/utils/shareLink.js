/*
============================================================
Lien de partage d'un parcours.

Le lien ne contient pas le tracé, seulement ce qu'il faut pour le recalculer : point de départ, distance et
forme (ou texte). Quiconque l'ouvre obtient les mêmes propositions, sans compte ni base de données.
Un dessin libre est trop long pour tenir dans une adresse : il n'est pas partageable de cette façon.
============================================================
*/
import { MAX_TEXT_LENGTH, SHAPES } from "../config";

// Adresse partageable, ou null si le choix actuel ne peut pas l'être (dessin libre, pas de départ).
export function buildShareUrl({ center, distanceKm, drawing }) {
  if (!center || drawing?.mode === "custom") return null;
  const params = new URLSearchParams({
    lat: center[0].toFixed(5),
    lon: center[1].toFixed(5),
    km: String(distanceKm),
  });
  if (drawing.mode === "text") params.set("text", drawing.text || "");
  else params.set("shape", drawing.shape);
  return `${window.location.origin}${window.location.pathname}?${params}`;
}

// Lit les paramètres d'un lien de partage. Renvoie { center, distanceKm, drawing } ou null s'il est absent ou invalide.
export function parseShareParams(search) {
  const params = new URLSearchParams(search);
  const lat = Number(params.get("lat"));
  const lon = Number(params.get("lon"));
  const km = Number(params.get("km"));
  if (!params.has("lat") || !params.has("lon") || !params.has("km")) return null;
  if (!(Math.abs(lat) <= 90) || !(Math.abs(lon) <= 180) || !(km >= 1 && km <= 500)) return null;

  const text = (params.get("text") || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9 ]/g, "").slice(0, MAX_TEXT_LENGTH).trim();
  const shape = params.get("shape");
  let drawing;
  if (text) drawing = { mode: "text", shape: "heart", text, points: [] };
  else if (SHAPES.some((item) => item.id === shape)) drawing = { mode: "shape", shape, text: "P2I", points: [] };
  else return null;

  return { center: [lat, lon], distanceKm: Math.round(km), drawing };
}
