import { useCallback, useState } from "react";

// Position actuelle de l'utilisateur via la géolocalisation du navigateur.
// `onPosition([lat, lng])` est appelée en cas de succès, `onError(message)` sinon.
export function useGeolocation({ onPosition, onError }) {
  const [locating, setLocating] = useState(false);

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      onError("La géolocalisation n’est pas supportée par ton navigateur.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        onPosition([position.coords.latitude, position.coords.longitude]);
      },
      () => {
        setLocating(false);
        onError("Impossible de récupérer la position actuelle.");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }, [onPosition, onError]);

  return { locating, locate };
}
