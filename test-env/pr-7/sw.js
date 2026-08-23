// Service Worker for offline play (see REQUIREMENTS.md item 1).
//
// Must be a real file served over http(s) — browsers refuse to register a
// Service Worker from a data: or blob: URL, which is why an earlier inline
// attempt at this never actually worked (it silently failed to register).
//
// Strategy: network-first, falling back to cache when offline. The app is
// fully static and self-contained (no separate CSS/JS/image requests, no
// external APIs), so there's nothing dynamic to worry about breaking —
// every successful online load simply refreshes the cached copy, and an
// offline load serves whatever was last cached. No manual cache-busting or
// version bump is needed for content changes to index.html; only bump
// CACHE_NAME below if the caching strategy itself changes and old cached
// entries should be discarded.
const CACHE_NAME = 'sudoku-cache-v1';
const APP_SHELL = ['./', './index.html'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(APP_SHELL))
            .catch(() => {}) // don't block install if the initial precache fails; fetch handler still caches on first successful load
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.map((key) => (key !== CACHE_NAME ? caches.delete(key) : undefined)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200) {
                    const copy = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                }
                return networkResponse;
            })
            .catch(() =>
                caches.match(event.request, { ignoreSearch: true }).then((cached) => {
                    if (cached) return cached;
                    return caches.match('./index.html');
                })
            )
    );
});
