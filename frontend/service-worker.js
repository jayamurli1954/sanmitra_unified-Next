const CACHE_NAME = "sanmitra-frontends-v10";
const APP_SHELL = [
  "./",
  "./index.html",
  "./shared/app-shell.css",
  "./shared/api-client.js",
  "./shared/pwa-shell.js",
  "./mitrabooks-erp/",
  "./mitrabooks-erp/index.html",
  "./mitrabooks-erp/app.js",
  "./legalmitra/",
  "./legalmitra/index.html",
  "./legalmitra/app.js",
  "./investmitra/",
  "./investmitra/index.html",
  "./investmitra/app.js",
  "./icons/sanmitra.svg",
  "./assets/brand/sanmitra-logo.png",
  "./assets/brand/mitrabooks-logo.jpg",
  "./assets/brand/mitrabooks-logo.mp4",
  "./assets/brand/legalmitra-logo.png",
  "./assets/brand/legalmitra-logo.mp4",
  "./assets/brand/investmitra-logo.png",
  "./assets/brand/mandirmitra-logo.jpeg",
  "./assets/brand/mandirmitra-logo.mp4",
  "./assets/brand/gruhamitra-logo.png",
  "./assets/brand/gruhamitra-logo.mp4",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    return;
  }

  if (url.pathname.includes("/api/") || url.pathname.endsWith("/health")) {
    event.respondWith(fetch(request));
    return;
  }

  if (request.mode === "navigate" || ["document", "script", "style", "worker"].includes(request.destination)) {
    event.respondWith(
      fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      }).catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      return response;
    }))
  );
});
