// URL du backend. Vite ne charge que les fichiers .env* (voir .env à la
// racine du frontend) : VITE_ROUTE_API_URL doit y être défini pour changer
// cette valeur sans toucher au code.
export const API_BASE = import.meta.env.VITE_ROUTE_API_URL || "http://localhost:8000";
