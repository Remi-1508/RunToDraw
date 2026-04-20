import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "leaflet/dist/leaflet.css";
import "./index.css";

/*
============================================================
EN:
This is the frontend entry point of the application.

It does three main things:
1) imports the main App component
2) imports the global styles, including Leaflet map styles
3) mounts the React application into the HTML root element

React.StrictMode is enabled to help detect potential issues
during development.

FR:
Ceci est le point d’entrée du frontend de l’application.

Il fait trois choses principales :
1) importe le composant principal App
2) importe les styles globaux, y compris ceux de Leaflet pour la carte
3) monte l’application React dans l’élément HTML racine

React.StrictMode est activé pour aider à détecter
d’éventuels problèmes pendant le développement.
============================================================
*/
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);