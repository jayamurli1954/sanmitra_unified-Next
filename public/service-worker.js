/*
  MitraBooks ERP - Service Worker
  PWA caching strategy: Network-first for APIs, Cache-first for assets
*/

const CACHE_NAME = 'mitrabooks-erp-v2';
const RUNTIME_CACHE = 'mitrabooks-runtime-v2';

// Assets to cache on install (critical for offline)
const CRITICAL_ASSETS = [
  // HTML
  '/',
  '/index.html',
  '/frontend/mitrabooks-erp/index.html',

  // CSS (theme tokens + styles)
  '/frontend/shared/theme-tokens.css',
  '/frontend/shared/app-shell.css',
  '/frontend/mitrabooks-erp/index.css',
  '/frontend/mitrabooks-erp/theme-overrides.css',

  // Brand assets
  '/frontend/assets/brand/mitrabooks-logo.jpg',

  // Manifest
  '/manifest.webmanifest'
];

// API endpoints - use network-first (online preferred)
const API_ROUTES = [
  '/api/v1/',
  'https://sanmitra-unified-next-staging-sg.onrender.com'
];

// Install event - cache critical assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching critical assets');
      return cache.addAll(CRITICAL_ASSETS).catch((err) => {
        console.warn('[SW] Some assets failed to cache (may be in development):', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - routing strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-http(s) schemes — chrome-extension://, data:, blob:, etc.
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    return;
  }

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // API requests - network-first (prefer live data)
  if (isApiRequest(url)) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // Static assets - cache-first (CSS, images, JS)
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirstStrategy(request));
    return;
  }

  // Everything else - network-first with cache fallback
  event.respondWith(networkFirstStrategy(request));
});

// Strategy 1: Network-first (try network, fallback to cache)
async function networkFirstStrategy(request) {
  try {
    const response = await fetch(request);

    // Cache successful responses
    if (shouldCacheResponse(request, response)) {
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // Network failed, try cache
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Network failed, serving from cache:', request.url);
      return cached;
    }

    // No cache available
    console.warn('[SW] Network and cache failed for:', request.url);
    return new Response('Offline - resource not available', { status: 503 });
  }
}

// Strategy 2: Cache-first (use cache, fallback to network)
async function cacheFirstStrategy(request) {
  const cached = await caches.match(request);
  if (cached) {
    // Update cache in background
    fetch(request)
      .then((response) => {
        if (shouldCacheResponse(request, response)) {
          const cache = caches.open(CACHE_NAME);
          cache.then((c) => c.put(request, response));
        }
      })
      .catch(() => {
        // Network error, but we have cache so it's OK
      });

    return cached;
  }

  // Not in cache, fetch from network
  try {
    const response = await fetch(request);
    if (shouldCacheResponse(request, response)) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.warn('[SW] Cache and network failed for:', request.url);
    return new Response('Offline - resource not available', { status: 503 });
  }
}

// Helper: Check if request is API call
function isApiRequest(url) {
  return url.pathname.includes('/api/v1/') ||
         url.origin.includes('sanmitra') ||
         url.origin.includes('onrender.com');
}

// Helper: Check if request is static asset
function isStaticAsset(url) {
  return /\.(css|js|png|jpg|jpeg|svg|woff2?|ttf|eot)$/.test(url.pathname);
}

function shouldCacheResponse(request, response) {
  return request.method === 'GET' &&
         response.status === 200 &&
         response.type !== 'opaqueredirect' &&
         !request.headers.has('range');
}

// Message handler - allow clients to skip waiting (instant updates)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
