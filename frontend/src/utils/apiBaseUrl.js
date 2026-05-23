import { buildActiveTempleHeaders } from './activeTemple';
import { handleTenantInactive, isTenantInactivePayload } from './tenantInactive';

const LOCAL_API_BASE_URL = 'http://localhost:8000';
const PRODUCTION_FALLBACK_API_BASE_URL = (
  process.env.REACT_APP_FALLBACK_API_URL ||
  process.env.REACT_APP_API_URL ||
  'https://sanmitra-unified-next-staging-sg.onrender.com'
)
  .trim()
  .replace(/\/$/, '');
const RETIRED_API_HOSTS = new Set(['mandirmitra-backend.onrender.com']);
const TRANSIENT_BACKEND_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524]);

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isLocalHostname(hostname = '') {
  const host = String(hostname || '').toLowerCase();
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

function isLocalUrl(url = '') {
  try {
    const parsed = new URL(url);
    return isLocalHostname(parsed.hostname);
  } catch (_err) {
    return /^https?:\/\/(localhost|127\.0\.0\.1|::1)(:\d+)?$/i.test(String(url || '').trim());
  }
}

function isBrowserLocal() {
  if (typeof window === 'undefined') return false;
  return isLocalHostname(window.location.hostname);
}

function getConfiguredBaseUrl() {
  const rawConfiguredBaseUrl = (process.env.REACT_APP_API_URL || '').trim().replace(/\/$/, '');
  if (!rawConfiguredBaseUrl) {
    return '';
  }

  try {
    const parsed = new URL(rawConfiguredBaseUrl);
    if (RETIRED_API_HOSTS.has(parsed.hostname.toLowerCase())) {
      return '';
    }
  } catch (_error) {
    // If URL parsing fails, return as-is and let callers handle errors.
  }

  return rawConfiguredBaseUrl;
}

function isRetryableNetworkError(error) {
  if (!error) return false;

  if (error?.name === 'AbortError') {
    return true;
  }

  if (String(error?.name || '').toLowerCase() === 'typeerror') {
    return true;
  }

  if (error instanceof TypeError) {
    return true;
  }

  const message = String(error?.message || '').toLowerCase();
  return (
    message.includes('failed to fetch') ||
    message.includes('networkerror') ||
    message.includes('network request failed') ||
    message.includes('load failed') ||
    message.includes('fetch failed')
  );
}

async function warmBackend(preferDirect = false) {
  try {
    await fetch(buildApiUrl('/health', { preferDirect }), {
      method: 'GET',
      mode: 'no-cors',
      cache: 'no-store',
    });
  } catch (_error) {
    // Ignore warm-up failures; retries will continue.
  }
}

export function getApiBaseUrl(options = {}) {
  const { preferDirect = false } = options;
  const configuredBaseUrl = getConfiguredBaseUrl();
  const browserLocal = isBrowserLocal();

  // Direct mode is used for explicit fallback attempts. In production-like hosts,
  // always route to a reachable public backend origin.
  if (preferDirect) {
    if (!browserLocal) {
      return PRODUCTION_FALLBACK_API_BASE_URL;
    }
    return configuredBaseUrl || LOCAL_API_BASE_URL;
  }

  if (configuredBaseUrl) {
    // Ignore localhost API URL when the app is served from non-localhost origins
    // (common accidental production build misconfiguration).
    if (!browserLocal && isLocalUrl(configuredBaseUrl)) {
      return PRODUCTION_FALLBACK_API_BASE_URL;
    }
    return configuredBaseUrl;
  }

  if (browserLocal) {
    return LOCAL_API_BASE_URL;
  }

  return PRODUCTION_FALLBACK_API_BASE_URL;
}

export function buildApiUrl(path, options = {}) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl(options)}${normalizedPath}`;
}

async function maybeHandleTenantInactiveResponse(response) {
  if (!response || response.status !== 403) {
    return;
  }

  try {
    const payload = await response.clone().json();
    if (!isTenantInactivePayload(payload)) {
      return;
    }

    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Tenant is inactive';
    handleTenantInactive(detail);
  } catch (_error) {
    // Ignore parse errors; caller will handle response as usual.
  }
}

export async function fetchWithApiFallback(path, init = {}, options = {}) {
  const {
    timeoutMs = 15000,
    maxAttemptsPerOrigin = 3,
    retryDelayMs = 1200,
  } = options;
  const primaryUrl = buildApiUrl(path);
  const fallbackUrl = buildApiUrl(path, { preferDirect: true });

  // When running on localhost, don't use fallback mechanism - always use primary URL
  const isLocalDevelopment = isBrowserLocal();
  const targets = (primaryUrl === fallbackUrl || isLocalDevelopment)
    ? [{ url: primaryUrl, preferDirect: false }]
    : [{ url: primaryUrl, preferDirect: false }, { url: fallbackUrl, preferDirect: true }];

  let lastError = null;
  for (const target of targets) {
    const { url, preferDirect } = target;
    for (let attempt = 1; attempt <= maxAttemptsPerOrigin; attempt += 1) {
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), timeoutMs);

      try {
        const mergedHeaders = buildActiveTempleHeaders(init.headers || {});
        const response = await fetch(url, { ...init, headers: mergedHeaders, signal: controller.signal });
        await maybeHandleTenantInactiveResponse(response);

        if (!TRANSIENT_BACKEND_STATUS_CODES.has(response.status)) {
          return response;
        }

        lastError = new Error(
          `Backend is temporarily unavailable (${response.status}). Retrying...`
        );
      } catch (error) {
        if (isRetryableNetworkError(error)) {
          lastError = new Error(
            'Cannot reach backend yet. Retrying...'
          );
        } else {
          lastError = error;
          throw error;
        }
      } finally {
        window.clearTimeout(timer);
      }

      if (attempt < maxAttemptsPerOrigin) {
        await warmBackend(preferDirect);
        await delay(retryDelayMs * attempt);
      }
    }
  }
  const retryExhaustedMessage = String(lastError?.message || '').toLowerCase();
  if (
    retryExhaustedMessage.includes('temporarily unavailable') ||
    retryExhaustedMessage.includes('cannot reach backend yet') ||
    retryExhaustedMessage.includes('retrying')
  ) {
    throw new Error(
      'Cannot connect to backend server right now. Please check backend status and retry.'
    );
  }

  throw lastError || new Error('Unable to reach backend after retries');
}
