import { clearAuthSession } from './authStorage';

export const TENANT_INACTIVE_PATH = '/tenant-inactive';
const TENANT_INACTIVE_REASON_KEY = 'mm_tenant_inactive_reason_v1';

const toMessage = (value) => {
  if (typeof value === 'string') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((entry) => toMessage(entry)).filter(Boolean).join('; ');
  }
  if (value && typeof value === 'object') {
    if (typeof value.detail === 'string') {
      return value.detail;
    }
    if (typeof value.message === 'string') {
      return value.message;
    }
  }
  return '';
};

export const isTenantInactiveMessage = (message) => (
  String(message || '').toLowerCase().includes('tenant is inactive')
);

export const isTenantInactivePayload = (payload) => isTenantInactiveMessage(toMessage(payload));

export const readTenantInactiveReason = () => {
  if (typeof window === 'undefined') {
    return 'Tenant is inactive';
  }
  return window.sessionStorage.getItem(TENANT_INACTIVE_REASON_KEY) || 'Tenant is inactive';
};

export const clearTenantInactiveReason = () => {
  if (typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.removeItem(TENANT_INACTIVE_REASON_KEY);
};

export const handleTenantInactive = (message = 'Tenant is inactive') => {
  if (typeof window === 'undefined') {
    return;
  }

  window.sessionStorage.setItem(TENANT_INACTIVE_REASON_KEY, String(message || 'Tenant is inactive'));
  clearAuthSession();
  window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { clear: true, reason: 'tenant_inactive' } }));

  if (window.location.pathname !== TENANT_INACTIVE_PATH) {
    window.location.href = TENANT_INACTIVE_PATH;
  }
};
