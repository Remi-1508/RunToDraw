import L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
import { Marker, Polyline, useMap } from "react-leaflet";

// Couche d'édition du tracé (affichée sur la carte quand le mode « Modifier » est actif).
//
// - Chaque point d'ancrage du tracé est un petit rond déplaçable : on le dépose ailleurs, le serveur
//   recalcule les deux tronçons voisins sur les vraies routes.
// - Cliquer sur un rond le sélectionne (pour le supprimer avec Suppr ou le bouton de la barre d'outils).
// - Appuyer sur le tracé et tirer crée un nouveau point à l'endroit où on relâche (comme sur Strava).
// - Pendant le glissement, une ligne pointillée montre où le tracé va passer ; le recalcul exact sur les
//   rues a lieu au relâchement.
//
// Les liaisons entre lettres (kind « link ») ne se modifient pas : elles suivent leurs lettres.

const PREVIEW_STYLE = { color: "#007aff", weight: 4, opacity: 0.9, dashArray: "4 8", interactive: false };

// Distance (au carré, dans un repère local approximatif) entre deux points [lat, lon]. Sert uniquement à
// trouver le point du tracé le plus proche d'un clic : pas besoin d'une vraie distance géodésique.
function squaredDistance(a, b, cosLat) {
  const dy = a[0] - b[0];
  const dx = (a[1] - b[1]) * cosLat;
  return dx * dx + dy * dy;
}

// Numéro du tronçon (entre l'ancrage k et k+1) auquel appartient l'endroit cliqué sur le tracé.
function legAtPoint(segment, latlng) {
  const cosLat = Math.cos((latlng.lat * Math.PI) / 180);
  const target = [latlng.lat, latlng.lng];
  let nearest = 0;
  let best = Infinity;
  segment.points.forEach((point, index) => {
    const d = squaredDistance(point, target, cosLat);
    if (d < best) {
      best = d;
      nearest = index;
    }
  });
  let leg = 0;
  segment.anchors.forEach((position, k) => {
    if (position <= nearest) leg = k;
  });
  return Math.min(leg, segment.anchors.length - 2);
}

// Icône d'un point d'ancrage (un rond ; plus grand et rouge quand il est sélectionné).
function anchorIcon(selected, isEnd) {
  const size = selected ? 20 : isEnd ? 16 : 14;
  const border = selected ? "#ff3b30" : "#ffffff";
  const fill = selected ? "#ff3b30" : isEnd ? "#007aff" : "#ffffff";
  const ring = selected ? "#ffffff" : "#007aff";
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html:
      `<div style="width:${size}px;height:${size}px;box-sizing:border-box;border-radius:50%;` +
      `background:${fill};border:3px solid ${selected ? border : ring};` +
      `box-shadow:0 1px 4px rgba(0,0,0,.45);cursor:grab"></div>`,
  });
}

// Position (lat, lon) du point d'ancrage k d'un segment.
function anchorPoint(segment, k) {
  return segment.points[segment.anchors[k]];
}

export default function RouteEditLayer({ route, pending, selectedAnchor, onSelect, onOperation }) {
  const map = useMap();
  // Aperçu pointillé pendant un glissement : { points: [[lat, lon], ...] }.
  const [preview, setPreview] = useState(null);
  // Glissement d'insertion en cours : { segmentIndex, leg }. `moved` (ref : lu à chaud par les écouteurs
  // de la page) indique si la souris a réellement bougé, pour qu'un simple clic sur le tracé ne crée rien.
  const [insertion, setInsertion] = useState(null);
  const movedRef = useRef(false);

  // Insertion : tant que le bouton est enfoncé, on suit la souris sur toute la page (même hors de la
  // carte) ; au relâchement, on demande au serveur d'ajouter le point là où on est.
  useEffect(() => {
    if (!insertion) return undefined;
    const segment = route.segments[insertion.segmentIndex];
    const before = anchorPoint(segment, insertion.leg);
    const after = anchorPoint(segment, insertion.leg + 1);
    map.dragging.disable();

    function toLatLng(event) {
      return map.mouseEventToLatLng(event);
    }
    function onMove(event) {
      const latlng = toLatLng(event);
      movedRef.current = true;
      setPreview({ points: [before, [latlng.lat, latlng.lng], after] });
    }
    function onUp(event) {
      const latlng = toLatLng(event);
      setPreview(null);
      setInsertion(null);
      if (movedRef.current) {
        onOperation(insertion.segmentIndex, { type: "insert", anchor: insertion.leg, lat: latlng.lat, lon: latlng.lng });
      }
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      map.dragging.enable();
    };
  }, [insertion, map, route, onOperation]);

  const editableSegments = useMemo(
    () => route.segments.map((segment, index) => ({ segment, index })).filter(({ segment }) => segment.kind !== "link" && segment.anchors?.length >= 2),
    [route]
  );

  return (
    <>
      {/* Zones d'accroche invisibles et larges le long du tracé, pour y « attraper » la ligne. */}
      {editableSegments.map(({ segment, index }) => (
        <Polyline
          key={`grab-${route.id}-${index}`}
          positions={segment.points}
          pathOptions={{ color: "#000", weight: 22, opacity: 0, lineCap: "round" }}
          eventHandlers={{
            mousedown: (event) => {
              if (pending) return;
              L.DomEvent.stop(event.originalEvent);
              movedRef.current = false;
              setInsertion({ segmentIndex: index, leg: legAtPoint(segment, event.latlng) });
            },
          }}
        />
      ))}

      {editableSegments.flatMap(({ segment, index }) =>
        segment.anchors.map((position, k) => {
          const isSelected = selectedAnchor?.segmentIndex === index && selectedAnchor?.anchor === k;
          const isEnd = k === 0 || k === segment.anchors.length - 1;
          const point = segment.points[position];
          return (
            <Marker
              key={`anchor-${route.id}-${index}-${k}-${position}`}
              position={point}
              icon={anchorIcon(isSelected, isEnd)}
              draggable={!pending}
              zIndexOffset={isSelected ? 1000 : 0}
              eventHandlers={{
                click: (event) => {
                  L.DomEvent.stop(event.originalEvent);
                  onSelect(index, k);
                },
                drag: (event) => {
                  const { lat, lng } = event.target.getLatLng();
                  const neighbours = [];
                  if (k > 0) neighbours.push(anchorPoint(segment, k - 1));
                  neighbours.push([lat, lng]);
                  if (k + 1 < segment.anchors.length) neighbours.push(anchorPoint(segment, k + 1));
                  setPreview({ points: neighbours });
                },
                dragend: async (event) => {
                  const marker = event.target;
                  const { lat, lng } = marker.getLatLng();
                  setPreview(null);
                  const ok = await onOperation(index, { type: "move", anchor: k, lat, lon: lng });
                  // Refusé (trop loin des routes, inaccessible…) : le point revient à sa place.
                  if (!ok) marker.setLatLng(point);
                },
              }}
            />
          );
        })
      )}

      {preview && <Polyline positions={preview.points} pathOptions={PREVIEW_STYLE} />}
    </>
  );
}
