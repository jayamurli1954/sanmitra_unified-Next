import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Grid,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import Layout from '../components/Layout';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';
import { getAccessToken } from '../utils/authStorage';
import { ACTIVE_TEMPLE_EVENT, getActiveTempleId } from '../utils/activeTemple';

const REQUIRED_OPENAPI_PATHS = [
  '/api/v1/onboarding-requests/{request_id}/resend-credentials',
  '/api/v1/sevas/bookings/quick-ticket',
  '/api/v1/upi-payments/quick-log',
  '/api/v1/public/temples/{temple_id}/upi-intent',
  '/api/v1/devotees/autofill/by-mobile/{phone}',
  '/api/v1/upi-payments/config',
];

const CHECK_DEFS = [
  { key: 'backend_health', label: 'Backend Reachability (/health)' },
  { key: 'openapi_paths', label: 'Required API Paths In OpenAPI' },
  { key: 'resend_route_method', label: 'Resend Credentials Route Reachability' },
  { key: 'quick_ticket_method', label: 'Quick Ticket Route Reachability' },
  { key: 'upi_quick_log_method', label: 'UPI Quick Log Route Reachability' },
  { key: 'upi_config', label: 'UPI Config API (Auth Route)' },
  { key: 'public_upi_intent', label: 'Public UPI Intent (Active Temple)' },
  { key: 'mobile_autofill', label: 'Mobile Autofill Lookup (Optional Input)' },
];

const STATUS_CHIP_PROPS = {
  idle: { color: 'default', label: 'Not Run' },
  running: { color: 'info', label: 'Running' },
  pass: { color: 'success', label: 'Pass' },
  warn: { color: 'warning', label: 'Warning' },
  fail: { color: 'error', label: 'Fail' },
};

const createInitialChecks = () => CHECK_DEFS.map((check) => ({
  ...check,
  status: 'idle',
  detail: 'Not run yet.',
}));

const trimMessage = (value, max = 240) => {
  const text = String(value || '').trim();
  if (!text) return '';
  return text.length > max ? `${text.slice(0, max)}...` : text;
};

const getDetailFromPayload = (payload) => {
  if (!payload) return '';
  if (typeof payload?.detail === 'string') return payload.detail;
  if (typeof payload?.message === 'string') return payload.message;
  return '';
};

async function readResponsePayload(response) {
  try {
    const parsed = await response.clone().json();
    return parsed;
  } catch (_jsonErr) {
    try {
      const txt = await response.clone().text();
      return txt ? { detail: txt } : null;
    } catch (_textErr) {
      return null;
    }
  }
}

function ImplementationChecks() {
  const [checks, setChecks] = useState(createInitialChecks);
  const [running, setRunning] = useState(false);
  const [lastRunAt, setLastRunAt] = useState(null);
  const [mobileInput, setMobileInput] = useState('');
  const [activeTempleId, setActiveTempleId] = useState(() => getActiveTempleId());


  useEffect(() => {
    const syncActiveTemple = (event) => {
      const value = Number.parseInt(String(event?.detail?.templeId || ''), 10);
      if (Number.isInteger(value) && value > 0) {
        setActiveTempleId(value);
        return;
      }
      setActiveTempleId(getActiveTempleId());
    };

    window.addEventListener(ACTIVE_TEMPLE_EVENT, syncActiveTemple);
    return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, syncActiveTemple);
  }, []);
  const setCheckStatus = (key, patch) => {
    setChecks((prev) => prev.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  };

  const startCheck = (key) => setCheckStatus(key, { status: 'running', detail: 'Running...' });

  const markPass = (key, detail) => setCheckStatus(key, { status: 'pass', detail: trimMessage(detail) || 'Check passed.' });
  const markWarn = (key, detail) => setCheckStatus(key, { status: 'warn', detail: trimMessage(detail) || 'Needs attention.' });
  const markFail = (key, detail) => setCheckStatus(key, { status: 'fail', detail: trimMessage(detail) || 'Check failed.' });

  const checkBackendHealth = async () => {
    const key = 'backend_health';
    startCheck(key);
    try {
      const response = await fetchWithApiFallback('/health', { method: 'GET' }, { timeoutMs: 12000, maxAttemptsPerOrigin: 2 });
      if (response.ok) {
        markPass(key, `HTTP ${response.status}`);
        return;
      }
      const payload = await readResponsePayload(response);
      markFail(key, `HTTP ${response.status}. ${getDetailFromPayload(payload) || 'Unexpected response.'}`);
    } catch (error) {
      markFail(key, error?.message || 'Unable to reach backend.');
    }
  };

  const checkOpenApiPaths = async () => {
    const key = 'openapi_paths';
    startCheck(key);
    try {
      const response = await fetchWithApiFallback('/openapi.json', { method: 'GET' }, { timeoutMs: 15000, maxAttemptsPerOrigin: 2 });
      if (!response.ok) {
        const payload = await readResponsePayload(response);
        markFail(key, `HTTP ${response.status}. ${getDetailFromPayload(payload) || 'Could not read OpenAPI.'}`);
        return;
      }
      const payload = await response.json();
      const paths = payload?.paths || {};
      const missing = REQUIRED_OPENAPI_PATHS.filter((path) => !Object.prototype.hasOwnProperty.call(paths, path));
      if (missing.length > 0) {
        markFail(key, `Missing paths: ${missing.join(', ')}`);
        return;
      }
      markPass(key, `All ${REQUIRED_OPENAPI_PATHS.length} required paths detected.`);
    } catch (error) {
      markFail(key, error?.message || 'Unable to verify OpenAPI paths.');
    }
  };

  const checkPostRouteReachability = async (key, path) => {
    startCheck(key);
    const token = getAccessToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    try {
      const response = await fetchWithApiFallback(path, { method: 'GET', headers }, { timeoutMs: 12000, maxAttemptsPerOrigin: 2 });
      const payload = await readResponsePayload(response);
      if (response.status === 405) {
        markPass(key, 'Route exists (GET rejected as expected for POST-only route).');
        return;
      }
      if (response.status === 401 || response.status === 403) {
        markWarn(key, `Route reachable but auth denied (HTTP ${response.status}). ${getDetailFromPayload(payload)}`);
        return;
      }
      if (response.status === 404) {
        markFail(key, 'Route not found (HTTP 404).');
        return;
      }
      if (response.ok) {
        markWarn(key, `Unexpected HTTP ${response.status}; route responded to GET.`);
        return;
      }
      markWarn(key, `HTTP ${response.status}. ${getDetailFromPayload(payload) || 'Needs review.'}`);
    } catch (error) {
      markFail(key, error?.message || 'Could not verify route reachability.');
    }
  };

  const checkUpiConfig = async () => {
    const key = 'upi_config';
    startCheck(key);

    const token = getAccessToken();
    if (!token) {
      markWarn(key, 'No access token found. Please login again and rerun.');
      return;
    }

    try {
      const response = await fetchWithApiFallback('/api/v1/upi-payments/config', {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` },
      }, { timeoutMs: 12000, maxAttemptsPerOrigin: 2 });
      const payload = await readResponsePayload(response);

      if (response.status === 200) {
        const hasExpectedField = payload && Object.prototype.hasOwnProperty.call(payload, 'upi_public_enabled');
        if (!hasExpectedField) {
          markWarn(key, 'API returned HTTP 200 but expected UPI config fields were not found.');
          return;
        }
        markPass(key, `HTTP 200. Public UPI enabled: ${Boolean(payload.upi_public_enabled)}`);
        return;
      }

      if (response.status === 401 || response.status === 403) {
        markWarn(key, `Access denied (HTTP ${response.status}). ${getDetailFromPayload(payload)}`);
        return;
      }

      markFail(key, `HTTP ${response.status}. ${getDetailFromPayload(payload) || 'Failed to read UPI config.'}`);
    } catch (error) {
      markFail(key, error?.message || 'Could not load UPI config.');
    }
  };

  const checkPublicUpiIntent = async () => {
    const key = 'public_upi_intent';
    startCheck(key);

    if (!activeTempleId) {
      markWarn(key, 'No active temple selected. Select a temple first, then rerun checks.');
      return;
    }

    try {
      const response = await fetchWithApiFallback(
        `/api/v1/public/temples/${activeTempleId}/upi-intent?amount=1&purpose=HealthCheck&reference=MM-UICHECK`,
        { method: 'GET' },
        { timeoutMs: 12000, maxAttemptsPerOrigin: 2 }
      );
      const payload = await readResponsePayload(response);
      const detail = (getDetailFromPayload(payload) || '').toLowerCase();

      if (response.status === 200 && payload?.intent_uri) {
        markPass(key, 'Intent URI generated successfully for active temple.');
        return;
      }

      if (response.status === 404 && (detail.includes('not enabled') || detail.includes('not configured'))) {
        markWarn(key, `Feature exists but temple setup is incomplete: ${getDetailFromPayload(payload)}`);
        return;
      }

      if (response.status === 404) {
        markFail(key, `Temple route check failed: ${getDetailFromPayload(payload) || 'Temple not found.'}`);
        return;
      }

      markFail(key, `HTTP ${response.status}. ${getDetailFromPayload(payload) || 'Public UPI intent check failed.'}`);
    } catch (error) {
      markFail(key, error?.message || 'Could not verify public UPI intent route.');
    }
  };

  const checkMobileAutofill = async () => {
    const key = 'mobile_autofill';
    startCheck(key);

    const token = getAccessToken();
    if (!token) {
      markWarn(key, 'No access token found. Please login again and rerun.');
      return;
    }

    const normalized = String(mobileInput || '').replace(/\D/g, '').slice(0, 10);
    if (normalized.length !== 10) {
      markWarn(key, 'Enter a 10-digit mobile number to run this check.');
      return;
    }

    try {
      const response = await fetchWithApiFallback(
        `/api/v1/devotees/autofill/by-mobile/${normalized}`,
        {
          method: 'GET',
          headers: { Authorization: `Bearer ${token}` },
        },
        { timeoutMs: 12000, maxAttemptsPerOrigin: 2 }
      );
      const payload = await readResponsePayload(response);

      if (response.status === 200 && typeof payload?.found === 'boolean') {
        markPass(key, payload.found ? 'Devotee found for mobile (tenant-scoped lookup working).' : 'No devotee found (lookup endpoint reachable and working).');
        return;
      }

      if (response.status === 401 || response.status === 403) {
        markWarn(key, `Access denied (HTTP ${response.status}). ${getDetailFromPayload(payload)}`);
        return;
      }

      markFail(key, `HTTP ${response.status}. ${getDetailFromPayload(payload) || 'Autofill check failed.'}`);
    } catch (error) {
      markFail(key, error?.message || 'Could not verify mobile autofill endpoint.');
    }
  };

  const runAllChecks = async () => {
    if (running) return;

    setRunning(true);
    setChecks(createInitialChecks());

    await checkBackendHealth();
    await checkOpenApiPaths();
    await checkPostRouteReachability('resend_route_method', '/api/v1/onboarding-requests/mm-check/resend-credentials');
    await checkPostRouteReachability('quick_ticket_method', '/api/v1/sevas/bookings/quick-ticket');
    await checkPostRouteReachability('upi_quick_log_method', '/api/v1/upi-payments/quick-log');
    await checkUpiConfig();
    await checkPublicUpiIntent();
    await checkMobileAutofill();

    setLastRunAt(new Date());
    setRunning(false);
  };

  const summary = useMemo(() => {
    const totals = checks.reduce((acc, item) => {
      acc[item.status] = (acc[item.status] || 0) + 1;
      return acc;
    }, {});
    return {
      pass: totals.pass || 0,
      warn: totals.warn || 0,
      fail: totals.fail || 0,
      running: totals.running || 0,
      idle: totals.idle || 0,
    };
  }, [checks]);

  return (
    <Layout>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Implementation Checks
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          One-click verification for current rollout items. These checks are read-only and do not create transactions.
        </Typography>

        <Alert severity="info" sx={{ mb: 2 }}>
          Active Temple ID: {activeTempleId || 'Not selected'}
        </Alert>

        <Paper sx={{ p: 2.5, mb: 2 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Mobile For Autofill Check"
                placeholder="10-digit mobile"
                value={mobileInput}
                onChange={(event) => setMobileInput(event.target.value.replace(/\D/g, '').slice(0, 10))}
                helperText="Optional for endpoint check"
              />
            </Grid>
            <Grid item xs={12} md={8}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                <Button
                  variant="contained"
                  startIcon={running ? <RefreshIcon /> : <PlayArrowIcon />}
                  onClick={runAllChecks}
                  disabled={running}
                >
                  {running ? 'Running Checks...' : 'Run All Checks'}
                </Button>
                <Chip color="success" label={`Pass: ${summary.pass}`} />
                <Chip color="warning" label={`Warn: ${summary.warn}`} />
                <Chip color="error" label={`Fail: ${summary.fail}`} />
                {lastRunAt ? <Chip label={`Last Run: ${lastRunAt.toLocaleString()}`} /> : null}
              </Box>
            </Grid>
          </Grid>
        </Paper>

        <Grid container spacing={2}>
          {checks.map((check) => {
            const chipProps = STATUS_CHIP_PROPS[check.status] || STATUS_CHIP_PROPS.idle;
            return (
              <Grid item xs={12} key={check.key}>
                <Paper sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {check.label}
                    </Typography>
                    <Chip color={chipProps.color} label={chipProps.label} size="small" />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {check.detail}
                  </Typography>
                </Paper>
              </Grid>
            );
          })}
        </Grid>
      </Box>
    </Layout>
  );
}

export default ImplementationChecks;

