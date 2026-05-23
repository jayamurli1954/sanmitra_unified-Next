import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import './i18n';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((registration) => {
        registration.update().catch(() => {});
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error('Service worker registration failed:', err);
      });
  });

  let reloadedForServiceWorkerUpdate = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloadedForServiceWorkerUpdate) {
      return;
    }
    reloadedForServiceWorkerUpdate = true;
    window.location.reload();
  });
}
