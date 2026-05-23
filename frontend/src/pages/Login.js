import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Link,
  Divider,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { IconButton, InputAdornment } from '@mui/material';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';
import { setAccessToken, setRefreshToken, writeStoredUser } from '../utils/authStorage';
import { clearTenantInactiveReason } from '../utils/tenantInactive';
import { emitActiveTempleChanged, getActiveTempleId, setActiveTempleId } from '../utils/activeTemple';
import AppInstallButton from '../components/AppInstallButton';

const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';
const PLATFORM_ADMIN_ROLES = new Set(['super_admin', 'superadmin', 'platform_owner', 'platform_admin']);

const normalizeCurrentUser = (userData, email) => ({
  id: userData?.id || userData?.sub,
  email: userData?.email || email,
  full_name: userData?.full_name || '',
  name: userData?.full_name || userData?.email || email.split('@')[0],
  role: userData?.system_role || userData?.role || 'temple_manager',
  system_role: userData?.system_role || userData?.role || 'temple_manager',
  role_key: userData?.role_key,
  role_label: userData?.role_label,
  phone: userData?.phone || '',
  module_permissions: userData?.module_permissions || {},
  action_permissions: userData?.action_permissions || {},
  is_superuser: Boolean(userData?.is_superuser),
  must_change_password: Boolean(userData?.must_change_password),
});

const parseErrorMessage = async (response, fallbackMessage) => {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === 'string' && payload.detail) {
      return payload.detail;
    }
    if (typeof payload?.message === 'string' && payload.message) {
      return payload.message;
    }
  } catch (_error) {
    // ignore parse failures, fallback message below
  }
  return fallbackMessage;
};

const decodeJwtPayload = (token) => {
  try {
    const [, payloadSegment] = String(token || '').split('.');
    if (!payloadSegment) return null;

    const normalized = payloadSegment.replace(/-/g, '+').replace(/_/g, '/');
    const padding = '='.repeat((4 - (normalized.length % 4)) % 4);
    const decoded = window.atob(normalized + padding);
    return JSON.parse(decoded);
  } catch (_error) {
    return null;
  }
};

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { t } = useTranslation();

  const googleButtonRef = useRef(null);

  const googleClientId = (process.env.REACT_APP_GOOGLE_CLIENT_ID || '').trim();
  const defaultGoogleTenantId = (process.env.REACT_APP_DEFAULT_TENANT_ID || '').trim() || null;
  const isSubmitting = loading || googleLoading;

  useEffect(() => {
    clearTenantInactiveReason();

    // Warm backend early so first login has better responsiveness.
    fetchWithApiFallback('/health', {
      method: 'GET',
      cache: 'no-store',
    }, {
      timeoutMs: 5000,
      maxAttemptsPerOrigin: 1,
      retryDelayMs: 800,
    }).catch(() => {
      // Ignore here; explicit login action handles user-facing errors.
    });
  }, []);

  const handleClickShowPassword = () => setShowPassword(!showPassword);

  const completeLoginSession = useCallback(async (tokenData, fallbackEmail = '') => {
    setAccessToken(tokenData.access_token);
    if (tokenData.refresh_token) {
      setRefreshToken(tokenData.refresh_token);
    }

    const profileResponse = await fetchWithApiFallback('/api/v1/users/me', {
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
      },
    }, { timeoutMs: 12000 });

    let currentUser = {
      email: fallbackEmail || '',
      name: fallbackEmail ? fallbackEmail.split('@')[0] : 'user',
      role: 'temple_manager',
      system_role: 'temple_manager',
      is_superuser: false,
      module_permissions: {},
      action_permissions: {},
    };

    if (profileResponse.ok) {
      const profileData = await profileResponse.json();
      currentUser = normalizeCurrentUser(profileData, fallbackEmail || profileData?.email || 'user@local');
    }

    const resolvedRole = String(currentUser.system_role || currentUser.role || '').toLowerCase();
    if (currentUser.is_superuser || PLATFORM_ADMIN_ROLES.has(resolvedRole)) {
      const storedTempleId = getActiveTempleId();
      const templesResponse = await fetchWithApiFallback('/api/v1/temples/', {
        headers: {
          Authorization: `Bearer ${tokenData.access_token}`,
        },
      }, { timeoutMs: 12000 });

      if (templesResponse.ok) {
        const templesPayload = await templesResponse.json();
        const temples = Array.isArray(templesPayload) ? templesPayload : [];
        const demoEditableTemples = temples.filter((temple) => Boolean(temple?.platform_can_write));
        const selectableTemples = demoEditableTemples.length > 0 ? demoEditableTemples : temples;
        const hasStoredTemple = selectableTemples.some((temple) => Number(temple?.id) === Number(storedTempleId));

        if (hasStoredTemple && storedTempleId) {
          const storedTemple = selectableTemples.find((temple) => Number(temple?.id) === Number(storedTempleId));
          setActiveTempleId(storedTempleId, storedTemple?.tenant_id);
          emitActiveTempleChanged(storedTempleId, storedTemple?.tenant_id);
        } else if (selectableTemples.length > 0 && selectableTemples[0]?.id) {
          const preferredTempleId = Number(selectableTemples[0].id);
          setActiveTempleId(preferredTempleId, selectableTemples[0]?.tenant_id);
          emitActiveTempleChanged(preferredTempleId, selectableTemples[0]?.tenant_id);
        } else {
          setActiveTempleId(null);
          emitActiveTempleChanged(null);
        }
      } else {
        setActiveTempleId(null);
        emitActiveTempleChanged(null);
      }
    }

    writeStoredUser(currentUser);
    window.dispatchEvent(new CustomEvent('user-profile-updated', { detail: currentUser }));

    if (currentUser.must_change_password) {
      sessionStorage.removeItem('showBrandIntroAfterLogin');
      navigate('/profile', { replace: true });
      return;
    }

    sessionStorage.setItem('showBrandIntroAfterLogin', '1');
    navigate('/brand-intro', { replace: true });
  }, [navigate]);

  const performPasswordLogin = useCallback(async () => {
    const unifiedResponse = await fetchWithApiFallback('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    }, { timeoutMs: 20000, maxAttemptsPerOrigin: 2, retryDelayMs: 1000 });

    if (unifiedResponse.ok) {
      return unifiedResponse;
    }

    // Keep backward compatibility with legacy backend contract.
    if (![404, 405, 415].includes(unifiedResponse.status)) {
      return unifiedResponse;
    }

    return fetchWithApiFallback('/api/v1/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    }, { timeoutMs: 20000, maxAttemptsPerOrigin: 2, retryDelayMs: 1000 });
  }, [email, password]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let response;
      try {
        response = await performPasswordLogin();
      } catch (loginErr) {
        if (loginErr?.name === 'AbortError') {
          response = await performPasswordLogin();
        } else {
          throw loginErr;
        }
      }

      if (!response.ok) {
        const message = await parseErrorMessage(response, t('login.errors.loginFailed'));
        throw new Error(message);
      }

      const data = await response.json();
      await completeLoginSession(data, email);
    } catch (err) {
      console.error('Login error:', err);
      if (err?.name === 'AbortError') {
        setError(t('login.errors.timedOut'));
      } else if (typeof err?.message === 'string' && err.message.trim()) {
        setError(err.message);
      } else {
        setError(t('login.errors.cannotConnect'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCredentialResponse = useCallback(async (credentialResponse) => {
    const idToken = credentialResponse?.credential;
    if (!idToken) {
      setError(t('login.errors.googleTokenMissing'));
      return;
    }

    setError('');
    setGoogleLoading(true);

    try {
      const response = await fetchWithApiFallback('/api/v1/auth/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_token: idToken,
          tenant_id: defaultGoogleTenantId,
        }),
      }, { timeoutMs: 20000, maxAttemptsPerOrigin: 2, retryDelayMs: 1000 });

      if (!response.ok) {
        const message = await parseErrorMessage(response, t('login.errors.googleLoginFailed'));
        if (response.status === 400 && message.includes('tenant_id is required')) {
          const claims = decodeJwtPayload(idToken) || {};
          const onboardingEmail = String(claims?.email || '').trim().toLowerCase();
          if (onboardingEmail) {
            sessionStorage.setItem('pending_onboarding_email', onboardingEmail);
            navigate(`/register-temple?admin_email=${encodeURIComponent(onboardingEmail)}`);
          } else {
            navigate('/register-temple');
          }
          return;
        }
        throw new Error(message);
      }

      const data = await response.json();
      await completeLoginSession(data);
    } catch (err) {
      console.error('Google login error:', err);
      setError(err.message || t('login.errors.googleLoginFailed'));
    } finally {
      setGoogleLoading(false);
    }
  }, [completeLoginSession, defaultGoogleTenantId, navigate, t]);

  useEffect(() => {
    if (!googleClientId || !googleButtonRef.current) {
      return undefined;
    }

    let cancelled = false;

    const initializeButton = () => {
      if (cancelled || !window.google?.accounts?.id || !googleButtonRef.current) {
        return;
      }

      googleButtonRef.current.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleCredentialResponse,
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: 320,
      });
    };

    if (window.google?.accounts?.id) {
      initializeButton();
      return () => {
        cancelled = true;
      };
    }

    const existingScript = document.querySelector(`script[src="${GOOGLE_SCRIPT_SRC}"]`);
    const handleLoad = () => initializeButton();

    if (existingScript) {
      existingScript.addEventListener('load', handleLoad);
      return () => {
        cancelled = true;
        existingScript.removeEventListener('load', handleLoad);
      };
    }

    const script = document.createElement('script');
    script.src = GOOGLE_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = handleLoad;
    document.head.appendChild(script);

    return () => {
      cancelled = true;
      script.onload = null;
    };
  }, [googleClientId, handleGoogleCredentialResponse]);

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
            <LockOutlinedIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
            <Box
              component="img"
              src="/branding/mandirmitra_logo1.jpg"
              alt="MandirMitra"
              sx={{ width: 120, height: 120, objectFit: 'contain', mt: 0.5 }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {t('login.systemTagline')}
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label={t('login.emailLabel')}
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label={t('login.passwordLabel')}
              type={showPassword ? 'text' : 'password'}
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleClickShowPassword}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, py: 1.5 }}
              disabled={isSubmitting}
            >
              {loading ? <CircularProgress size={24} /> : t('login.signIn')}
            </Button>

            {googleClientId && (
              <>
                <Divider sx={{ my: 2 }}>{t('common.or')}</Divider>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2, minHeight: 44 }}>
                  {googleLoading ? <CircularProgress size={24} /> : <Box ref={googleButtonRef} />}
                </Box>
              </>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 2 }}>
              <Link component="button" type="button" variant="body2" onClick={() => navigate('/register-temple')}>
                {t('login.newTempleRegister')}
              </Link>
              <Link component="button" type="button" variant="body2" onClick={() => navigate('/forgot-password')}>
                {t('login.forgotPassword')}
              </Link>
            </Box>

            <Box
              component="button"
              type="button"
              onClick={() => navigate('/pay')}
              sx={{
                width: '100%', py: 1.2, px: 2, mb: 1,
                bgcolor: '#FFF3E0', border: '1.5px solid #FF9933', borderRadius: 2,
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1,
                '&:hover': { bgcolor: '#FFE0B2' },
                transition: 'background-color 0.2s',
              }}
            >
              <Box component="span" sx={{ fontSize: 18 }}>&#x1F64F;</Box>
              <Box>
                <Typography variant="body2" fontWeight="bold" color="#e65c00" lineHeight={1.2}>
                  Book a Seva / Make a Donation
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  No login required - pay directly to your temple
                </Typography>
              </Box>
            </Box>
            <Box sx={{ mt: 2 }}>
              <AppInstallButton variant="button" color="primary" fullWidth />
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}

export default Login;

