/**
 * Compás service worker.
 *
 * Strategy:
 *  - The SvelteKit app shell (HTML, JS, CSS) is precached on install.
 *  - At runtime: cache-first for the app shell, network-first for /api/*.
 *  - Audio + stem URLs use a stale-while-revalidate approach (cache last good response,
 *    fall back to network, update cache on success).
 *  - On install: skip waiting. On activate: clean old caches.
 *
 * Bump CACHE_NAME on each release to invalidate stale app shell.
 */
const CACHE_NAME = 'compas-v1';
const APP_SHELL = ['/', '/manifest.webmanifest', '/icon.svg'];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches.keys().then((keys) =>
			Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
		).then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	const url = new URL(event.request.url);

	// Only handle same-origin requests
	if (url.origin !== self.location.origin) return;

	// Network-first for API
	if (url.pathname.startsWith('/api/')) {
		event.respondWith(
			fetch(event.request)
				.then((res) => {
					// cache successful GET responses
					if (event.request.method === 'GET' && res.ok) {
						const clone = res.clone();
						caches.open(CACHE_NAME).then((c) => c.put(event.request, clone));
					}
					return res;
				})
				.catch(() => caches.match(event.request).then((r) => r || new Response('Offline', { status: 503 })))
		);
		return;
	}

	// Stale-while-revalidate for audio + stems
	if (url.pathname.includes('/audio') || url.pathname.includes('/stems/')) {
		event.respondWith(
			caches.open(CACHE_NAME).then((cache) =>
				cache.match(event.request).then((cached) => {
					const fetched = fetch(event.request)
						.then((res) => {
							if (res.ok) cache.put(event.request, res.clone());
							return res;
						})
						.catch(() => cached || new Response('Offline', { status: 503 }));
					return cached || fetched;
				})
			)
		);
		return;
	}

	// Cache-first for app shell
	event.respondWith(
		caches.match(event.request).then((cached) => {
			if (cached) return cached;
			return fetch(event.request)
				.then((res) => {
					if (res.ok && event.request.method === 'GET') {
						const clone = res.clone();
						caches.open(CACHE_NAME).then((c) => c.put(event.request, clone));
					}
					return res;
				})
				.catch(() => caches.match('/'));
		})
	);
});
