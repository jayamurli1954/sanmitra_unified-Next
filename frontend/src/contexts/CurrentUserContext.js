import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  readStoredUser,
  writeStoredUser,
  clearStoredUser,
  readAccessTokenClaims,
} from '../utils/authStorage';

const LAYOUT_CACHE_TTL_MS = 2 * 60 * 1000;
const USER_PROFILE_CACHE_KEY = 'layout_user_profile_cache_v1';
const AUTH_REFRESH_ENDPOINTS = ['/api/v1/auth/refresh', '/api/auth/refresh'];

const isAuthFailureStatus = (status) => status === 401;
const PLATFORM_ADMIN_ROLES = new Set(['super_admin', 'superadmin', 'platform_owner', 'platform_admin']);

const CurrentUserContext = createContext({
  user: {},
  loading: false,
  refreshUser: async () => ({}),
  clearUser: () => {},
});

const readCachedProfile = () => {
  try {
    const raw = sessionStorage.getItem(USER_PROFILE_CACHE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      sessionStorage.removeItem(USER_PROFILE_CACHE_KEY);
      return null;
    }

    if (typeof parsed.expiresAt !== 'number' || Date.now() > parsed.expiresAt) {
      sessionStorage.removeItem(USER_PROFILE_CACHE_KEY);
      return null;
    }

    return parsed.value ?? null;
  } catch (error) {
    sessionStorage.removeItem(USER_PROFILE_CACHE_KEY);
    return null;
  }
};

const writeCachedProfile = (value, ttlMs = LAYOUT_CACHE_TTL_MS) => {
  try {
    sessionStorage.setItem(
      USER_PROFILE_CACHE_KEY,
      JSON.stringify({
        value,
        expiresAt: Date.now() + ttlMs,
      })
    );
  } catch (error) {
    // Ignore storage write failures.
  }
};

const normalizeCurrentUser = (userData, fallbackUser = {}) => {
  const tokenClaims = readAccessTokenClaims() || {};
  const tokenRole = String(tokenClaims.system_role || tokenClaims.role || '').toLowerCase();
  const profileRole = userData?.system_role || userData?.role || fallbackUser.system_role || fallbackUser.role;
  const resolvedRole = PLATFORM_ADMIN_ROLES.has(tokenRole) ? tokenRole : profileRole;

  return {
    ...fallbackUser,
    id: userData?.id ?? fallbackUser.id ?? tokenClaims.sub,
    email: userData?.email ?? fallbackUser.email ?? tokenClaims.email,
    full_name: userData?.full_name ?? fallbackUser.full_name,
    name: userData?.full_name || userData?.email || fallbackUser.name || tokenClaims.email,
    role: resolvedRole,
    system_role: resolvedRole,
    role_key: userData?.role_key ?? fallbackUser.role_key,
    role_label: userData?.role_label ?? fallbackUser.role_label,
    phone: userData?.phone ?? fallbackUser.phone ?? '',
    module_permissions: userData?.module_permissions || fallbackUser.module_permissions || {},
    action_permissions: userData?.action_permissions || fallbackUser.action_permissions || {},
    is_superuser: Boolean(userData?.is_superuser ?? fallbackUser.is_superuser ?? ['super_admin', 'superadmin'].includes(tokenRole)),
    must_change_password: Boolean(userData?.must_change_password ?? fallbackUser.must_change_password),
  };
};

export function CurrentUserProvider({ children }) {
  const [user, setUser] = useState(() => {
    const cachedProfile = readCachedProfile();
    if (cachedProfile && typeof cachedProfile === 'object') {
      return cachedProfile;
    }
    return readStoredUser();
  });
  const [loading, setLoading] = useState(() => Boolean(getAccessToken()));

  const applyUser = useCallback((nextUser) => {
    const normalized = normalizeCurrentUser(nextUser, readStoredUser());
    setUser(normalized);
    writeStoredUser(normalized);
    writeCachedProfile(normalized);
    return normalized;
  }, []);

  const clearUser = useCallback(() => {
    setUser({});
    setLoading(false);
    clearStoredUser();
    sessionStorage.removeItem(USER_PROFILE_CACHE_KEY);
  }, []);

  const refreshUser = useCallback(async () => {
    let token = getAccessToken();
    if (!token) {
      clearUser();
      return {};
    }

    const tryRefreshToken = async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        return null;
      }

      let lastRefreshError = null;
      for (const endpoint of AUTH_REFRESH_ENDPOINTS) {
        const refreshResponse = await fetchWithApiFallback(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        }, { timeoutMs: 12000, maxAttemptsPerOrigin: 1 });

        if (refreshResponse.ok) {
          const payload = await refreshResponse.json();
          if (!payload?.access_token) {
            throw new Error('Refresh response missing access token');
          }
          setAccessToken(payload.access_token);
          setRefreshToken(payload.refresh_token || refreshToken);
          return payload.access_token;
        }

        if ([404, 405].includes(Number(refreshResponse.status))) {
          lastRefreshError = new Error('Refresh endpoint not found');
          continue;
        }

        lastRefreshError = new Error('Refresh request failed');
        lastRefreshError.status = refreshResponse.status;
        break;
      }

      if (lastRefreshError) {
        throw lastRefreshError;
      }
      return null;
    };

    setLoading(true);
    try {
      let response = await fetchWithApiFallback('/api/v1/users/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }, { timeoutMs: 12000 });

      if (response.status === 401) {
        const refreshedToken = await tryRefreshToken();
        if (refreshedToken) {
          token = refreshedToken;
          response = await fetchWithApiFallback('/api/v1/users/me', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }, { timeoutMs: 12000 });
        }
      }

      if (!response.ok) {
        const error = new Error('Failed to load current user');
        error.status = response.status;
        throw error;
      }

      const data = await response.json();
      return applyUser(data);
    } finally {
      setLoading(false);
    }
  }, [applyUser, clearUser]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }

    refreshUser().catch((error) => {
      console.error('Failed to refresh current user', error);
      if (isAuthFailureStatus(error?.status)) {
        clearAuthSession();
        clearUser();
        return;
      }
      setUser(readStoredUser());
      setLoading(false);
    });
  }, [clearUser, refreshUser]);

  useEffect(() => {
    const handleProfileUpdated = (event) => {
      if (event?.detail && typeof event.detail === 'object') {
        applyUser(event.detail);
        setLoading(false);
        return;
      }

      refreshUser().catch((error) => {
        console.error('Failed to refresh current user after profile update', error);
        if (isAuthFailureStatus(error?.status)) {
          clearAuthSession();
          clearUser();
          return;
        }
        setUser(readStoredUser());
        setLoading(false);
      });
    };

    const handleAuthStateChanged = (event) => {
      if (event?.detail?.clear) {
        clearUser();
        return;
      }

      refreshUser().catch((error) => {
        console.error('Failed to refresh current user after auth state change', error);
        if (isAuthFailureStatus(error?.status)) {
          clearAuthSession();
          clearUser();
          return;
        }
        setUser(readStoredUser());
        setLoading(false);
      });
    };

    window.addEventListener('user-profile-updated', handleProfileUpdated);
    window.addEventListener('auth-state-changed', handleAuthStateChanged);

    return () => {
      window.removeEventListener('user-profile-updated', handleProfileUpdated);
      window.removeEventListener('auth-state-changed', handleAuthStateChanged);
    };
  }, [applyUser, clearUser, refreshUser]);

  const value = useMemo(() => ({
    user,
    loading,
    refreshUser,
    clearUser,
  }), [clearUser, loading, refreshUser, user]);

  return (
    <CurrentUserContext.Provider value={value}>
      {children}
    </CurrentUserContext.Provider>
  );
}

export function useCurrentUser() {
  return useContext(CurrentUserContext);
}
