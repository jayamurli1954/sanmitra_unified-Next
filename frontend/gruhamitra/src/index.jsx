import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import ErrorBoundary from './ErrorBoundary';

const escapeHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

const bindReloadButton = (container) => {
  const reloadButton = container?.querySelector('[data-reload-page]');
  reloadButton?.addEventListener('click', () => window.location.reload());
};

console.log('GruhaMitra: Starting initialization...');
console.log('React imported:', typeof React !== 'undefined');

console.log('GruhaMitra: Application starting...');
console.log('React imported successfully');

// Error boundary for initialization
try {
  // Get root element
  const container = document.getElementById('root');
  
  if (!container) {
    throw new Error('Root element not found! Make sure index.html has <div id="root"></div>');
  }

  console.log('Root container found, creating React root...');
  
  // Show loading indicator
  container.innerHTML = '<div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif;"><h1 style="color: #007AFF;">GruhaMitra</h1><p style="color: #666;">Loading React...</p></div>';
  
  const root = createRoot(container);
  console.log('React root created, rendering app...');

  // Render app with error boundary
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  );

  // Mark React as mounted so global error handler stops
  window.__REACT_MOUNTED__ = true;
  console.log('App rendered successfully!');
} catch (error) {
  console.error('FATAL ERROR: Failed to initialize GruhaMitra:', error);
  
  // Show error message on screen with full details
  const container = document.getElementById('root') || document.body;
  const errorMessage = escapeHtml(error.message || 'Unknown error');
  const errorStack = escapeHtml(error.stack || error.toString());
  
  container.innerHTML = `
    <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif; padding: 20px; text-align: center; background: #fff;">
      <h1 style="color: #ff4444; margin-bottom: 20px;"> Application Error</h1>
      <p style="color: #666; font-size: 18px; margin-bottom: 10px;">Failed to load GruhaMitra</p>
      <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; max-width: 800px; margin: 20px 0; text-align: left;">
        <p style="color: #333; font-size: 14px; margin-bottom: 10px; font-weight: bold;">Error Message:</p>
        <p style="color: #ff4444; font-size: 12px; margin-bottom: 15px; word-break: break-all;">${errorMessage}</p>
        <details style="margin-top: 10px;">
          <summary style="cursor: pointer; color: #007AFF; margin-bottom: 10px;">Show Full Error Details</summary>
          <pre style="color: #666; font-size: 11px; text-align: left; overflow-x: auto; background: #fff; padding: 10px; border-radius: 4px; margin-top: 10px;">${errorStack}</pre>
        </details>
      </div>
      <div style="margin-top: 20px;">
        <p style="color: #999; font-size: 12px; margin-bottom: 10px;">To open Developer Tools (if F12 doesn't work):</p>
        <ul style="color: #666; font-size: 11px; text-align: left; list-style: none; padding: 0;">
          <li> Right-click page  "Inspect" or "Inspect Element"</li>
          <li> Press Ctrl + Shift + I</li>
          <li> Press Ctrl + Shift + J (Chrome/Edge)</li>
          <li> Menu (3 dots)  More Tools  Developer Tools</li>
        </ul>
      </div>
      <button type="button" data-reload-page style="margin-top: 20px; padding: 12px 24px; background: #007AFF; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold;">Reload Page</button>
    </div>
  `;
  bindReloadButton(container);
}


