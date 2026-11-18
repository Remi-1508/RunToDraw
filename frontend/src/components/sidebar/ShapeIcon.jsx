// Pictogrammes des formes prédéfinies (traits fins, couleur héritée du texte du bouton).
// Remplacent les emojis, dont le rendu change d'un système à l'autre.
const PATHS = {
  square: <rect x="5" y="5" width="14" height="14" rx="1.5" />,
  circle: <circle cx="12" cy="12" r="7.5" />,
  heart: <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.4A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" />,
  star: <path d="M12 4l2.4 5 5.4.7-4 3.8 1 5.4-4.8-2.7-4.8 2.7 1-5.4-4-3.8 5.4-.7z" />,
  triangle: <path d="M12 5l8 14H4z" />,
  diamond: <path d="M12 3l6 9-6 9-6-9z" />,
  cross: <path d="M9.5 4h5v5.5H20v5h-5.5V20h-5v-5.5H4v-5h5.5z" />,
  arrow: <path d="M12 4l7 8h-4v8H9v-8H5z" />,
  house: <path d="M5 19V11l7-6 7 6v8z" />,
  lightning: <path d="M13 3L6 13.5h5L10 21l8-11.5h-5.2z" />,
  crescent: <path d="M16.5 4.5A8 8 0 1 0 19 16 6.5 6.5 0 0 1 16.5 4.5z" />,
  drop: <path d="M12 3.5s6 6.2 6 10.5a6 6 0 0 1-12 0C6 9.7 12 3.5 12 3.5z" />,
  pencil: <path d="M4 20l1-4L16.5 4.5a2 2 0 0 1 3 3L8 19zM14.5 6.5l3 3" />,
  infinity: <path d="M12 12c-1.6-2.4-3.2-3.5-5-3.5a3.5 3.5 0 0 0 0 7c1.8 0 3.4-1.1 5-3.5zm0 0c1.6 2.4 3.2 3.5 5 3.5a3.5 3.5 0 0 0 0-7c-1.8 0-3.4 1.1-5 3.5z" />,
};

export default function ShapeIcon({ shape, size = 24 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[shape] ?? PATHS.circle}
    </svg>
  );
}
