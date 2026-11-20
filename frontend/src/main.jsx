import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import ErrorBoundary from "./components/feedback/ErrorBoundary.jsx";
import "leaflet/dist/leaflet.css";
import "./index.css";

// Ceci est le point d’entrée du frontend de l’application.
//
// Il fait trois choses principales :
// 1) importe le composant principal App
// 2) importe les styles globaux, y compris ceux de Leaflet pour la carte
// 3) monte l’application React dans l’élément HTML racine
//
// React.StrictMode est activé pour aider à détecter
// d’éventuels problèmes pendant le développement.
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
// Service worker (notifications de fin de génération, installation sur l'écran d'accueil).
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
