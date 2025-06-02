const CACHE_NAME = "eduPresence-cache-v1";
const STATIC_FILES = [
  "/",
  // "/dashboard",
  // "/manage-classes",
  "/static/css/dashboard.css",
  "/static/css/index.css",
  // "/static/js/service-worker.js",
  "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css",
  "https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"
];

// Install event: Cache static assets
self.addEventListener("install", (event) => {
  console.log("Service Worker: Installing...");
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Caching static files...");
      return cache.addAll(STATIC_FILES);
    }).catch(err => console.error("Cache error:", err))
  );
});

// Activate event: Clean up old caches
self.addEventListener("activate", (event) => {
  console.log("Service Worker: Activating...");
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  return self.clients.claim();
});

// Fetch event: Serve cached content when offline
self.addEventListener("fetch", (event) => {
  console.log("Fetching:", event.request.url);
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request);
    }).catch(err => console.error("Fetch error:", err))
  );
});
