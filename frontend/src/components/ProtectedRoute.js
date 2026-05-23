import React, { useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';
import { getAccessToken, readStoredUser, writeStoredUser } from '../utils/authStorage';
import { getActiveTempleId } from '../utils/activeTemple';

const SETUP_REDIRECT_EXEMPT_PATHS = new Set(['/profile']);
const SETUP_GUARD_CACHE_KEY = 'mm_setup_guard_cache_v1';
const SETUP_GUARD_CACHE_TTL_MS = 60 * 1000;
const PLATFORM_ADMIN_ROLES = new Set(['super_admin', 'superadmin', 'platform_owner', 'platform_admin']);

const readCurrentUser = () => readStoredUser();

const normalizeCurrentUser = (userData, fallbackUser = {}) => ({
  ...fallbackUser,
  id: userData?.id ?? fallbackUser.id,
  email: userData?.email ?? fallbackUser.email,
  full_name: userData?.full_name ?? fallbackUser.full_name,
  name: userData?.full_name || userData?.email || fallbackUser.name,
  role: userData?.system_role || userData?.role || fallbackUser.role,
  system_role: userData?.system_role || userData?.role || fallbackUser.system_role,
  role_key: userData?.role_key ?? fallbackUser.role_key,
  role_label: userData?.role_label ?? fallbackUser.role_label,
  phone: userData?.phone ?? fallbackUser.phone ?? '',
  module_permissions: userData?.module_permissions || fallbackUser.module_permissions || {},
  action_permissions: userData?.action_permissions || fallbackUser.action_permissions || {},
  is_superuser: Boolean(userData?.is_superuser ?? fallbackUser.is_superuser),
  must_change_password: Boolean(userData?.must_change_password ?? fallbackUser.must_change_password),
});

const readGuardCache = () => {
  try {
    const raw = sessionStorage.getItem(SETUP_GUARD_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      sessionStorage.removeItem(SETUP_GUARD_CACHE_KEY);
      return null;
    }
    if (typeof parsed.expiresAt !== 'number' || Date.now() > parsed.expiresAt) {
      sessionStorage.removeItem(SETUP_GUARD_CACHE_KEY);
      return null;
    }
    return parsed.value ?? null;
  } catch (_error) {
    sessionStorage.removeItem(SETUP_GUARD_CACHE_KEY);
    return null;
  }
};

const writeGuardCache = (value, ttlMs = SETUP_GUARD_CACHE_TTL_MS) => {
  try {
    sessionStorage.setItem(
      SETUP_GUARD_CACHE_KEY,
      JSON.stringify({
        value,
        expiresAt: Date.now() + ttlMs,
      })
    );
  } catch (_error) {
    // Ignore cache write failures.
  }
};

function ProtectedRoute({ children }) {
  const token = getAccessToken();
  const location = useLocation();
  const cachedGuard = useMemo(() => readGuardCache(), []);
  const [state, setState] = useState(() => {
    if (!token) {
      return {
        loading: false,
        setupData: null,
        currentUser: {},
      };
    }

    if (cachedGuard) {
      return {
        loading: false,
        setupData: cachedGuard.setupData || null,
        currentUser: cachedGuard.currentUser || readCurrentUser(),
      };
    }

    return {
      loading: true,
      setupData: null,
      currentUser: readCurrentUser(),
    };
  });

  useEffect(() => {
    if (!token) {
      sessionStorage.removeItem(SETUP_GUARD_CACHE_KEY);
      setState({ loading: false, setupData: null, currentUser: {} });
      return;
    }

    let cancelled = false;

    const hydrateGuard = async () => {
      try {
        const fallbackUser = readCurrentUser();
        const [setupResponse, currentUserResponse] = await Promise.all([
          fetchWithApiFallback('/api/v1/setup-wizard/status', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }, { timeoutMs: 6000, maxAttemptsPerOrigin: 1 }),
          fetchWithApiFallback('/api/v1/users/me', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }, { timeoutMs: 6000, maxAttemptsPerOrigin: 1 }),
        ]);

        const data = setupResponse.ok
          ? await setupResponse.json()
          : { force_setup: false, can_manage_setup: true };

        let currentUser = fallbackUser;
        if (currentUserResponse.ok) {
          const currentUserData = await currentUserResponse.json();
          currentUser = normalizeCurrentUser(currentUserData, fallbackUser);
          writeStoredUser(currentUser);
        }

        if (!cancelled) {
          const nextState = {
            loading: false,
            setupData: data,
            currentUser,
          };
          setState(nextState);
          writeGuardCache({
            setupData: data,
            currentUser,
          });
        }
      } catch (_error) {
        if (!cancelled) {
          // Fail-open for navigation stability when backend is slow/unreachable.
          setState((prev) => ({
            loading: false,
            setupData: prev.setupData || { force_setup: false, can_manage_setup: true },
            currentUser: prev.currentUser || readCurrentUser(),
          }));
        }
      }
    };

    hydrateGuard();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (state.loading) {
    return <div style={{ padding: 16 }}>Loading...</div>;
  }

  const currentUser = state.currentUser || {};
  const setupData = state.setupData || { force_setup: false, can_manage_setup: true };
  const onWizardPage = location.pathname === '/setup-wizard';
  const isSetupRedirectExempt = SETUP_REDIRECT_EXEMPT_PATHS.has(location.pathname);
  const resolvedRole = String(currentUser?.system_role || currentUser?.role || '').toLowerCase();
  const isPlatformSuperAdmin = Boolean(currentUser?.is_superuser) || PLATFORM_ADMIN_ROLES.has(resolvedRole);
  const activeTempleId = getActiveTempleId();

  let redirectTo = null;
  if (Boolean(currentUser?.must_change_password) && location.pathname !== '/profile') {
    redirectTo = '/profile';
  } else if (location.pathname === '/dashboard' && isPlatformSuperAdmin && !activeTempleId) {
    redirectTo = '/platform/temples';
  } else if (setupData.force_setup && !onWizardPage && !isSetupRedirectExempt && !isPlatformSuperAdmin) {
    redirectTo = '/setup-wizard';
  } else if (onWizardPage && !setupData.can_manage_setup && !isPlatformSuperAdmin) {
    redirectTo = '/dashboard';
  }

  if (redirectTo && redirectTo !== location.pathname) {
    return <Navigate to={redirectTo} replace />;
  }

  return children;
}

export default ProtectedRoute;


