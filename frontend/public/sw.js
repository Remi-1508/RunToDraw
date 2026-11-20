// Service worker de RunToDraw : il sert à afficher les notifications (Android exige un service worker) et rend
// l'application installable. Il ne met rien en cache : les pages et l'API passent toujours par le réseau.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});

// Toucher la notification ramène sur l'onglet de l'application (ou en ouvre un).
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      for (const client of windows) if ("focus" in client) return client.focus();
      return self.clients.openWindow("/");
    })
  );
});
