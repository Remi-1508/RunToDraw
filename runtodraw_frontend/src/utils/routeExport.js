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

function flattenRoutePoints(route) {
  const raw = [];

  for (const segment of route?.segments ?? []) {
    for (const point of segment?.points ?? []) {
      if (Array.isArray(point) && point.length >= 2) {
        raw.push([Number(point[0]), Number(point[1])]);
      }
    }
  }

  return dedupeConsecutivePoints(raw);
}

function dedupeConsecutivePoints(points, epsilon = 1e-9) {
  const out = [];

  for (const p of points) {
    if (!out.length) {
      out.push(p);
      continue;
    }

    const last = out[out.length - 1];
    const sameLat = Math.abs(last[0] - p[0]) < epsilon;
    const sameLon = Math.abs(last[1] - p[1]) < epsilon;

    if (!sameLat || !sameLon) {
      out.push(p);
    }
  }

  return out;
}

function haversineMeters(a, b) {
  const [lat1, lon1] = a;
  const [lat2, lon2] = b;

  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const aa =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;

  return 2 * R * Math.asin(Math.sqrt(aa));
}

function totalLengthMeters(points) {
  let total = 0;
  for (let i = 0; i < points.length - 1; i++) {
    total += haversineMeters(points[i], points[i + 1]);
  }
  return total;
}

function pointToSegmentDistanceMeters(point, start, end) {
  const refLat = ((start[0] + end[0]) / 2) * (Math.PI / 180);
  const metersPerDegLat = 111320;
  const metersPerDegLon = 111320 * Math.cos(refLat);

  const toXY = ([lat, lon]) => [
    lon * metersPerDegLon,
    lat * metersPerDegLat,
  ];

  const [px, py] = toXY(point);
  const [sx, sy] = toXY(start);
  const [ex, ey] = toXY(end);

  const dx = ex - sx;
  const dy = ey - sy;

  if (Math.abs(dx) < 1e-9 && Math.abs(dy) < 1e-9) {
    return Math.hypot(px - sx, py - sy);
  }

  const t = Math.max(
    0,
    Math.min(1, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy))
  );

  const projX = sx + t * dx;
  const projY = sy + t * dy;

  return Math.hypot(px - projX, py - projY);
}

function douglasPeucker(points, toleranceMeters) {
  if (!points || points.length <= 2) return points ?? [];

  let maxDist = 0;
  let index = -1;

  for (let i = 1; i < points.length - 1; i++) {
    const dist = pointToSegmentDistanceMeters(
      points[i],
      points[0],
      points[points.length - 1]
    );

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

function simplifyByMinStep(points, minStepMeters = 12) {
  if (points.length <= 2) return points;

  const out = [points[0]];
  let lastKept = points[0];

  for (let i = 1; i < points.length - 1; i++) {
    const d = haversineMeters(lastKept, points[i]);
    if (d >= minStepMeters) {
      out.push(points[i]);
      lastKept = points[i];
    }
  }

  out.push(points[points.length - 1]);
  return out;
}

function bearingDegrees(a, b) {
  const [lat1, lon1] = a.map((v) => (v * Math.PI) / 180);
  const [lat2, lon2] = b.map((v) => (v * Math.PI) / 180);

  const y = Math.sin(lon2 - lon1) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1);

  const brng = (Math.atan2(y, x) * 180) / Math.PI;
  return (brng + 360) % 360;
}

function angleDiffDegrees(a, b) {
  const diff = Math.abs(a - b) % 360;
  return diff > 180 ? 360 - diff : diff;
}

function simplifyByTurns(points, minTurnDeg = 28, minSpacingMeters = 35) {
  if (points.length <= 2) return points;

  const out = [points[0]];
  let lastKeptIndex = 0;

  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const cur = points[i];
    const next = points[i + 1];

    const b1 = bearingDegrees(prev, cur);
    const b2 = bearingDegrees(cur, next);
    const turn = angleDiffDegrees(b1, b2);

    const distFromLastKept = haversineMeters(points[lastKeptIndex], cur);

    if (turn >= minTurnDeg && distFromLastKept >= minSpacingMeters) {
      out.push(cur);
      lastKeptIndex = i;
    }
  }

  out.push(points[points.length - 1]);
  return dedupeConsecutivePoints(out);
}

function simplifyRoutePoints(points, options = {}) {
  const {
    toleranceMeters = 18,
    minStepMeters = 10,
    preserveTurns = true,
  } = options;

  if (!points || points.length <= 2) return points ?? [];

  let simplified = dedupeConsecutivePoints(points);
  simplified = simplifyByMinStep(simplified, minStepMeters);

  if (simplified.length > 2) {
    simplified = douglasPeucker(simplified, toleranceMeters);
  }

  if (preserveTurns && simplified.length > 2) {
    simplified = simplifyByTurns(simplified, 28, 35);
  }

  simplified = dedupeConsecutivePoints(simplified);

  if (simplified.length < 2 && points.length >= 2) {
    return [points[0], points[points.length - 1]];
  }

  return simplified;
}

function samplePointsByDistance(points, targetCount) {
  if (points.length <= targetCount) return points;

  const total = totalLengthMeters(points);
  if (total <= 1) return [points[0], points[points.length - 1]];

  const out = [points[0]];
  const step = total / (targetCount - 1);

  let accumulated = 0;
  let nextTarget = step;

  for (let i = 1; i < points.length; i++) {
    const seg = haversineMeters(points[i - 1], points[i]);
    accumulated += seg;

    if (accumulated >= nextTarget) {
      out.push(points[i]);
      nextTarget += step;
    }
  }

  const last = points[points.length - 1];
  const lastOut = out[out.length - 1];
  if (lastOut[0] !== last[0] || lastOut[1] !== last[1]) {
    out.push(last);
  }

  return dedupeConsecutivePoints(out);
}

function buildGoogleMapsWaypointSet(points, maxWaypoints = 8) {
  if (points.length <= 2) {
    return {
      origin: points[0] ?? null,
      destination: points[points.length - 1] ?? null,
      waypoints: [],
    };
  }

  let simplified = simplifyRoutePoints(points, {
    toleranceMeters: 30,
    minStepMeters: 20,
    preserveTurns: true,
  });

  if (simplified.length > maxWaypoints + 2) {
    simplified = samplePointsByDistance(simplified, maxWaypoints + 2);
  }

  const origin = simplified[0];
  const destination = simplified[simplified.length - 1];
  const waypoints = simplified.slice(1, -1);

  return { origin, destination, waypoints };
}

function latLonToString([lat, lon]) {
  return `${lat},${lon}`;
}

function routeLabel(route) {
  return route?.label || "RunToDraw route";
}

function routeDescription(route) {
  const total = route?.total_distance_m ?? 0;
  const gap = route?.length_gap_m ?? 0;
  return `Distance totale: ${(total / 1000).toFixed(2)} km | Ecart cible: ${gap.toFixed(0)} m`;
}

export function downloadRouteGPX(route, filename = "runtodraw_route.gpx") {
  const rawPoints = flattenRoutePoints(route);
  const points = simplifyRoutePoints(rawPoints, {
    toleranceMeters: 8,
    minStepMeters: 6,
    preserveTurns: false,
  });

  if (points.length < 2) {
    throw new Error("Impossible de générer un GPX : pas assez de points.");
  }

  const name = escapeXml(routeLabel(route));
  const desc = escapeXml(routeDescription(route));
  const nowIso = new Date().toISOString();

  const trkpts = points
    .map(
      ([lat, lon]) =>
        `      <trkpt lat="${lat}" lon="${lon}"></trkpt>`
    )
    .join("\n");

  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="RunToDraw" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>${name}</name>
    <desc>${desc}</desc>
    <time>${nowIso}</time>
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

export function downloadKML(route, filename = "runtodraw_route.kml") {
  const rawPoints = flattenRoutePoints(route);
  const points = simplifyRoutePoints(rawPoints, {
    toleranceMeters: 12,
    minStepMeters: 8,
    preserveTurns: false,
  });

  if (points.length < 2) {
    throw new Error("Impossible de générer un KML : pas assez de points.");
  }

  const name = escapeXml(routeLabel(route));
  const desc = escapeXml(routeDescription(route));

  const coordinates = points
    .map(([lat, lon]) => `${lon},${lat},0`)
    .join(" ");

  const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>${name}</name>
    <Placemark>
      <name>${name}</name>
      <description>${desc}</description>
      <Style>
        <LineStyle>
          <color>ff3c78ff</color>
          <width>4</width>
        </LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>${coordinates}</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>`;

  downloadTextFile(
    kml,
    filename,
    "application/vnd.google-earth.kml+xml"
  );
}

export function downloadGoogleMapsShortcut(route) {
  const rawPoints = flattenRoutePoints(route);

  if (rawPoints.length < 2) {
    throw new Error("Impossible d’ouvrir Google Maps : pas assez de points.");
  }

  const { origin, destination, waypoints } = buildGoogleMapsWaypointSet(rawPoints, 8);

  if (!origin || !destination) {
    throw new Error("Impossible d’ouvrir Google Maps : origine ou destination manquante.");
  }

  const params = new URLSearchParams({
    api: "1",
    origin: latLonToString(origin),
    destination: latLonToString(destination),
    travelmode: "walking",
  });

  if (waypoints.length > 0) {
    params.set(
      "waypoints",
      waypoints.map(latLonToString).join("|")
    );
  }

  const url = `https://www.google.com/maps/dir/?${params.toString()}`;
  window.open(url, "_blank", "noopener,noreferrer");
}

/**
 * Optional helper if you want to inspect the simplified points in the console.
 */
export function debugSimplifiedRoute(route) {
  const rawPoints = flattenRoutePoints(route);
  const gpxPoints = simplifyRoutePoints(rawPoints, {
    toleranceMeters: 8,
    minStepMeters: 6,
    preserveTurns: false,
  });
  const mapsPoints = buildGoogleMapsWaypointSet(rawPoints, 8);

  return {
    rawCount: rawPoints.length,
    gpxCount: gpxPoints.length,
    googleMaps: mapsPoints,
  };
}