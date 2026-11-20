// Tests des fonctions pures du frontend (outil de test intégré à Node : aucune dépendance à installer).
// Lancer avec : npm test
import assert from "node:assert/strict";
import { test } from "node:test";

import { computeGainLoss, resampleRoute, smooth } from "../src/api/elevation.js";
import { buildRouteGPX, flattenRoutePoints, haversineMeters } from "../src/utils/routeExport.js";
import { createZip } from "../src/utils/zip.js";

// Un itinéraire minimal, au format renvoyé par le backend.
const route = {
  label: "Cœur & « test »",
  total_distance_m: 1200,
  segments: [
    {
      label: "A",
      distance_m: 600,
      points: [
        [44.84, -0.57],
        [44.841, -0.57],
        [44.842, -0.569],
      ],
    },
    {
      label: "B",
      distance_m: 600,
      points: [
        [44.842, -0.569],
        [44.843, -0.568],
      ],
    },
  ],
};

test("haversineMeters : un degré de latitude fait environ 111 km", () => {
  const d = haversineMeters([44, 0], [45, 0]);
  assert.ok(Math.abs(d - 111195) < 200, `distance inattendue : ${d}`);
  assert.equal(haversineMeters([44, 0], [44, 0]), 0);
});

test("flattenRoutePoints : colle les morceaux sans doublon à la jonction", () => {
  assert.equal(flattenRoutePoints(route).length, 4);
});

test("buildRouteGPX : GPX valide, échappé, avec tous les points utiles", () => {
  const gpx = buildRouteGPX(route);
  assert.match(gpx, /^<\?xml version="1.0" encoding="UTF-8"\?>/);
  assert.match(gpx, /<gpx version="1.1" creator="RunToDraw"/);
  assert.match(gpx, /Cœur &amp; « test »/);
  assert.equal((gpx.match(/<trkpt /g) ?? []).length >= 2, true);
});

test("buildRouteGPX : une seule lettre quand on demande un morceau", () => {
  const gpx = buildRouteGPX(route, 1);
  assert.match(gpx, /lettre B/);
  assert.equal((gpx.match(/<trkpt /g) ?? []).length, 2);
});

test("buildRouteGPX : refuse un itinéraire sans assez de points", () => {
  assert.throws(() => buildRouteGPX({ segments: [{ points: [[44, 0]] }] }), /pas assez de points/);
});

test("resampleRoute : points espacés régulièrement, extrémités conservées", () => {
  const line = [
    [44.0, 0],
    [44.01, 0], // environ 1 112 m plus loin
  ];
  const out = resampleRoute(line, 100);
  assert.deepEqual(out[0], line[0]);
  assert.deepEqual(out[out.length - 1], line[1]);
  assert.ok(out.length >= 11 && out.length <= 13, `nombre de points inattendu : ${out.length}`);
  assert.ok(Math.abs(haversineMeters(out[0], out[1]) - 100) < 1);
});

test("computeGainLoss : ignore le bruit sous le seuil et compte les vraies montées", () => {
  assert.deepEqual(computeGainLoss([100, 100.5, 100.2, 100.4]), { gainM: 0, lossM: 0 });
  const { gainM, lossM } = computeGainLoss([100, 110, 120, 105, 95]);
  assert.equal(gainM, 20);
  assert.equal(lossM, 25);
  assert.deepEqual(computeGainLoss([100]), { gainM: 0, lossM: 0 });
});

test("smooth : garde la longueur et adoucit un pic isolé", () => {
  const out = smooth([0, 0, 10, 0, 0]);
  assert.equal(out.length, 5);
  assert.ok(out[2] < 10 && out[2] > 0);
});

test("createZip : archive ZIP bien formée contenant les fichiers", async () => {
  const blob = createZip([{ name: "a.gpx", content: "<gpx/>" }]);
  const bytes = new Uint8Array(await blob.arrayBuffer());
  assert.equal(String.fromCharCode(...bytes.slice(0, 2)), "PK");
  assert.ok(new TextDecoder().decode(bytes).includes("a.gpx"));
});
