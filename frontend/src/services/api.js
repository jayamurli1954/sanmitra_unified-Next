import axios from 'axios';
import { getApiBaseUrl } from '../utils/apiBaseUrl';
import { buildActiveTempleHeaders } from '../utils/activeTemple';
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from '../utils/authStorage';
import { handleTenantInactive, isTenantInactiveMessage, isTenantInactivePayload } from '../utils/tenantInactive';

const api = axios.create({
  baseURL: getApiBaseUrl({ preferDirect: true }),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 20000,
});

const refreshClient = axios.create({
  baseURL: getApiBaseUrl({ preferDirect: true }),
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshPromise = null;

const shouldSkipRefresh = (config) => {
  const url = String(config?.url || '').toLowerCase();
  return url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout');
};

const isRefreshAuthFailure = (error) => {
  const status = Number(error?.response?.status);
  if (status === 401 || status === 403) {
    return true;
  }

  const message = String(error?.message || '').toLowerCase();
  return message.includes('missing refresh token') || message.includes('refresh response missing access token');
};

const forceLogout = (reason = 'unauthorized') => {
  clearAuthSession();
  window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { clear: true, reason } }));

  if (window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
};

const requestTokenRefresh = async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('Missing refresh token');
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const headers = buildActiveTempleHeaders({
      'Content-Type': 'application/json',
    });

    const refreshEndpoints = ['/api/v1/auth/refresh', '/api/auth/refresh'];
    let lastError = null;

    for (const endpoint of refreshEndpoints) {
      try {
        const response = await refreshClient.post(endpoint, { refresh_token: refreshToken }, { headers });
        const payload = response?.data || {};

        if (!payload?.access_token) {
          throw new Error('Refresh response missing access token');
        }

        setAccessToken(payload.access_token);
        setRefreshToken(payload.refresh_token || refreshToken);
        return payload.access_token;
      } catch (error) {
        lastError = error;
        const status = error?.response?.status;
        if (![404, 405].includes(Number(status))) {
          break;
        }
      }
    }

    throw lastError || new Error('Token refresh failed');
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
};

// Add token to requests
api.interceptors.request.use(
  (config) => {
    config.headers = buildActiveTempleHeaders(config.headers || {});
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle response errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const errorData = error.response?.data;
    const originalRequest = error.config || {};

    if (status === 401) {
      if (shouldSkipRefresh(originalRequest)) {
        return Promise.reject(error);
      }

      if (!originalRequest._retry) {
        originalRequest._retry = true;
        try {
          const newAccessToken = await requestTokenRefresh();
          originalRequest.headers = buildActiveTempleHeaders(originalRequest.headers || {});
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          if (isRefreshAuthFailure(refreshError)) {
            forceLogout('unauthorized');
          } else {
            error.userMessage = 'Session refresh is temporarily unavailable. Please retry.';
            return Promise.reject(error);
          }
        }
      } else {
        forceLogout('unauthorized');
      }
    }

    if (status === 403 && (isTenantInactivePayload(errorData) || isTenantInactiveMessage(errorData?.detail))) {
      handleTenantInactive(typeof errorData?.detail === 'string' ? errorData.detail : 'Tenant is inactive');
    }

    // Extract error message from response
    let errorMessage = 'An error occurred';
    if (errorData) {
      if (errorData.error?.message) {
        errorMessage = errorData.error.message;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.detail) {
        errorMessage = errorData.detail;
      }
    } else if (error.message) {
      errorMessage = error.message;
    }

    // Add error message to error object for easy access
    error.userMessage = errorMessage;

    return Promise.reject(error);
  }
);

export default api;
