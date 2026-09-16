import { API_BASE } from "../config";

/*
============================================================
EN:
planRoutes sends the graph and user choices to the backend
so it can calculate route proposals.

The frontend sends:
- the extracted graph
- the requested distance
- the drawing settings (shape or text)

The backend then uses the Python planner to generate
several route candidates.

This function only communicates with the API.

FR:
planRoutes envoie le graphe et les choix utilisateur
au backend pour calculer des propositions d’itinéraires.

Le frontend envoie :
- le graphe extrait
- la distance demandée
- les paramètres du dessin (forme ou texte)

Le backend utilise ensuite le moteur Python pour générer
plusieurs itinéraires candidats.

Cette fonction sert uniquement à communiquer avec l’API.
============================================================
*/
export async function planRoutes({ graphPayload, distanceKm, drawing }) {
  const res = await fetch(`${API_BASE}/api/routes/plan`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    /*
    EN:
    The payload contains everything needed by the planner.

    graph_payload:
    full road graph already extracted earlier

    distance_km:
    target running distance

    drawing:
    user request (shape mode or text mode)

    FR:
    Le payload contient tout ce dont le moteur a besoin.

    graph_payload :
    graphe routier déjà extrait auparavant

    distance_km :
    distance cible

    drawing :
    demande utilisateur (mode forme ou mode texte)
    */
    body: JSON.stringify({
      graph_payload: graphPayload,
      distance_km: distanceKm,
      drawing,
    }),
  });

  /*
  EN:
  If the backend fails, we try to read the response text
  to display a more useful error message.

  FR:
  Si le backend échoue, on essaie de lire le texte renvoyé
  pour afficher un message d’erreur plus utile.
  */
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Route planner HTTP ${res.status}`);
  }

  /*
  EN:
  On success, the backend returns:
  - a summary text
  - several route proposals
  - metrics for each route

  FR:
  En cas de succès, le backend renvoie :
  - un texte résumé
  - plusieurs propositions d’itinéraires
  - des métriques pour chaque trajet
  */
  return res.json();
}

async function readJson(res, context) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${context} HTTP ${res.status}`);
  }
  return res.json();
}

const POLL_INTERVAL_MS = 400;

/*
============================================================
EN:
planRoutesWithProgress uses the background job endpoints instead of a
single blocking request: it starts a job, then polls its status until it
completes. This reports real progress (candidates actually evaluated, not
a simulated timer), and avoids a multi-minute HTTP request that could time
out behind a proxy once deployed.

onProgress(fraction) is called with a 0..1 value as the backend reports it.

FR:
planRoutesWithProgress utilise les endpoints de tâche en arrière-plan au
lieu d’une seule requête bloquante : elle démarre une tâche, puis interroge
son état jusqu’à ce qu’elle se termine. Cela donne une progression réelle
(candidats réellement évalués, pas un minuteur simulé), et évite une
requête HTTP de plusieurs minutes qui pourrait tomber en timeout derrière
un proxy une fois déployée.

onProgress(fraction) est appelée avec une valeur 0..1 telle que renvoyée
par le backend.
============================================================
*/
export async function planRoutesWithProgress({ graphPayload, distanceKm, drawing, onProgress, signal }) {
  const jobRes = await fetch(`${API_BASE}/api/routes/plan/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      graph_payload: graphPayload,
      distance_km: distanceKm,
      drawing,
    }),
    signal,
  });
  const { job_id: jobId } = await readJson(jobRes, "Route planner");

  for (;;) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    const jobStatusRes = await fetch(`${API_BASE}/api/routes/plan/jobs/${jobId}`, { signal });
    const job = await readJson(jobStatusRes, "Route planner");

    onProgress?.(job.progress ?? 0);

    if (job.status === "done") return job.result;
    if (job.status === "error") throw new Error(job.error || "La génération des itinéraires a échoué.");

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}