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

const PREVIEW_STYLE = { color: "#fc4c02", weight: 4, opacity: 0.9, dashArray: "4 8", interactive: false };

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

// Icône d'un point d'ancrage (un rond blanc cerclé d'orange ; plus grand et sombre quand il est sélectionné).
// Les icônes sont créées une seule fois et réutilisées : si le composant en fabriquait une nouvelle à chaque
// rendu, Leaflet reconstruirait l'élément du marqueur en plein glissement et le déplacement s'interromprait.
const ICONS = {};
const HIT_SIZE = 32;
function anchorIcon(selected, isEnd) {
  const key = selected ? "selected" : isEnd ? "end" : "normal";
  if (!ICONS[key]) {
    const size = selected ? 20 : isEnd ? 16 : 14;
    const fill = selected ? "#1b2430" : isEnd ? "#fc4c02" : "#ffffff";
    const border = selected ? "#fc4c02" : isEnd ? "#ffffff" : "#fc4c02";
    ICONS[key] = L.divIcon({
      className: "",
      iconSize: [HIT_SIZE, HIT_SIZE],
      iconAnchor: [HIT_SIZE / 2, HIT_SIZE / 2],
      // Zone tactile transparente de 32 px autour du point visible : au doigt, un rond de 14 px est introuvable.
      html:
        `<div style="width:${HIT_SIZE}px;height:${HIT_SIZE}px;display:flex;align-items:center;justify-content:center;cursor:grab">` +
        `<div style="width:${size}px;height:${size}px;box-sizing:border-box;border-radius:50%;` +
        `background:${fill};border:3px solid ${border};box-shadow:0 1px 4px rgba(0,0,0,.45)"></div></div>`,
    });
  }
  return ICONS[key];
}

// Position (lat, lon) du point d'ancrage k d'un segment.
function anchorPoint(segment, k) {
  return segment.points[segment.anchors[k]];
}

// Ligne invisible et épaisse posée sur un tronçon. Les polylignes Leaflet ne transmettent pas les événements
// tactiles : on écoute directement `pointerdown` sur l'élément SVG, ce qui couvre aussi la souris.
function GrabLine({ segment, width, onGrab }) {
  const map = useMap();
  const lineRef = useRef(null);
  const grabRef = useRef(onGrab);
  grabRef.current = onGrab;

  useEffect(() => {
    const element = lineRef.current?.getElement?.();
    if (!element) return undefined;
    function onPointerDown(event) {
      if (event.pointerType === "mouse" && event.button !== 0) return;
      L.DomEvent.stop(event); // empêche la carte de commencer à se déplacer avec ce même geste
      grabRef.current(map.mouseEventToLatLng(event));
    }
    element.addEventListener("pointerdown", onPointerDown);
    return () => element.removeEventListener("pointerdown", onPointerDown);
  }, [map, segment]);

  return (
    <Polyline
      ref={lineRef}
      positions={segment.points}
      pathOptions={{ color: "#000", weight: width, opacity: 0, lineCap: "round", className: "rtd-grab" }}
    />
  );
}

export default function RouteEditLayer({ route, pending, selectedAnchor, onSelect, onOperation }) {
  const map = useMap();
  // Doigt : zone d'accroche plus large (un trait de 22 px est difficile à viser avec le pouce).
  const grabWidth = window.matchMedia?.("(pointer: coarse)").matches ? 40 : 22;
  // Aperçu pointillé pendant un glissement : { points: [[lat, lon], ...] }.
  const [preview, setPreview] = useState(null);
  // Glissement d'insertion en cours : { segmentIndex, leg }. `moved` (ref : lu à chaud par les écouteurs
  // de la page) indique si la souris a réellement bougé, pour qu'un simple clic sur le tracé ne crée rien.
  const [insertion, setInsertion] = useState(null);
  const movedRef = useRef(false);

  // Insertion : tant que le bouton (ou le doigt) est posé, on suit le pointeur sur toute la page (même hors de la
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
    // Événements « pointer » : souris, doigt et stylet passent par les mêmes écouteurs.
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
    document.addEventListener("pointercancel", onUp);
    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointercancel", onUp);
      map.dragging.enable();
    };
  }, [insertion, map, route, onOperation]);

  const editableSegments = useMemo(
    () => route.segments.map((segment, index) => ({ segment, index })).filter(({ segment }) => segment.kind !== "link" && segment.anchors?.length >= 2),
    [route]
  );

  return (
    <>
      {/* Zones d'accroche invisibles et larges le long du tracé, pour y « attraper » la ligne (à la souris ou au doigt). */}
      {editableSegments.map(({ segment, index }) => (
        <GrabLine
          key={`grab-${route.id}-${index}`}
          segment={segment}
          width={grabWidth}
          onGrab={(latlng) => {
            if (pending) return;
            movedRef.current = false;
            setInsertion({ segmentIndex: index, leg: legAtPoint(segment, latlng) });
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
