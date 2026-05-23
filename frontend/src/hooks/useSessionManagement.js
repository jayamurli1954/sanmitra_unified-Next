import { useEffect, useRef, useCallback } from 'react';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';
import { getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from '../utils/authStorage';

const INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
const INACTIVITY_WARNING_TIME_MS = 1 * 60 * 1000; // 1 minute before logout
const TOKEN_REFRESH_INTERVAL_MS = 50 * 60 * 1000; // Refresh at 50 min (before 60 min expiry)
const INACTIVITY_CHECK_INTERVAL_MS = 15 * 1000; // Check every 15 seconds

export function useSessionManagement(onLogout, onShowWarning) {
  const lastActivityRef = useRef(Date.now());
  const warningShownRef = useRef(false);
  const tokenRefreshIntervalRef = useRef(null);
  const inactivityCheckIntervalRef = useRef(null);

  // Perform token refresh using the keep-alive endpoint
  const refreshTokenSilently = useCallback(async () => {
    try {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        return false;
      }

      const response = await fetchWithApiFallback('/api/v1/auth/keep-alive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }, { timeoutMs: 8000 });

      if (response.ok) {
        const data = await response.json();
        if (data.access_token) {
          setAccessToken(data.access_token);
          if (data.refresh_token) {
            setRefreshToken(data.refresh_token);
          }
          console.debug('Token refreshed silently');
          return true;
        }
      }

      if (response.status === 401) {
        // Refresh token expired or invalid
        onLogout();
        return false;
      }
    } catch (error) {
      console.warn('Silent token refresh failed:', error);
    }
    return false;
  }, [onLogout]);

  // Reset inactivity timer
  const resetInactivityTimer = useCallback(() => {
    if (!getAccessToken()) return;

    lastActivityRef.current = Date.now();
    warningShownRef.current = false;
  }, []);

  // Check inactivity and show warning if needed
  const checkInactivity = useCallback(() => {
    if (!getAccessToken()) return;

    const timeInactive = Date.now() - lastActivityRef.current;

    // If warning should be shown
    if (timeInactive >= INACTIVITY_TIMEOUT_MS - INACTIVITY_WARNING_TIME_MS && !warningShownRef.current) {
      warningShownRef.current = true;
      onShowWarning?.();
    }

    // If completely inactive, logout
    if (timeInactive >= INACTIVITY_TIMEOUT_MS) {
      console.warn('Session expired due to inactivity');
      onLogout();
    }
  }, [onLogout, onShowWarning]);

  // Setup activity tracking
  useEffect(() => {
    if (!getAccessToken()) return;

    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];

    activityEvents.forEach((event) => {
      window.addEventListener(event, resetInactivityTimer, { passive: true });
    });

    return () => {
      activityEvents.forEach((event) => {
        window.removeEventListener(event, resetInactivityTimer);
      });
    };
  }, [resetInactivityTimer]);

  // Setup periodic token refresh (at 50-minute mark)
  useEffect(() => {
    if (!getAccessToken()) return;

    tokenRefreshIntervalRef.current = window.setInterval(() => {
      refreshTokenSilently();
    }, TOKEN_REFRESH_INTERVAL_MS);

    return () => {
      if (tokenRefreshIntervalRef.current) {
        window.clearInterval(tokenRefreshIntervalRef.current);
      }
    };
  }, [refreshTokenSilently]);

  // Setup inactivity checking
  useEffect(() => {
    if (!getAccessToken()) return;

    inactivityCheckIntervalRef.current = window.setInterval(() => {
      checkInactivity();
    }, INACTIVITY_CHECK_INTERVAL_MS);

    return () => {
      if (inactivityCheckIntervalRef.current) {
        window.clearInterval(inactivityCheckIntervalRef.current);
      }
    };
  }, [checkInactivity]);

  // Handle visibility change (tab focus)
  // Don't logout on minimize - just check if session is still valid
  useEffect(() => {
    if (!getAccessToken()) return;

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Tab became visible - validate token is still good
        resetInactivityTimer();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [resetInactivityTimer]);

  // Export public methods
  return {
    resetInactivityTimer,
    refreshTokenSilently,
    checkInactivity,
  };
}
