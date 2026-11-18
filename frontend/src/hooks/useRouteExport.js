import { useCallback } from "react";
import { downloadKML, downloadRouteGPX } from "../utils/routeExport";

// Nom de fichier sûr (sans accents ni caractères spéciaux) construit à partir du libellé de l'itinéraire.
function safeFileName(label) {
  return label
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

// Export de l'itinéraire sélectionné (GPX ou KML). Pour un mot en lettres séparées,
// `segmentIndex` désigne la lettre à exporter seule en GPX.
export function useRouteExport({ selectedRoute, showToast }) {
  return useCallback(
    (exportType, segmentIndex = null) => {
      if (!selectedRoute) return;
      const baseName = safeFileName(selectedRoute.label);

      try {
        if (exportType === "gpx") {
          const segment = segmentIndex === null ? null : selectedRoute.segments?.[segmentIndex];
          const suffix = segment ? `_lettre-${String(segment.label).toLowerCase()}-${segmentIndex + 1}` : "";
          downloadRouteGPX(selectedRoute, `runtodraw_${baseName}${suffix}.gpx`, segmentIndex);
          showToast(
            segment
              ? `GPX de la lettre ${segment.label} généré.`
              : "Export GPX généré. C’est le plus simple pour Strava et beaucoup d’applis GPS.",
            "success"
          );
        } else if (exportType === "kml") {
          downloadKML(selectedRoute, `runtodraw_${baseName}.kml`);
          showToast("Export KML généré pour Google My Maps.", "success");
        }
      } catch (error) {
        showToast(error?.message ?? "Export impossible.", "error");
      }
    },
    [selectedRoute, showToast]
  );
}
