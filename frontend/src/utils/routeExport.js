/*
============================================================
Export des itinéraires : GPX (Strava, montres GPS) et KML (Google My Maps).

Le backend envoie le tracé complet, nœud par nœud, qui suit exactement les rues.
On le simplifie légèrement (points quasi alignés supprimés, tolérance de quelques
mètres) pour garder des fichiers légers sans s'écarter des rues.

Cas des « lettres séparées » : chaque lettre est un itinéraire à part. Le GPX
s'exporte lettre par lettre (`segmentIndex`) ; le KML contient une ligne par lettre.
Pour les autres itinéraires, les morceaux (lettres et liaisons d'un mot relié) se
suivent sans interruption et forment une seule trace.

Le lien Google Maps a été retiré : Google n'accepte qu'une poignée de points de
passage et recalcule son propre itinéraire entre eux, ce qui ne respecte pas le dessin.
============================================================
*/

function downloadTextFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  URL.revokeObjectURL(url);
}

function escapeXml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function dedupeConsecutivePoints(points, epsilon = 1e-9) {
  const out = [];
  for (const p of points) {
    const last = out[out.length - 1];
    if (!last || Math.abs(last[0] - p[0]) >= epsilon || Math.abs(last[1] - p[1]) >= epsilon) {
      out.push(p);
    }
  }
  return out;
}

function segmentPoints(segment) {
  return (segment?.points ?? [])
    .filter((point) => Array.isArray(point) && point.length >= 2)
    .map((point) => [Number(point[0]), Number(point[1])]);
}

// Tous les morceaux d'un itinéraire, bout à bout (une seule trace continue).
function flattenRoutePoints(route) {
  return dedupeConsecutivePoints((route?.segments ?? []).flatMap(segmentPoints));
}

function haversineMeters(a, b) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(b[0] - a[0]);
  const dLon = toRad(b[1] - a[1]);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function pointToSegmentDistanceMeters(point, start, end) {
  const refLat = ((start[0] + end[0]) / 2) * (Math.PI / 180);
  const metersPerDegLat = 111320;
  const metersPerDegLon = 111320 * Math.cos(refLat);
  const toXY = ([lat, lon]) => [lon * metersPerDegLon, lat * metersPerDegLat];

  const [px, py] = toXY(point);
  const [sx, sy] = toXY(start);
  const [ex, ey] = toXY(end);
  const dx = ex - sx;
  const dy = ey - sy;

  if (Math.abs(dx) < 1e-9 && Math.abs(dy) < 1e-9) {
    return Math.hypot(px - sx, py - sy);
  }

  const t = Math.max(0, Math.min(1, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - (sx + t * dx), py - (sy + t * dy));
}

// Douglas-Peucker : retire les points qui s'écartent de moins de `toleranceMeters` de la ligne.
function douglasPeucker(points, toleranceMeters) {
  if (points.length <= 2) return points;

  let maxDist = 0;
  let index = -1;
  for (let i = 1; i < points.length - 1; i++) {
    const dist = pointToSegmentDistanceMeters(points[i], points[0], points[points.length - 1]);
    if (dist > maxDist) {
      maxDist = dist;
      index = i;
    }
  }

  if (maxDist <= toleranceMeters || index === -1) {
    return [points[0], points[points.length - 1]];
  }

  const left = douglasPeucker(points.slice(0, index + 1), toleranceMeters);
  const right = douglasPeucker(points.slice(index), toleranceMeters);
  return [...left.slice(0, -1), ...right];
}

// Ignore les points trop rapprochés (moins de `minStepMeters` du dernier gardé).
function simplifyByMinStep(points, minStepMeters) {
  if (points.length <= 2) return points;
  const out = [points[0]];
  for (let i = 1; i < points.length - 1; i++) {
    if (haversineMeters(out[out.length - 1], points[i]) >= minStepMeters) {
      out.push(points[i]);
    }
  }
  out.push(points[points.length - 1]);
  return out;
}

function simplifyRoutePoints(points, { toleranceMeters, minStepMeters }) {
  if (points.length <= 2) return points;
  const simplified = dedupeConsecutivePoints(
    douglasPeucker(simplifyByMinStep(dedupeConsecutivePoints(points), minStepMeters), toleranceMeters)
  );
  return simplified.length >= 2 ? simplified : [points[0], points[points.length - 1]];
}

function routeDescription(route) {
  const total = route?.total_distance_m ?? 0;
  const gap = route?.length_gap_m ?? 0;
  return `Distance totale : ${(total / 1000).toFixed(2)} km | Écart à la cible : ${gap.toFixed(0)} m`;
}

/**
 * Télécharge un fichier GPX.
 * @param route itinéraire renvoyé par le backend
 * @param filename nom du fichier
 * @param segmentIndex si fourni, n'exporte que ce morceau (une lettre d'un mot en lettres séparées)
 */
export function downloadRouteGPX(route, filename = "runtodraw_route.gpx", segmentIndex = null) {
  const segment = segmentIndex === null ? null : route?.segments?.[segmentIndex];
  const rawPoints = segment ? dedupeConsecutivePoints(segmentPoints(segment)) : flattenRoutePoints(route);
  const points = simplifyRoutePoints(rawPoints, { toleranceMeters: 8, minStepMeters: 6 });

  if (points.length < 2) {
    throw new Error("Impossible de générer un GPX : pas assez de points.");
  }

  const title = segment ? `${route?.label ?? "RunToDraw"} – lettre ${segment.label}` : route?.label ?? "RunToDraw";
  const name = escapeXml(title);
  const desc = escapeXml(
    segment ? `Distance : ${((segment.distance_m ?? 0) / 1000).toFixed(2)} km` : routeDescription(route)
  );
  const trkpts = points.map(([lat, lon]) => `      <trkpt lat="${lat}" lon="${lon}"></trkpt>`).join("\n");

  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="RunToDraw" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>${name}</name>
    <desc>${desc}</desc>
    <time>${new Date().toISOString()}</time>
  </metadata>
  <trk>
    <name>${name}</name>
    <desc>${desc}</desc>
    <trkseg>
${trkpts}
    </trkseg>
  </trk>
</gpx>`;

  downloadTextFile(gpx, filename, "application/gpx+xml");
}

/**
 * Télécharge un fichier KML (Google My Maps). Pour un mot en lettres séparées,
 * chaque lettre devient une ligne distincte ; sinon l'itinéraire est une seule ligne.
 */
export function downloadKML(route, filename = "runtodraw_route.kml") {
  const parts = route?.separate
    ? (route.segments ?? []).map((segment) => ({
        name: `${route.label} – lettre ${segment.label}`,
        points: dedupeConsecutivePoints(segmentPoints(segment)),
      }))
    : [{ name: route?.label ?? "RunToDraw", points: flattenRoutePoints(route) }];

  const placemarks = parts
    .map((part) => ({ ...part, points: simplifyRoutePoints(part.points, { toleranceMeters: 12, minStepMeters: 8 }) }))
    .filter((part) => part.points.length >= 2)
    .map(
      (part) => `    <Placemark>
      <name>${escapeXml(part.name)}</name>
      <description>${escapeXml(routeDescription(route))}</description>
      <Style>
        <LineStyle>
          <color>ff3c78ff</color>
          <width>4</width>
        </LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>${part.points.map(([lat, lon]) => `${lon},${lat},0`).join(" ")}</coordinates>
      </LineString>
    </Placemark>`
    );

  if (!placemarks.length) {
    throw new Error("Impossible de générer un KML : pas assez de points.");
  }

  const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>${escapeXml(route?.label ?? "RunToDraw")}</name>
${placemarks.join("\n")}
  </Document>
</kml>`;

  downloadTextFile(kml, filename, "application/vnd.google-earth.kml+xml");
}
