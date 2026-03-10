import { Polyline, CircleMarker } from "react-leaflet";

export default function GraphOverlay({
  nodesById,
  edgesByNode,
  maxSegments = 2000,
  maxNodes = 3000,
}) {
  if (!nodesById || !edgesByNode) return null;

  const segments = [];
  const seenEdges = new Set();
  const nodeIdsToDraw = new Set();

  for (const [u, neigh] of edgesByNode.entries()) {
    const U = nodesById.get(u);
    if (!U) continue;

    for (const e of neigh) {
      const v = e.to;
      const V = nodesById.get(v);
      if (!V) continue;

      const a = Math.min(u, v);
      const b = Math.max(u, v);
      const key = `${a}-${b}`;
      if (seenEdges.has(key)) continue;
      seenEdges.add(key);

      segments.push([
        [U.lat, U.lon],
        [V.lat, V.lon],
      ]);

      nodeIdsToDraw.add(u);
      nodeIdsToDraw.add(v);

      if (segments.length >= maxSegments) break;
    }
    if (segments.length >= maxSegments) break;
  }

  // Ajoute d'autres nodes pour montrer que "tous les sommets existent"
  if (nodeIdsToDraw.size < maxNodes) {
    for (const id of nodesById.keys()) {
      nodeIdsToDraw.add(id);
      if (nodeIdsToDraw.size >= maxNodes) break;
    }
  }

  return (
    <>
      {segments.map((seg, i) => (
        <Polyline
          key={i}
          positions={seg}
          pathOptions={{ color: "blue", weight: 2, opacity: 0.7 }}
        />
      ))}

      {Array.from(nodeIdsToDraw).map((id) => {
        const p = nodesById.get(id);
        if (!p) return null;
        return (
          <CircleMarker
            key={id}
            center={[p.lat, p.lon]}
            radius={2}
            pathOptions={{ color: "red" }}
          />
        );
      })}
    </>
  );
}