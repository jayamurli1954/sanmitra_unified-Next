import React, { useEffect, useState } from 'react';

const DISMISS_STORAGE_KEY = 'gm_install_banner_dismissed_until';
const DISMISS_DURATION_MS = 3 * 24 * 60 * 60 * 1000;

const isStandaloneMode = () => {
  if (typeof window === 'undefined') return false;
  const inDisplayMode = window.matchMedia && window.matchMedia('(display-mode: standalone)').matches;
  const iosStandalone = window.navigator && window.navigator.standalone === true;
  return Boolean(inDisplayMode || iosStandalone);
};

const isIosDevice = () => {
  if (typeof window === 'undefined') return false;
  const ua = window.navigator.userAgent.toLowerCase();
  const isAppleMobile = /iphone|ipad|ipod/.test(ua);
  const isIpadOsDesktopUA = window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1;
  return isAppleMobile || isIpadOsDesktopUA;
};

const isLikelyMobileDevice = () => {
  if (typeof window === 'undefined') return false;
  const ua = window.navigator.userAgent.toLowerCase();
  const byUa = /android|iphone|ipad|ipod|mobile/.test(ua);
  const byViewport = window.matchMedia && window.matchMedia('(max-width: 1024px)').matches;
  return Boolean(byUa || byViewport);
};

const getDismissedUntil = () => {
  try {
    const value = Number(localStorage.getItem(DISMISS_STORAGE_KEY));
    return Number.isFinite(value) ? value : 0;
  } catch (error) {
    return 0;
  }
};

const saveDismissedUntil = () => {
  try {
    localStorage.setItem(
      DISMISS_STORAGE_KEY,
      String(Date.now() + DISMISS_DURATION_MS)
    );
  } catch (error) {
    // Ignore storage write failures in private/incognito modes.
  }
};

const PWAInstallBanner = () => {
  const [mode, setMode] = useState(null); // 'prompt' | 'ios' | 'manual'
  const [deferredPrompt, setDeferredPrompt] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    if (isStandaloneMode()) return undefined;
    if (getDismissedUntil() > Date.now()) return undefined;

    const ios = isIosDevice();
    if (ios) {
      setMode('ios');
    }

    const handleBeforeInstallPrompt = (event) => {
      event.preventDefault();
      setDeferredPrompt(event);
      setMode('prompt');
    };

    const handleAppInstalled = () => {
      setDeferredPrompt(null);
      setMode(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    const manualHintTimer = window.setTimeout(() => {
      if (!ios && !isStandaloneMode() && isLikelyMobileDevice()) {
        setMode((currentMode) => currentMode || 'manual');
      }
    }, 3500);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
      window.clearTimeout(manualHintTimer);
    };
  }, []);

  const handleDismiss = () => {
    saveDismissedUntil();
    setDeferredPrompt(null);
    setMode(null);
  };

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();

    try {
      const choice = await deferredPrompt.userChoice;
      if (choice && choice.outcome === 'accepted') {
        setMode(null);
      } else {
        setMode('manual');
      }
    } finally {
      setDeferredPrompt(null);
    }
  };

  if (!mode) return null;

  let title = 'Install GruhaMitra';
  let message = 'Add the app to your home screen for one-tap access.';
  let showInstallAction = mode === 'prompt';

  if (mode === 'ios') {
    message = 'In Safari, tap Share and then "Add to Home Screen".';
    showInstallAction = false;
  } else if (mode === 'manual') {
    message = 'Open your browser menu and choose "Install app" or "Add to Home screen".';
    showInstallAction = false;
  }

  return (
    <div className="pwa-install-banner" role="region" aria-label="Install app">
      <div className="pwa-install-title">{title}</div>
      <div className="pwa-install-text">{message}</div>
      <div className="pwa-install-actions">
        {showInstallAction && (
          <button type="button" className="pwa-install-btn" onClick={handleInstall}>
            Install
          </button>
        )}
        <button type="button" className="pwa-install-btn secondary" onClick={handleDismiss}>
          Not now
        </button>
      </div>
    </div>
  );
};

export default PWAInstallBanner;
