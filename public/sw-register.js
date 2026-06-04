/*
  Service Worker Registration
  Safely register SW and handle updates
*/

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js', { scope: '/' })
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
  });

  // Handle controller change (SW updated)
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    console.log('[App] Service Worker controller changed');
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
