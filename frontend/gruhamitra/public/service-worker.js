const CACHE_NAME = 'gruhamitra-v6';
const ASSETS_TO_CACHE = [
    '/gruhamitra/',
    '/gruhamitra/index.html',
    '/gruhamitra/manifest.json',
    '/gruhamitra/icons/icon-192.png',
    '/gruhamitra/icons/icon-512.png',
    '/gruhamitra/icons/icon-maskable-192.png',
    '/gruhamitra/icons/icon-maskable-512.png',
    '/gruhamitra/icons/apple-touch-icon.png'
];

// Install Event - Skip waiting to activate immediately
self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Static assets cached');
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// Activate Event - Clear old caches and take control immediately
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch Event - Network first for HTML/JS, cache for static assets only
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip API calls - always live
    if (url.pathname.startsWith('/api/') || url.hostname !== self.location.hostname) {
        return;
    }

    // Network first for HTML and JS files (always get fresh)
    if (event.request.destination === 'document' ||
        url.pathname.endsWith('.html') ||
        url.pathname.endsWith('.js') ||
        url.pathname === '/' ||
        url.pathname.startsWith('/gruhamitra')) {
        event.respondWith(
            fetch(event.request).catch(() =>
                caches.match(event.request).then((response) => response || caches.match('/gruhamitra/index.html'))
            )
        );
        return;
    }

    // Cache first for static assets (images, icons)
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});

// Push Event Listener for Visitor Approvals and other alerts
self.addEventListener('push', (event) => {
    if (!event.data) return;
    try {
        const payload = event.data.json();
        const title = payload.title || 'GruhaMitra Alert';
        const options = {
            body: payload.body || 'New visitor request received',
            icon: '/gruhamitra/icons/icon-192.png',
            badge: '/gruhamitra/icons/icon-192.png',
            data: payload.data || {},
            actions: [
                { action: 'approve', title: 'Approve' },
                { action: 'reject', title: 'Reject' }
            ]
        };
        event.waitUntil(self.registration.showNotification(title, options));
    } catch (err) {
        console.error('Error displaying push notification:', err);
    }
});

// Notification Action & Click Event Listener
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const visitorId = event.notification.data?.visitor_id;
    if (!visitorId) return;

    let action = 'view';
    if (event.action === 'approve') {
        action = 'approve';
    } else if (event.action === 'reject') {
        action = 'reject';
    }

    const urlToOpen = new URL(`/gruhamitra/visitors?action=${action}&id=${visitorId}`, self.location.origin).href;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            // If the app is already open, navigate to visitors screen with query parameters
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url.includes('/gruhamitra') && 'focus' in client) {
                    return client.navigate(urlToOpen).then((focusedClient) => {
                        if (focusedClient) focusedClient.focus();
                    });
                }
            }
            // Otherwise, open a new window
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});
