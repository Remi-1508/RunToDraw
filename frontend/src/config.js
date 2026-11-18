// Configuration et constantes de l'application, regroupées en un seul endroit.

// Adresse du backend FastAPI (définie par VITE_ROUTE_API_URL, voir .env.example).
export const API_BASE = (import.meta.env.VITE_ROUTE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

// Centre de la carte avant que l'utilisateur choisisse un point de départ (Bordeaux).
export const DEFAULT_CENTER = [44.8378, -0.5792];

// Distance : valeur initiale, minimum, maximum par défaut (le serveur communique son propre maximum)
// et seuil à partir duquel on prévient que le téléchargement du réseau routier sera long.
export const DEFAULT_DISTANCE_KM = 15;
export const MIN_DISTANCE_KM = 1;
export const FALLBACK_MAX_DISTANCE_KM = 50;
export const LONG_DISTANCE_CONFIRM_KM = 30;

// Dessin choisi au chargement : un cœur (le texte par défaut sert quand on passe en mode texte).
export const INITIAL_DRAWING = { mode: "shape", shape: "heart", text: "P2I" };
export const MAX_TEXT_LENGTH = 10;

// Formes prédéfinies : identifiant (compris par le backend) et libellé (pictogrammes : ShapeIcon).
export const SHAPES = [
  { id: "square", label: "Carré" },
  { id: "circle", label: "Rond" },
  { id: "heart", label: "Cœur" },
  { id: "star", label: "Étoile" },
  { id: "infinity", label: "Infini" },
];

// Largeur de la barre latérale, en pixels.
export const SIDEBAR_WIDTH = { min: 340, max: 720, default: 430 };

// Clés de stockage local du navigateur.
export const STORAGE_KEYS = {
  theme: "runtodraw-theme",
  mapBackground: "runtodraw-map-background",
  sidebarWidth: "runtodraw-sidebar-width",
};
