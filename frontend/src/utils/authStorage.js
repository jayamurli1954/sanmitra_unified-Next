const ACCESS_TOKEN_KEY = 'mm_access_token_v1';
const REFRESH_TOKEN_KEY = 'mm_refresh_token_v1';
const USER_KEY = 'mm_current_user_v1';
const LEGACY_TOKEN_KEY = 'token';
const LEGACY_REFRESH_TOKEN_KEY = 'refresh_token';
const LEGACY_USER_KEY = 'user';

const safeStorage = (storage) => {
  try {
    return storage;
  } catch (error) {
    return null;
  }
};

const session = () => safeStorage(window.sessionStorage);
const local = () => safeStorage(window.localStorage);

const readSessionFirst = (...keys) => {
  const sessionStore = session();
  const localStore = local();
  for (const key of keys) {
    const sessionValue = sessionStore?.getItem(key);
    if (sessionValue) {
      return sessionValue;
    }
    const localValue = localStore?.getItem(key);
    if (localValue) {
      // Legacy compatibility: migrate localStorage auth values into session storage.
      sessionStore?.setItem(key, localValue);
      localStore?.removeItem(key);
      return localValue;
    }
  }
  return null;
};

const writeValueToSession = (key, value) => {
  const sessionStore = session();
  const localStore = local();
  if (value === null || value === undefined || value === '') {
    sessionStore?.removeItem(key);
    localStore?.removeItem(key);
    return;
  }
  sessionStore?.setItem(key, value);
  localStore?.removeItem(key);
};

const removeFromStores = (...keys) => {
  const localStore = local();
  const sessionStore = session();
  keys.forEach((key) => {
    localStore?.removeItem(key);
    sessionStore?.removeItem(key);
  });
};

export const getAccessToken = () => {
  const current = readSessionFirst(ACCESS_TOKEN_KEY, LEGACY_TOKEN_KEY);
  if (!current) {
    return null;
  }
  writeValueToSession(ACCESS_TOKEN_KEY, current);
  removeFromStores(LEGACY_TOKEN_KEY);
  return current;
};

export const getRefreshToken = () => {
  const current = readSessionFirst(REFRESH_TOKEN_KEY, LEGACY_REFRESH_TOKEN_KEY);
  if (!current) {
    return null;
  }
  writeValueToSession(REFRESH_TOKEN_KEY, current);
  removeFromStores(LEGACY_REFRESH_TOKEN_KEY);
  return current;
};

export const hasAccessToken = () => Boolean(getAccessToken());

export const decodeJwtPayload = (token) => {
  try {
    const [, payloadSegment] = String(token || '').split('.');
    if (!payloadSegment) return null;

    const normalized = payloadSegment.replace(/-/g, '+').replace(/_/g, '/');
    const padding = '='.repeat((4 - (normalized.length % 4)) % 4);
    const decoded = window.atob(normalized + padding);
    return JSON.parse(decoded);
  } catch (error) {
    return null;
  }
};

export const readAccessTokenClaims = () => decodeJwtPayload(getAccessToken());

export const setAccessToken = (token) => {
  writeValueToSession(ACCESS_TOKEN_KEY, token);
  removeFromStores(LEGACY_TOKEN_KEY);
};

export const setRefreshToken = (token) => {
  writeValueToSession(REFRESH_TOKEN_KEY, token || null);
  removeFromStores(LEGACY_REFRESH_TOKEN_KEY);
};

export const readStoredUser = () => {
  const current = readSessionFirst(USER_KEY, LEGACY_USER_KEY);
  if (current) {
    try {
      const parsed = JSON.parse(current) || {};
      writeValueToSession(USER_KEY, JSON.stringify(parsed));
      removeFromStores(LEGACY_USER_KEY);
      return parsed;
    } catch (error) {
      removeFromStores(USER_KEY, LEGACY_USER_KEY);
    }
  }

  return {};
};

export const writeStoredUser = (user) => {
  const serialized = JSON.stringify(user || {});
  writeValueToSession(USER_KEY, serialized);
  removeFromStores(LEGACY_USER_KEY);
};

export const clearStoredUser = () => {
  removeFromStores(USER_KEY, LEGACY_USER_KEY);
};

export const clearAuthSession = () => {
  removeFromStores(
    ACCESS_TOKEN_KEY,
    LEGACY_TOKEN_KEY,
    REFRESH_TOKEN_KEY,
    LEGACY_REFRESH_TOKEN_KEY,
    USER_KEY,
    LEGACY_USER_KEY
  );
};
