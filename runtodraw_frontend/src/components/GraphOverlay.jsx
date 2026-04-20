import { CircleMarker, Polyline } from "react-leaflet";

/*
============================================================
EN:
GraphOverlay displays the exported road graph on the Leaflet map.

It draws:
- road segments as blue lines
- graph nodes as red points

To keep the interface smooth, the number of displayed
segments and nodes is limited.

FR:
GraphOverlay affiche le graphe routier exporté sur la carte Leaflet.

Il dessine :
- les segments routiers en bleu
- les nœuds du graphe en rouge

Pour garder une interface fluide, le nombre de segments
et de nœuds affichés est limité.
============================================================
*/

export default function GraphOverlay({
  nodesById,
  edgesByNode,
  maxSegments = 2000,
  maxNodes = 3000,
}) {
  /*
  EN:
  If graph data is missing, nothing is displayed.

  FR:
  Si les données du graphe sont absentes,
  rien n’est affiché.
  */
  if (!nodesById || !edgesByNode) return null;

  /*
  EN:
  segments:
  Stores all line segments that will be drawn.

  seenEdges:
  Prevents drawing the same edge twice.

  nodeIdsToDraw:
  Stores the nodes that should be displayed.

  FR:
  segments :
  Contient les segments à dessiner.

  seenEdges :
  Empêche d’afficher deux fois la même arête.

  nodeIdsToDraw :
  Contient les nœuds à afficher.
  */
  const segments = [];
  const seenEdges = new Set();
  const nodeIdsToDraw = new Set();

  /*
  ============================================================
  EN:
  Build visible road segments.

  We loop through each node and its neighbors.
  If an edge was already processed, we skip it.

  This is important because in an undirected graph,
  A -> B and B -> A may both exist.

  FR:
  Construction des segments visibles.

  On parcourt chaque nœud et ses voisins.
  Si une arête a déjà été traitée, on l’ignore.

  C’est important car dans un graphe non orienté,
  A -> B et B -> A peuvent exister en même temps.
  ============================================================
  */
  for (const [u, neigh] of edgesByNode.entries()) {
    const U = nodesById.get(u);
    if (!U) continue;

    for (const e of neigh) {
      const v = e.to;
      const V = nodesById.get(v);
      if (!V) continue;

      /*
      EN:
      Create a unique key for the edge.

      FR:
      Création d’une clé unique pour l’arête.
      */
      const a = Math.min(u, v);
      const b = Math.max(u, v);
      const key = `${a}-${b}`;

      if (seenEdges.has(key)) continue;
      seenEdges.add(key);

      /*
      EN:
      Save segment coordinates for drawing.

      FR:
      Sauvegarde des coordonnées du segment.
      */
      segments.push([
        [U.lat, U.lon],
        [V.lat, V.lon],
      ]);

      /*
      EN:
      Nodes used by drawn edges are also marked to be displayed.

      FR:
      Les nœuds utilisés par les segments affichés
      sont aussi marqués pour affichage.
      */
      nodeIdsToDraw.add(u);
      nodeIdsToDraw.add(v);

      /*
      EN:
      Performance limit.

      FR:
      Limite de performance.
      */
      if (segments.length >= maxSegments) break;
    }

    if (segments.length >= maxSegments) break;
  }

  /*
  ============================================================
  EN:
  If we still have room, we add more nodes,
  even if they are not connected to displayed segments.

  This gives a better global visual representation.

  FR:
  S’il reste de la place, on ajoute d’autres nœuds,
  même s’ils ne sont pas liés aux segments affichés.

  Cela donne une meilleure vision globale du graphe.
  ============================================================
  */
  if (nodeIdsToDraw.size < maxNodes) {
    for (const id of nodesById.keys()) {
      nodeIdsToDraw.add(id);

      if (nodeIdsToDraw.size >= maxNodes) break;
    }
  }

  /*
  ============================================================
  EN:
  Final rendering:
  - Blue polylines = roads
  - Red markers = graph nodes

  FR:
  Affichage final :
  - Lignes bleues = routes
  - Points rouges = nœuds du graphe
  ============================================================
  */
  return (
    <>
      {segments.map((seg, i) => (
        <Polyline
          key={i}
          positions={seg}
          pathOptions={{
            color: "#0a84ff",
            weight: 2,
            opacity: 0.7,
          }}
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
            pathOptions={{
              color: "#ff453a",
              fillColor: "#ff453a",
              fillOpacity: 0.8,
            }}
          />
        );
      })}
    </>
  );
}