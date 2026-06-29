/*
  Service Worker Registration
  Safely register SW and handle updates
*/

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    if (!window.location.pathname.startsWith('/mitrabooks-erp/')) {
      return;
    }

    const isStagingHost = /(^staging\.mitrabooks\.sanmitratech\.in$|mitrabooks-erp-staging\.vercel\.app$)/i
      .test(window.location.hostname);
    const isProductionHost = /(^mitrabooks\.sanmitratech\.in$|^www\.mitrabooks\.sanmitratech\.in$)/i
      .test(window.location.hostname);

    if (isStagingHost) {
      clearServiceWorkerCaches()
        .then(() => {
          console.log('[App] Staging service worker cache cleared');
          const reloadKey = 'mitrabooks-staging-cache-cleared-v20';
          if (!sessionStorage.getItem(reloadKey)) {
            sessionStorage.setItem(reloadKey, '1');
            window.location.reload();
          }
        })
        .catch((error) => {
          console.warn('[App] Failed to clear staging service worker cache:', error);
        });
      return;
    }

    if (isProductionHost) {
      const reloadKey = 'mitrabooks-production-cache-reset-v17';
      if (!sessionStorage.getItem(reloadKey)) {
        clearServiceWorkerCaches()
          .then(() => {
            console.log('[App] Production service worker cache reset');
            sessionStorage.setItem(reloadKey, '1');
            window.location.reload();
          })
          .catch((error) => {
            console.warn('[App] Failed to reset production service worker cache:', error);
            sessionStorage.setItem(reloadKey, '1');
            registerServiceWorker();
          });
        return;
      }
    }

    registerServiceWorker();
  });

  // Handle controller change (SW updated)
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    console.log('[App] Service Worker controller changed');
  });
}

function clearServiceWorkerCaches() {
  return navigator.serviceWorker.getRegistrations()
    .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
    .then(() => {
      if ('caches' in window) {
        return caches.keys().then((cacheNames) => Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName))));
      }
      return undefined;
    });
}

function registerServiceWorker() {
  navigator.serviceWorker
    .register('/service-worker.js', { scope: '/mitrabooks-erp/' })
    .then((registration) => {
      console.log('[App] Service Worker registered:', registration);

      // Check for updates periodically
      setInterval(() => {
        registration.update();
      }, 60000); // Check every minute

      // Listen for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[App] Service Worker update available');
            // Notify user (optional)
            notifyUpdateAvailable();
          }
        });
      });
    })
    .catch((error) => {
      console.warn('[App] Service Worker registration failed:', error);
    });
}

// Optional: Notify user of updates
function notifyUpdateAvailable() {
  // Could show toast notification here
  console.log('[App] Refresh page to get latest version');
}

// Optional: Allow clients to trigger SW skip waiting
function skipWaitingServiceWorker() {
  const registration = navigator.serviceWorker.ready;
  registration.then((reg) => {
    if (reg.waiting) {
      reg.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  });
}
