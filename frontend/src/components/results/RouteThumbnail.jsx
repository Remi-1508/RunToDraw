import { useMemo } from "react";

// Miniature d'un itinéraire : le tracé seul, sur fond neutre, pour reconnaître la forme d'un coup d'œil.
// Les coordonnées (lat, lon) sont projetées à plat, avec la longitude réduite par cos(latitude)
// pour ne pas déformer la forme.
const SIZE = 100;
const PAD = 8;

function buildPaths(segments) {
  const all = segments.flatMap((segment) => segment.points || []);
  if (all.length < 2) return null;

  const lat0 = all.reduce((sum, p) => sum + p[0], 0) / all.length;
  const kx = Math.cos((lat0 * Math.PI) / 180);
  const xs = all.map((p) => p[1] * kx);
  const ys = all.map((p) => -p[0]);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const span = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY) || 1;
  const scale = (SIZE - 2 * PAD) / span;
  const offsetX = (SIZE - (Math.max(...xs) - minX) * scale) / 2;
  const offsetY = (SIZE - (Math.max(...ys) - minY) * scale) / 2;

  return segments.map((segment) => ({
    isLink: segment.kind === "link",
    d: (segment.points || [])
      .map(([lat, lon], i) => {
        const x = offsetX + (lon * kx - minX) * scale;
        const y = offsetY + (-lat - minY) * scale;
        return `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" "),
  }));
}

export default function RouteThumbnail({ segments, size = 76 }) {
  const paths = useMemo(() => buildPaths(segments ?? []), [segments]);

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      width={size}
      height={size}
      style={{ flexShrink: 0, borderRadius: "var(--radius-sm)", background: "var(--map-neutral)" }}
      aria-hidden="true"
    >
      {paths?.map((path, index) => (
        <g key={index} fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path d={path.d} stroke="var(--route-casing)" strokeWidth={path.isLink ? 0 : 6} />
          <path
            d={path.d}
            stroke={path.isLink ? "var(--text-soft)" : "var(--accent)"}
            strokeWidth={path.isLink ? 1.5 : 3.2}
            strokeDasharray={path.isLink ? "3 3" : undefined}
          />
        </g>
      ))}
    </svg>
  );
}
