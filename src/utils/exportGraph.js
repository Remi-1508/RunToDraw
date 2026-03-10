export function graphToFullJSON({ graphData, distanceKm }) {
  const { center, radiusKm, nodesById, edgesByNode } = graphData;

  const nodes = [];
  for (const [id, p] of nodesById.entries()) {
    nodes.push({ id, lat: p.lat, lon: p.lon });
  }

  const edges = [];
  const seenDirected = new Set();

  for (const [from, neigh] of edgesByNode.entries()) {
    const A = nodesById.get(from);
    if (!A) continue;

    for (const e of neigh) {
      const to = e.to;
      const B = nodesById.get(to);
      if (!B) continue;

      const key = `${from}->${to}`;
      if (seenDirected.has(key)) continue;
      seenDirected.add(key);

      edges.push({
        id: key,
        from,
        to,
        length_m: e.w,
        oneway: !!e.oneway,
        wayId: e.wayId ?? null,
        tags: e.tags ?? {},
        geom: [
          [A.lon, A.lat],
          [B.lon, B.lat],
        ],
      });
    }
  }

  return {
    meta: {
      version: "RunToDraw_graph_v1",
      createdAt: new Date().toISOString(),
      center,
      radiusKm,
      distanceRequestedKm: distanceKm,
      weightUnit: "meters",
      directed: true,
    },
    nodes,
    edges,
  };
}

export function downloadJSON(filename, data) {
  const blob = new Blob([JSON.stringify(data)], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
  return filename;
}