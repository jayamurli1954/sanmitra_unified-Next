/**
 * Web-compatible storage with session protection for auth keys.
 * Replaces AsyncStorage for web/desktop.
 */
const AUTH_SESSION_KEYS = new Set(['access_token', 'supabase_user', 'backend_auth_active']);

const canUseStorage = (storage) => {
  try {
    return storage;
  } catch (_error) {
    return null;
  }
};

const localStore = () => canUseStorage(window.localStorage);
const sessionStore = () => canUseStorage(window.sessionStorage);
const isAuthSessionKey = (key) => AUTH_SESSION_KEYS.has(String(key || '').trim());

const storage = {
  async getItem(key) {
    try {
      if (isAuthSessionKey(key)) {
        const session = sessionStore();
        const local = localStore();
        const sessionValue = session?.getItem(key);
        if (sessionValue !== null) {
          return sessionValue;
        }
        const legacyValue = local?.getItem(key);
        if (legacyValue !== null && session) {
          session.setItem(key, legacyValue);
          local.removeItem(key);
        }
        return legacyValue;
      }
      return localStore()?.getItem(key);
    } catch (error) {
      console.error('Storage getItem error:', error);
      return null;
    }
  },

  async setItem(key, value) {
    try {
      if (isAuthSessionKey(key)) {
        sessionStore()?.setItem(key, value);
        localStore()?.removeItem(key);
        return;
      }
      localStore()?.setItem(key, value);
    } catch (error) {
      console.error('Storage setItem error:', error);
    }
  },

  async removeItem(key) {
    try {
      sessionStore()?.removeItem(key);
      localStore()?.removeItem(key);
    } catch (error) {
      console.error('Storage removeItem error:', error);
    }
  },

  async clear() {
    try {
      sessionStore()?.clear();
      localStore()?.clear();
    } catch (error) {
      console.error('Storage clear error:', error);
    }
  },
};

export default storage;

