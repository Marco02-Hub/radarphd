/* Service worker: app in cache (offline), dati sempre freschi dalla rete (cache solo come riserva). */
const VERSION = "radar-v1";
const APP = [
  "./", "index.html", "app.css", "app.js", "manifest.webmanifest",
  "icons/icon-192.png", "icons/icon-512.png", "icons/icon-512-maskable.png", "icons/apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(APP)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const networkFirst = async (req) => {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req, { cache: "no-store" });
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    throw err;
  }
};

const cacheFirst = async (req) => {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === "opaque") cache.put(req, res.clone());
  return res;
};

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin && url.pathname.includes("/data/")) {
    e.respondWith(networkFirst(req));            // dati: sempre dalla rete
  } else if (url.origin === location.origin && (req.mode === "navigate" || /\.(html|js|css|webmanifest)$/.test(url.pathname))) {
    e.respondWith(networkFirst(req));            // shell: aggiornata se online, offline dalla cache
  } else if (url.origin === location.origin || /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
    e.respondWith(cacheFirst(req));              // immagini, icone, font
  }
});
