const CACHE_NAME = "huyen-hoc-shell-v2";
const SHELL_PATHS = [
  "/app",
  "/dashboard",
  "/tu-vi",
  "/offline.html",
  "/manifest.json",
  "/icon.svg",
  "/hop-tuoi",
  "/tarot",
  "/kinh-dich"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL_PATHS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(key => key.startsWith("huyen-hoc-shell-") && key !== CACHE_NAME)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.search) return;

  if (SHELL_PATHS.includes(url.pathname)) {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.put(request, copy)));
        }
        return response;
      }).catch(async () => {
        const cached = await caches.match(request);
        return cached || (request.mode === "navigate" ? caches.match("/offline.html") : Response.error());
      })
    );
  }
});
