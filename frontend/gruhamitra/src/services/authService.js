/**
 * Web-compatible Authentication Service
 */
import api from './api';
import storage from '../utils/storage';
import supabase, { supabaseEnabled } from './supabaseClient';

let authListenerRegistered = false;
const BACKEND_PROFILE_ENDPOINT = '/v1/auth/me';
const BACKEND_LOGIN_FALLBACK_ENDPOINTS = ['/v1/auth/login', '/auth/local-login', '/auth/login'];

const normalizeEmail = (email) => String(email || '').trim().toLowerCase();
const QUICK_PROFILE_WAIT_MS = 1200;
const SUPABASE_LOGIN_TIMEOUT_MS = 12000;
const LEGACY_LOGIN_TIMEOUT_MS = 6000;

const withTimeout = (promise, timeoutMs, message) => {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => {
        const timeoutError = new Error(message || 'Operation timed out');
        timeoutError.name = 'TimeoutError';
        reject(timeoutError);
      }, timeoutMs);
    }),
  ]);
};

const parseUserSafe = (rawUser) => {
  if (!rawUser) return null;
  try {
    const user = JSON.parse(rawUser);
    if (!user || (!user.email && !user.id && !user.username)) {
      return null;
    }
    return user;
  } catch (error) {
    return null;
  }
};

const getStoredUserMatchingEmail = async (email) => {
  const rawUser = await storage.getItem('user');
  const storedUser = parseUserSafe(rawUser);
  if (!storedUser) return null;
  if (!email) return storedUser;
  const storedEmail = normalizeEmail(storedUser.email);
  return storedEmail && storedEmail === email ? storedUser : null;
};

const setAccessToken = async (token) => {
  if (token) {
    await storage.setItem('access_token', token);
  } else {
    await storage.removeItem('access_token');
  }
};

const setSupabaseUser = async (user) => {
  if (user) {
    await storage.setItem('supabase_user', JSON.stringify(user));
  } else {
    await storage.removeItem('supabase_user');
  }
};

const setBackendAuthActive = async (active) => {
  if (active) {
    await storage.setItem('backend_auth_active', 'true');
  } else {
    await storage.removeItem('backend_auth_active');
  }
};

const clearStoredAuthState = async () => {
  await storage.removeItem('access_token');
  await storage.removeItem('user');
  await storage.removeItem('supabase_user');
  await storage.removeItem('backend_auth_active');
};

const fetchBackendProfileWithTimeout = async (timeoutMs = 5000) => {
  try {
    const response = await Promise.race([
      api.get(BACKEND_PROFILE_ENDPOINT),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Backend profile timeout')), timeoutMs)
      ),
    ]);
    return response?.data || null;
  } catch (error) {
    console.warn('Backend profile lookup skipped:', error?.message || error);
    return null;
  }
};

const isFallbackEndpointUnavailable = (status) => [404, 405, 410].includes(Number(status));

const storeBackendLoginResult = async (backendData) => {
  const token = backendData?.access_token || null;
  const user = backendData?.user || null;
  await setAccessToken(token);
  await setBackendAuthActive(Boolean(token));
  await setSupabaseUser(null);
  if (user) {
    await storage.setItem('user', JSON.stringify(user));
  }
  return backendData;
};

const tryBackendLogin = async (credentials) => {
  let lastError = null;
  for (const endpoint of BACKEND_LOGIN_FALLBACK_ENDPOINTS) {
    try {
      const response = await api.post(endpoint, credentials, {
        timeout: LEGACY_LOGIN_TIMEOUT_MS,
        skipAuthRedirect: true,
      });
      if (response?.data?.access_token) {
        return await storeBackendLoginResult(response.data);
      }
      lastError = new Error('Backend login response missing access token');
    } catch (error) {
      const status = error?.response?.status;
      if (isFallbackEndpointUnavailable(status)) {
        continue;
      }
      lastError = error;
      if (status === 401 || status === 422) {
        break;
      }
    }
  }
  if (lastError) {
    throw lastError;
  }
  return null;
};

export const authService = {
  /**
   * Register Supabase auth listener once
   */
  async initAuthListener() {
    if (authListenerRegistered) return;
    authListenerRegistered = true;

    // Avoid blocking startup on getSession network/refresh behavior.
    supabase.auth.onAuthStateChange(async (_event, session) => {
      try {
        const backendAuthActive = await storage.getItem('backend_auth_active');
        if (!session?.access_token && backendAuthActive === 'true') {
          return;
        }
        await setAccessToken(session?.access_token || null);
        await setBackendAuthActive(false);
        await setSupabaseUser(session?.user || null);
      } catch (error) {
        console.error('Failed to sync Supabase session:', error);
      }
    });
  },
  /**
   * Login with email and password
   */
  async login(credentials) {
    const normalizedCredentials = {
      ...credentials,
      email: normalizeEmail(credentials?.email),
    };

    const loginStartedAt = Date.now();
    let backendLoginError = null;

    // Unified backend is the primary auth source for GruhaMitra.
    try {
      const backendResponse = await tryBackendLogin(normalizedCredentials);
      if (backendResponse) {
        return backendResponse;
      }
    } catch (backendError) {
      backendLoginError = backendError;
      const status = backendError?.response?.status;
      if (status === 401 || status === 422) {
        const message =
          backendError?.response?.data?.detail ||
          backendError?.response?.data?.message ||
          'Incorrect email or password';
        const err = new Error(message);
        err.name = 'BackendAuthError';
        throw err;
      }
      console.warn('Primary backend login failed, trying Supabase fallback:', backendError);
    }

    if (!supabaseEnabled && backendLoginError) {
      const message =
        backendLoginError?.response?.data?.detail ||
        backendLoginError?.response?.data?.message ||
        backendLoginError?.message ||
        'Backend login failed';
      const err = new Error(message);
      err.name = 'BackendAuthError';
      throw err;
    }
    let data = null;
    let error = null;

    try {
      const signInResult = await withTimeout(
        supabase.auth.signInWithPassword({
          email: normalizedCredentials.email,
          password: normalizedCredentials.password,
        }),
        SUPABASE_LOGIN_TIMEOUT_MS,
        'Supabase login timed out'
      );
      data = signInResult?.data || null;
      error = signInResult?.error || null;
    } catch (signInError) {
      error = signInError;
    }

    if (error) {
      // Backward compatibility: try backend auth once more if Supabase auth fails.
      try {
        const legacyResponse = await tryBackendLogin(normalizedCredentials);
        if (legacyResponse) {
          return legacyResponse;
        }
      } catch (legacyError) {
        console.warn('Legacy login fallback failed:', legacyError);
      }

      const message = String(error.message || '');
      const normalizedMessage = message.toLowerCase();
      const isInvalidCredentials = normalizedMessage.includes('invalid login credentials');
      const isTimeout = error?.name === 'TimeoutError' || normalizedMessage.includes('timed out');

      const err = new Error(
        isInvalidCredentials
          ? 'Incorrect email or password'
          : isTimeout
            ? 'Login is taking too long. Please check network and try again.'
            : message
      );
      err.name = 'SupabaseAuthError';
      throw err;
    }

    const accessToken = data?.session?.access_token || null;
    await setAccessToken(accessToken);
    await setBackendAuthActive(false);
    await setSupabaseUser(data?.user || null);

    // Start backend profile fetch immediately, but cap login wait time for faster navigation.
    const backendProfilePromise = fetchBackendProfileWithTimeout(5000);
    const backendUser = await Promise.race([
      backendProfilePromise,
      new Promise((resolve) => setTimeout(() => resolve(null), QUICK_PROFILE_WAIT_MS)),
    ]);
    const cachedUser = await getStoredUserMatchingEmail(normalizedCredentials.email);

    // Store user data (backend profile preferred, then cached profile, then Supabase user)
    const user = backendUser || cachedUser || data?.user || null;
    if (user) {
      await storage.setItem('user', JSON.stringify(user));
    }

    // Ensure storage eventually gets freshest backend profile without blocking login.
    backendProfilePromise.then(async (resolvedUser) => {
      if (resolvedUser) {
        await storage.setItem('user', JSON.stringify(resolvedUser));
      }
    });

    console.log('Login success latency(ms):', Date.now() - loginStartedAt);

    return { access_token: accessToken, user };
  },

  /**
   * Send password reset email via Supabase Auth (HTTP API)
   */
  async requestPasswordReset(email, redirectTo) {
    const normalizedEmail = normalizeEmail(email);
    const { error } = await supabase.auth.resetPasswordForEmail(normalizedEmail, {
      redirectTo,
    });

    if (error) {
      const err = new Error(error.message || 'Failed to send password reset link');
      err.name = 'SupabaseAuthError';
      throw err;
    }

    return { success: true };
  },

  /**
   * Check if a recovery session exists (from password reset link)
   */
  async hasRecoverySession() {
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      return false;
    }
    return Boolean(data?.session?.access_token);
  },

  /**
   * Update password for current Supabase session (recovery/session required)
   */
  async updatePassword(newPassword) {
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    if (error) {
      const err = new Error(error.message || 'Failed to update password');
      err.name = 'SupabaseAuthError';
      throw err;
    }

    // Wait for remote sign-out to finish so it cannot invalidate the next login.
    await this.logout({ waitForRemoteSignOut: true, skipBackup: true });
    return { success: true };
  },

  /**
   * Register new user
   */
  async register(data) {
    const { data: authData, error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        data: {
          name: data.name,
          apartment_number: data.apartment_number,
          phone_number: data.phone_number || '',
        },
      },
    });

    if (error) {
      const rawMessage = String(error.message || '');
      const normalized = rawMessage.toLowerCase();
      let friendlyMessage = rawMessage;
      if (normalized.includes('email rate limit exceeded') || normalized.includes('too many requests')) {
        friendlyMessage = 'Too many signup attempts from this IP/email. Please wait 5-10 minutes and try again.';
      }
      const err = new Error(friendlyMessage);
      err.name = 'SupabaseAuthError';
      throw err;
    }

    const accessToken = authData?.session?.access_token || null;
    await setAccessToken(accessToken);
    await setBackendAuthActive(false);
    await setSupabaseUser(authData?.user || null);

    // Create or update backend profile
    let backendUser = null;
    try {
      const response = await api.post('/auth/register', data);
      backendUser = response.data?.user || response.data;
    } catch (backendError) {
      const detail = backendError.response?.data?.detail || backendError.message;
      // If already exists, try to fetch profile
      if (detail && String(detail).toLowerCase().includes('already registered')) {
        try {
          const response = await api.get('/auth/me');
          backendUser = response.data;
        } catch (fetchError) {
          console.warn('Failed to fetch backend profile after signup:', fetchError);
        }
      } else {
        console.warn('Backend profile creation failed:', backendError);
      }
    }

    // If profile creation response did not include user, do a short non-blocking lookup.
    if (!backendUser) {
      backendUser = await fetchBackendProfileWithTimeout(5000);
    }

    // Store token and user data
    const user = backendUser || authData?.user || null;
    if (user) {
      await storage.setItem('user', JSON.stringify(user));
    }

    return { access_token: accessToken, user };
  },

  /**
   * Register a new society with its first super admin (backend onboarding)
   */
  async registerSociety(data) {
    const payload = {
      temple_name: data?.society_name,
      trust_name: data?.society_name,
      temple_slug: String(data?.society_name || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 120),
      address: data?.society_address || undefined,
      admin_full_name: data?.admin_name,
      admin_email: data?.admin_email,
      admin_phone: data?.admin_phone || undefined,
    };
    const response = await api.post('/onboarding-requests/register', payload, {
      skipAuthRedirect: true,
    });
    return response.data;
  },

  /**
   * Logout user
   */
  async logout(options = {}) {
    const { waitForRemoteSignOut = false, skipBackup = false } = options;

    // Clear the local session first so the UI can navigate immediately.
    const backupPromise = skipBackup
      ? Promise.resolve()
      : api.post('/database/backup-on-logout', null, {
          timeout: 3000,
          skipAuthRedirect: true,
        }).catch((error) => {
          console.warn('Backup on logout failed:', error);
        });

    const signOutPromise = supabase.auth.signOut().catch((error) => {
      console.warn('Supabase sign out failed:', error);
    });

    await clearStoredAuthState();

    if (waitForRemoteSignOut) {
      await Promise.allSettled([backupPromise, signOutPromise]);
      return;
    }

    void Promise.allSettled([backupPromise, signOutPromise]);
  },

  /**
   * Check if user is authenticated
   */
  async isAuthenticated() {
    const token = await storage.getItem('access_token');
    return !!token;
  },

  /**
   * Get current user from storage
   */
  async getCurrentUser() {
    try {
      // First, try to get user from storage (fast, no API call)
      const userStr = await storage.getItem('user');
      if (userStr) {
        try {
          const user = JSON.parse(userStr);
          // Validate that user object has required fields
          if (user && (user.email || user.id || user.username)) {
            return user;
          }
        } catch (parseError) {
          console.warn('Failed to parse stored user data:', parseError);
          // Continue to try API fetch
        }
      }

      // Only try to fetch from API if we have a token but no user in storage
      const token = await storage.getItem('access_token');
      if (!token) {
        return null;
      }

      // If not in storage but have token, try to fetch from API with timeout
      try {
        const response = await Promise.race([
          api.get(BACKEND_PROFILE_ENDPOINT, { skipAuthRedirect: true }),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Request timeout')), 3000)
          )
        ]);
        const user = response.data;
        if (user) {
          await storage.setItem('user', JSON.stringify(user));
          return user;
        }
        return null;
      } catch (apiError) {
        console.warn('Could not fetch user from API:', apiError.message);
        // Fall back to Supabase user
        const supaUser = await storage.getItem('supabase_user');
        if (supaUser) {
          try {
            return JSON.parse(supaUser);
          } catch (parseError) {
            return null;
          }
        }
        return null;
      }
    } catch (error) {
      console.error('Error getting current user:', error);
      // Don't logout on error - let the app handle it
      return null;
    }
  },

  /**
   * Get stored access token
   */
  async getToken() {
    return await storage.getItem('access_token');
  },
  /**
   * Update stored user data (after profile update)
   */
  async updateStoredUser(userData) {
    try {
      await storage.setItem('user', JSON.stringify(userData));
    } catch (error) {
      console.error('Error updating stored user:', error);
    }
  },
};



