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

const getValueFromStores = (...keys) => {
  const localStore = local();
  const sessionStore = session();
  for (const key of keys) {
    const localValue = localStore?.getItem(key);
    if (localValue) {
      return localValue;
    }
    const sessionValue = sessionStore?.getItem(key);
    if (sessionValue) {
      return sessionValue;
    }
  }
  return null;
};

const writeValueToStores = (key, value) => {
  const localStore = local();
  const sessionStore = session();
  if (value === null || value === undefined || value === '') {
    localStore?.removeItem(key);
    sessionStore?.removeItem(key);
    return;
  }
  localStore?.setItem(key, value);
  sessionStore?.setItem(key, value);
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
  const current = getValueFromStores(ACCESS_TOKEN_KEY, LEGACY_TOKEN_KEY);
  if (!current) {
    return null;
  }
  writeValueToStores(ACCESS_TOKEN_KEY, current);
  removeFromStores(LEGACY_TOKEN_KEY);
  return current;
};

export const getRefreshToken = () => {
  const current = getValueFromStores(REFRESH_TOKEN_KEY, LEGACY_REFRESH_TOKEN_KEY);
  if (!current) {
    return null;
  }
  writeValueToStores(REFRESH_TOKEN_KEY, current);
  removeFromStores(LEGACY_REFRESH_TOKEN_KEY);
  return current;
};

export const hasAccessToken = () => Boolean(getAccessToken());

export const setAccessToken = (token) => {
  writeValueToStores(ACCESS_TOKEN_KEY, token);
  removeFromStores(LEGACY_TOKEN_KEY);
};

export const setRefreshToken = (token) => {
  writeValueToStores(REFRESH_TOKEN_KEY, token || null);
  removeFromStores(LEGACY_REFRESH_TOKEN_KEY);
};

export const readStoredUser = () => {
  const current = getValueFromStores(USER_KEY, LEGACY_USER_KEY);
  if (current) {
    try {
      const parsed = JSON.parse(current) || {};
      writeValueToStores(USER_KEY, JSON.stringify(parsed));
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
  writeValueToStores(USER_KEY, serialized);
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
