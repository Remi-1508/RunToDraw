// Client HTTP commun à tous les appels vers le backend RunToDraw.
import { API_BASE } from "../config";

// Erreur d'API portant un message déjà lisible par l'utilisateur.
export class ApiError extends Error {
  constructor(message, { status = 0, retryAfter = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

const FIELD_LABELS = {
  distance_km: "Distance",
  lat: "Position",
  lon: "Position",
  text: "Texte",
  shape: "Forme",
  mode: "Mode",
  tolerance_ratio: "Tolérance",
};

// FastAPI renvoie {"detail": "texte"} pour nos erreurs, et {"detail": [{loc, msg}, ...]} pour les
// erreurs de validation (422) : dans les deux cas on en tire une phrase lisible.
function messageFromDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        const field = [...(item.loc || [])].reverse().find((part) => FIELD_LABELS[part]);
        const msg = String(item.msg || "").replace(/^Value error,\s*/, "");
        return field ? `${FIELD_LABELS[field]} : ${msg}` : msg;
      })
      .join(" ");
  }
  return null;
}

async function toApiError(response, fallback) {
  const text = await response.text();
  let detail = null;
  try {
    detail = messageFromDetail(JSON.parse(text)?.detail);
  } catch {
    // réponse non JSON (page d'erreur d'un proxy, par exemple)
  }
  return new ApiError(detail || `${fallback} (erreur ${response.status}).`, {
    status: response.status,
    retryAfter: Number(response.headers.get("Retry-After")) || null,
  });
}

// Appel JSON vers le backend. `signal` permet d'annuler la requête (AbortController).
export async function request(path, { method = "GET", body, signal, fallback = "Requête impossible" } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("Impossible de joindre le serveur. Vérifie ta connexion ou réessaie dans un instant.");
  }
  if (!response.ok) throw await toApiError(response, fallback);
  return response.json();
}
