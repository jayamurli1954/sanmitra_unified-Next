/**
 * Web-compatible API Service
 * Uses localStorage instead of AsyncStorage
 */
import axios from 'axios';
import storage from '../utils/storage';
import supabase from './supabaseClient';

const APP_KEY = (import.meta?.env?.VITE_APP_KEY || 'gruhamitra').trim();
const SHARED_ACCOUNTING_TENANTS = new Set(['default', 'demo_tenant', 'seed-tenant-1']);
const UNIFIED_BACKEND_API_URL = 'https://sanmitra-unified-next-staging-sg.onrender.com/api';
const VERCEL_PROXY_API_URL = '/api';
const DEFAULT_GRUHAMITRA_TENANT_ID = (
  import.meta?.env?.VITE_GRUHAMITRA_TENANT_ID || 'gruhamitra-demo-society'
).trim();

const isHostedVercelApp = () => (
  typeof window !== 'undefined' &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1' &&
  window.location.hostname.endsWith('vercel.app')
);

const normalizeApiUrl = (url) => {
  const rawUrl = String(url || '').trim();
  if (!rawUrl) {
    return '';
  }

  if (isHostedVercelApp() && (
    rawUrl.includes('gharmitra-backend.onrender.com') ||
    rawUrl.includes('sanmitra-backend-staging-sg.onrender.com') ||
    rawUrl.includes('sanmitra-unified-next-staging-sg.onrender.com')
  )) {
    return VERCEL_PROXY_API_URL;
  }

  // The legacy standalone backend rejects internal SanMitra admin emails and
  // lacks the unified v1 auth routes. Keep production pointed at the monolith.
  if (rawUrl.includes('gharmitra-backend.onrender.com')) {
    return UNIFIED_BACKEND_API_URL;
  }

  return rawUrl.replace(/\/+$/, '');
};

// Determine API URL based on environment
const getApiUrl = () => {
  const isBrowserHosted =
    typeof window !== 'undefined' &&
    window.location.hostname &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1';

  if (isBrowserHosted) {
    return isHostedVercelApp() ? VERCEL_PROXY_API_URL : UNIFIED_BACKEND_API_URL;
  }

  // Check if running in Electron
  if (typeof window !== 'undefined' && window.electron && window.electron.isDesktop) {
    return 'http://localhost:8002/api';
  }

  // Production / Building for Cloud (Priority 1)
  if (import.meta?.env?.VITE_API_URL) {
    return normalizeApiUrl(import.meta.env.VITE_API_URL);
  }

  // Runtime Environment Variable injection (Priority 2)
  if (typeof window !== 'undefined' && window.__API_URL__) {
    return normalizeApiUrl(window.__API_URL__);
  }

  // Production Detection - Vercel/Cloud deployment (Priority 3)
  if (isBrowserHosted) {
    // Running on Vercel or other cloud - use same-origin proxy to avoid browser CORS.
    return isHostedVercelApp() ? VERCEL_PROXY_API_URL : UNIFIED_BACKEND_API_URL;
  }

  // Local Development Fallback
  return 'http://localhost:8002/api';
};

// Create axios instance
const api = axios.create({
  baseURL: getApiUrl(),
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
    'X-App-Key': APP_KEY,
  },
});

let sessionRefreshPromise = null;

const decodeJwtPayload = (token) => {
  try {
    const payloadPart = String(token || '').split('.')[1];
    if (!payloadPart || typeof window === 'undefined' || !window.atob) {
      return null;
    }
    const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=');
    return JSON.parse(window.atob(padded));
  } catch (error) {
    return null;
  }
};

const getStoredGruhaTenantId = async () => {
  try {
    const rawUser = await storage.getItem('user');
    const user = rawUser ? JSON.parse(rawUser) : null;
    const candidates = [
      user?.society_id,
      localStorage.getItem('gruhamitra_tenant_id'),
      user?.tenant_id,
      DEFAULT_GRUHAMITRA_TENANT_ID,
    ];
    const tenantId = candidates
      .map((value) => String(value || '').trim())
      .find((value) => value && !SHARED_ACCOUNTING_TENANTS.has(value));

    return tenantId || DEFAULT_GRUHAMITRA_TENANT_ID;
  } catch (error) {
    return DEFAULT_GRUHAMITRA_TENANT_ID;
  }
};

const normalizeRelativeApiPath = (url) => {
  const rawUrl = typeof url === 'string' ? url : '';
  if (!rawUrl.startsWith('/')) {
    return rawUrl;
  }

  const [pathPart, queryPart = ''] = rawUrl.split('?', 2);
  const normalizedPath = pathPart.length > 1 ? pathPart.replace(/\/+$/, '') : pathPart;
  return queryPart ? `${normalizedPath}?${queryPart}` : normalizedPath;
};

const clearAuthStateAndRedirectToLogin = async () => {
  try {
    await storage.removeItem('access_token');
    await storage.removeItem('user');
    await storage.removeItem('supabase_user');
    console.log('Session expired. Please login again.');
    window.location.href = '/gruhamitra/login';
  } catch (err) {
    console.error('Error clearing storage:', err);
  }
};

const refreshSupabaseSession = async () => {
  if (!sessionRefreshPromise) {
    sessionRefreshPromise = (async () => {
      const refreshResult = await supabase.auth.refreshSession();
      const refreshedSession = refreshResult?.data?.session || null;
      if (refreshedSession?.access_token) {
        await storage.setItem('access_token', refreshedSession.access_token);
        if (refreshedSession.user) {
          await storage.setItem('supabase_user', JSON.stringify(refreshedSession.user));
        }
        return refreshedSession.access_token;
      }

      const fallbackSessionResult = await supabase.auth.getSession();
      const fallbackSession = fallbackSessionResult?.data?.session || null;
      if (fallbackSession?.access_token) {
        await storage.setItem('access_token', fallbackSession.access_token);
        if (fallbackSession.user) {
          await storage.setItem('supabase_user', JSON.stringify(fallbackSession.user));
        }
        return fallbackSession.access_token;
      }

      return null;
    })().finally(() => {
      sessionRefreshPromise = null;
    });
  }

  return sessionRefreshPromise;
};

// Log API configuration on initialization
if (typeof window !== 'undefined') {
  console.log('API Service initialized with baseURL:', getApiUrl());
}

// Request interceptor - Add auth token to all requests
api.interceptors.request.use(
  async (config) => {
    try {
      const rawUrl = normalizeRelativeApiPath(config.url);
      const isRelativeApiPath = rawUrl.startsWith('/');
      const isAlreadyVersioned = /^\/v1(\/|$)/.test(rawUrl);
      const normalizedUrl = isRelativeApiPath && !isAlreadyVersioned ? `/v1${rawUrl}` : rawUrl;
      const isAuthCredentialRequest = /\/auth\/(login|local-login|legacy-login|register|google|refresh)(\/|$)/.test(normalizedUrl);
      const isAccountingRequest =
        /\/accounting(\/|$)/.test(normalizedUrl) ||
        /\/journal(\/|$|\?)/.test(normalizedUrl) ||
        /\/transactions(\/|$)/.test(normalizedUrl) ||
        /\/reports\/trial-balance(\/|$|\?)/.test(normalizedUrl);
      if (isRelativeApiPath && !isAlreadyVersioned) {
        config.url = normalizedUrl;
      }

      config.headers = config.headers || {};
      if (APP_KEY && !config.headers['X-App-Key']) {
        config.headers['X-App-Key'] = APP_KEY;
      }
      const token = await storage.getItem('access_token');
      if (token) {
        const tokenPayload = decodeJwtPayload(token);
        const tokenTenant = String(tokenPayload?.tenant_id || '').trim();
        const tokenRole = String(tokenPayload?.role || '').trim();
        const shouldUseGruhaTenantHeader =
          APP_KEY === 'gruhamitra' &&
          !isAuthCredentialRequest &&
          !config.headers['X-Tenant-ID'] &&
          (isAccountingRequest || SHARED_ACCOUNTING_TENANTS.has(tokenTenant) || tokenRole === 'super_admin');
        if (shouldUseGruhaTenantHeader) {
          const tenantId = await getStoredGruhaTenantId();
          if (tenantId) {
            config.headers['X-Tenant-ID'] = tenantId;
          }
        }
        const effectiveTenant = String(config.headers['X-Tenant-ID'] || tokenTenant).trim();
        if (isAccountingRequest && APP_KEY === 'gruhamitra' && SHARED_ACCOUNTING_TENANTS.has(effectiveTenant)) {
          return Promise.reject(new Error('GruhaMitra accounting cannot use a shared/default tenant. Please login with a housing society tenant.'));
        }
        if (!isAuthCredentialRequest) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch (error) {
      console.error('Error getting access token:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors globally
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const skipAuthRedirect = Boolean(error?.config?.skipAuthRedirect);

    // Network error (connection failed)
    if (error.code === 'ECONNREFUSED' || error.code === 'NETWORK_ERROR' || error.code === 'ERR_NETWORK' || !error.response) {
      console.error('Network Error:', {
        message: error.message,
        code: error.code,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        fullURL: error.config?.baseURL + error.config?.url,
      });

      // Check if it's a CORS error
      if (error.message && error.message.includes('CORS')) {
        return Promise.reject({
          message: 'CORS error: Backend may not be allowing requests from this origin. Check CORS settings.',
          code: 'CORS_ERROR',
          originalError: error,
        });
      }

      return Promise.reject({
        message: 'Cannot connect to GruhaMitra backend. Please check your internet connection and retry. If the problem continues, contact support with the time of the error.',
        code: 'CONNECTION_ERROR',
        originalError: error,
      });
    }

    // 500 Internal Server Error - Backend crashed
    if (error.response?.status >= 500) {
      console.error('Server Error (500+):', {
        status: error.response.status,
        data: error.response.data,
        url: error.config?.url,
      });
      return Promise.reject({
        message: `Internal Server Error (500). The backend encountered an unexpected condition. (v1.2.3)`,
        code: 'SERVER_ERROR',
        response: error.response,
      });
    }

    // 401 Unauthorized - Token expired or invalid
    if (error.response?.status === 401) {
      if (skipAuthRedirect) {
        return Promise.reject(error);
      }

      const originalRequest = error.config || {};
      if (!originalRequest._retry) {
        originalRequest._retry = true;
        try {
          const refreshedToken = await refreshSupabaseSession();
          if (refreshedToken) {
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${refreshedToken}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          console.warn('Supabase session refresh failed:', refreshError);
        }
      }

      await clearAuthStateAndRedirectToLogin();
    }

    // 403 Forbidden
    if (error.response?.status === 403) {
      const errorDetail = error.response?.data?.detail || error.response?.data?.message || 'You do not have permission to perform this action';

      if (!skipAuthRedirect && error.config?.url?.includes('/auth/')) {
        try {
          await storage.removeItem('access_token');
          await storage.removeItem('user');
          window.location.href = '/gruhamitra/login';
        } catch (err) {
          console.error('Error clearing storage:', err);
        }
      }

      console.error('Permission Error (403):', {
        message: errorDetail,
        url: error.config?.url,
      });
    }

    return Promise.reject(error);
  }
);

export default api;
