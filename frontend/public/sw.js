/**
 * Setu Offline PWA Service Worker (FIX 3e).
 * Precaches application shell, manifest, icons, and built hashed assets.
 * Caches API pack requests and falls back cleanly when offline.
 */

const CACHE_NAME = 'setu-cache-v5';
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/icon-192.png",
  "/icon-512.png",
  "/assets/index-DkLQBgE_.js",
  "/assets/index-yun6A7Ga.css"
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Non-GET requests pass through
  if (event.request.method !== 'GET' || !url.protocol.startsWith('http')) {
    return;
  }

  // Navigation requests: Serve cached HTML immediately or fallback on network error
  if (event.request.mode === 'navigate') {
    event.respondWith(
      caches.match('/index.html').then((cached) => {
        if (cached) return cached;
        return caches.match('/').then((r) => {
          if (r) return r;
          return fetch(event.request);
        });
      }).catch(() => {
        return caches.match('/index.html').then((r) => r || caches.match('/'));
      })
    );
    return;
  }

  // Assets and static files: Pathname match first, then request match, then network
  event.respondWith(
    caches.match(url.pathname).then((cachedByPath) => {
      if (cachedByPath) {
        return cachedByPath;
      }
      return caches.match(event.request).then((cachedReq) => {
        if (cachedReq) {
          return cachedReq;
        }
        return fetch(event.request).then((networkResponse) => {
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            (url.pathname.endsWith('.js') ||
              url.pathname.endsWith('.css') ||
              url.pathname.endsWith('.png') ||
              url.pathname.endsWith('.svg') ||
              url.pathname.endsWith('.json') ||
              url.pathname.includes('/assets/'))
          ) {
            const toCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, toCache);
            });
          }
          return networkResponse;
        });
      });
    }).catch(() => {
      if (event.request.mode === 'navigate') {
        return caches.match('/index.html').then((r) => r || caches.match('/'));
      }
    })
  );
});
