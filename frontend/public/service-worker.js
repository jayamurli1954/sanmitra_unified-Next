self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  return;
});

self.addEventListener('push', (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const title = data.title || 'Visitor Alert';
    const options = {
      body: data.body || 'A visitor is at the gate.',
      icon: '/gruhamitra/GruhaMitra_Logo.png',
      badge: '/gruhamitra/GruhaMitra_Logo.png',
      vibrate: [200, 100, 200],
      data: data.data || {},
      actions: [
        { action: 'approve', title: 'Approve' },
        { action: 'reject', title: 'Reject' }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(title, options)
    );
  } catch (e) {
    console.error('Failed to parse push data:', e);
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const visitorId = event.notification.data?.visitor_id;
  if (!visitorId) return;

  let targetUrl = '/gruhamitra/visitors';
  if (event.action === 'approve') {
    targetUrl += `?action=approve&id=${visitorId}`;
  } else if (event.action === 'reject') {
    targetUrl += `?action=reject&id=${visitorId}`;
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/gruhamitra') && 'focus' in client) {
          return client.navigate(targetUrl).then(c => c.focus());
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
    })
  );
});

