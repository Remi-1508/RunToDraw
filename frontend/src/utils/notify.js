/*
============================================================
Notification de fin de génération.

La génération peut durer une à deux minutes : on laisse la personne quitter l'onglet (ou verrouiller son
téléphone) et on la prévient quand c'est prêt, de trois façons qui s'additionnent :
- une notification système, si elle l'a autorisée (via le service worker, seul moyen qui marche sur Android) ;
- une vibration courte sur téléphone ;
- le titre de l'onglet, qui annonce « Parcours prêt » jusqu'au retour sur la page.

Limite d'iOS : Safari n'affiche des notifications que pour une application ajoutée à l'écran d'accueil
(iOS 16.4 ou plus). Dans un simple onglet Safari, seul le titre de l'onglet change.
============================================================
*/
import { readStorage, writeStorage } from "./storage";

const ASKED_KEY = "runtodraw.notifications.asked";
const ORIGINAL_TITLE = typeof document !== "undefined" ? document.title : "RunToDraw";

export function notificationsSupported() {
  return typeof Notification !== "undefined" && "serviceWorker" in navigator;
}

// À appeler lors d'un geste de la personne (clic sur « Générer ») : les navigateurs refusent sinon d'afficher
// la demande d'autorisation. On ne la propose qu'une fois ; refusée, elle n'est plus jamais reposée.
export function requestNotificationPermissionOnce() {
  if (!notificationsSupported() || Notification.permission !== "default") return;
  if (readStorage(ASKED_KEY)) return;
  writeStorage(ASKED_KEY, "1");
  try {
    Notification.requestPermission();
  } catch {
    // navigateur ancien : on s'en passe
  }
}

let restoreTitleHandler = null;

// Annonce que le parcours est prêt (seulement si la personne n'est plus sur la page).
export async function notifyRouteReady({ title, body }) {
  if (typeof document === "undefined" || !document.hidden) return;

  try {
    navigator.vibrate?.([120, 60, 120]);
  } catch {
    // vibration indisponible
  }

  document.title = `✅ ${title}`;
  if (!restoreTitleHandler) {
    restoreTitleHandler = () => {
      if (document.hidden) return;
      document.title = ORIGINAL_TITLE;
      document.removeEventListener("visibilitychange", restoreTitleHandler);
      restoreTitleHandler = null;
    };
    document.addEventListener("visibilitychange", restoreTitleHandler);
  }

  if (!notificationsSupported() || Notification.permission !== "granted") return;
  try {
    const registration = await navigator.serviceWorker.ready;
    await registration.showNotification(title, { body, icon: "/favicon.png", tag: "runtodraw-ready" });
  } catch {
    // service worker indisponible : le titre de l'onglet suffit
  }
}
