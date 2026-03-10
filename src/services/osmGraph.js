const OVERPASS_ENDPOINTS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.openstreetmap.ru/api/interpreter",
];

function haversineMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function buildOverpassQueryCircle(lat, lon, radiusMeters) {
  const r = Math.round(radiusMeters);
  return `
[out:json][timeout:180];
(
  way(around:${r},${lat},${lon})["highway"]
    ["highway"!~"motorway|motorway_link|trunk|trunk_link"]
    ["area"!="yes"]
    ["access"!="private"];
);
out body;
>;
out skel qt;
`.trim();
}

async function postOverpass(endpoint, query) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: new URLSearchParams({ data: query }),
  });
  if (!res.ok) throw new Error(`Overpass HTTP ${res.status}`);
  return res.json();
}

async function fetchOverpassWithFallback(query, maxTries = 4) {
  let lastErr = null;
  for (let attempt = 0; attempt < maxTries; attempt++) {
    const endpoint = OVERPASS_ENDPOINTS[attempt % OVERPASS_ENDPOINTS.length];
    try {
      return await postOverpass(endpoint, query);
    } catch (e) {
      lastErr = e;
      await new Promise((r) => setTimeout(r, 800 * (attempt + 1)));
    }
  }
  throw lastErr ?? new Error("Overpass failed");
}

export function countUniqueUndirectedEdges(edgesByNode) {
  const seen = new Set();
  for (const [u, neigh] of edgesByNode.entries()) {
    for (const e of neigh) {
      const v = e.to;
      const a = Math.min(u, v);
      const b = Math.max(u, v);
      seen.add(`${a}-${b}`);
    }
  }
  return seen.size;
}

export function buildGraphFromOverpass(osmJson) {
  const nodesById = new Map();
  const ways = [];

  for (const el of osmJson.elements ?? []) {
    if (el.type === "node") nodesById.set(el.id, { lat: el.lat, lon: el.lon });
    else if (el.type === "way") ways.push(el);
  }

  const edgesByNode = new Map();

  const addEdge = (from, to, w, extra) => {
    if (!edgesByNode.has(from)) edgesByNode.set(from, []);
    edgesByNode.get(from).push({
      to,
      w,
      wayId: extra.wayId,
      oneway: extra.oneway,
      tags: extra.tags,
    });
  };

  for (const way of ways) {
    const ns = way.nodes;
    if (!Array.isArray(ns) || ns.length < 2) continue;

    const onewayTag = (way.tags?.oneway ?? "").toString().toLowerCase();
    const oneway = onewayTag === "yes" || onewayTag === "1" || onewayTag === "true";

    const tags = {
      highway: way.tags?.highway ?? null,
      surface: way.tags?.surface ?? null,
      bridge: way.tags?.bridge ?? null,
      tunnel: way.tags?.tunnel ?? null,
      layer: way.tags?.layer ?? null,
      access: way.tags?.access ?? null,
      foot: way.tags?.foot ?? null,
      sidewalk: way.tags?.sidewalk ?? null,
      lit: way.tags?.lit ?? null,
    };

    for (let i = 0; i < ns.length - 1; i++) {
      const a = ns[i];
      const b = ns[i + 1];

      const A = nodesById.get(a);
      const B = nodesById.get(b);
      if (!A || !B) continue;

      const w = haversineMeters(A.lat, A.lon, B.lat, B.lon);

      addEdge(a, b, w, { wayId: way.id, oneway, tags });
      if (!oneway) addEdge(b, a, w, { wayId: way.id, oneway, tags });
    }
  }

  const edgeCount = countUniqueUndirectedEdges(edgesByNode);
  return { nodesById, edgesByNode, ways, edgeCount };
}

export async function fetchGraphForRun({ lat, lon, distanceKm }) {
  const radiusKm = distanceKm / 2;
  const radiusMeters = radiusKm * 1000;

  const query = buildOverpassQueryCircle(lat, lon, radiusMeters);
  const osm = await fetchOverpassWithFallback(query);

  const graph = buildGraphFromOverpass(osm);
  return { center: [lat, lon], radiusKm, ...graph };
}