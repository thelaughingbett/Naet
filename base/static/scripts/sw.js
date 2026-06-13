const CACHE = "portal-v1";

const PRE_CACHE = [
  "/",
  "/academics/curriculum/",
  "/financials/fees/",
  "/timetable/schedule/",
  "/admissions/reporting/",
  "/static/base/styles/portal.css",
  "/static/base/styles/resets.css",
  "/static/base/styles/index/index.css",
  "/static/base/styles/academics/curriculum/index.css",
  // "/static/base/scripts/main.js",
  // "/static/base/scripts/db.js",
];

// install — cache critical pages on first load
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRE_CACHE)));
  self.skipWaiting();
});

// activate — clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)),
        ),
      ),
  );
  self.clients.claim();
});

// fetch — network first, fall back to cache
self.addEventListener("fetch", (event) => {
  // only intercept GET requests for same-origin HTML pages
  if (
    event.request.method !== "GET" ||
    !event.request.url.startsWith(self.location.origin)
  )
    return;

  const isHTML = event.request.headers.get("accept")?.includes("text/html");
  const isAsset = event.request.url.includes("/static/");

  if (isAsset) {
    // assets — cache first
    event.respondWith(
      caches.match(event.request).then(
        (cached) =>
          cached ||
          fetch(event.request).then((response) => {
            const clone = response.clone();
            caches.open(CACHE).then((c) => c.put(event.request, clone));
            return response;
          }),
      ),
    );
    return;
  }

  if (isHTML) {
    // HTML pages — network first, cache as fallback
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // cache the fresh response
          const clone = response.clone();
          caches.open(CACHE).then((c) => c.put(event.request, clone));
          return response;
        })
        .catch(() => {
          // offline — serve cached version
          return caches.match(event.request) || caches.match("/"); // ultimate fallback
        }),
    );
  }
});
