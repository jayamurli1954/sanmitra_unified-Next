import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import AddBusinessIcon from '@mui/icons-material/AddBusiness';
import { Navigate, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Layout from '../components/Layout';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { readStoredUser } from '../utils/authStorage';
import { setActiveTempleId, emitActiveTempleChanged } from '../utils/activeTemple';

const getDisplayName = (temple) => temple?.name || temple?.trust_name || `Temple ${temple?.id || ''}`;
const normalizeName = (value) => String(value || '').trim().toLowerCase();
const getRequestIdCandidates = (request) => {
  const candidates = [
    request?.request_id,
    request?.onboarding_request_id,
    request?.id,
  ]
    .map((value) => String(value || '').trim())
    .filter(Boolean);
  return Array.from(new Set(candidates));
};

const getRequestId = (request) => getRequestIdCandidates(request)[0] || '';

function TempleDirectory() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { showError, showSuccess } = useNotification();
  const [loading, setLoading] = useState(true);
  const [tenantActionKey, setTenantActionKey] = useState('');
  const [resendLoadingRequestId, setResendLoadingRequestId] = useState(null);
  const [temples, setTemples] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [approvalSummary, setApprovalSummary] = useState(null);
  const currentUser = useMemo(() => readStoredUser(), []);
  const isPlatformSuperAdmin = Boolean(currentUser.is_superuser) || currentUser.role === 'super_admin' || currentUser.system_role === 'super_admin';

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError('');
      const templesResponse = await api.get('/api/v1/temples/');
      setTemples(Array.isArray(templesResponse.data) ? templesResponse.data : []);
      if (isPlatformSuperAdmin) {
        const requestsResponse = await api.get('/api/v1/onboarding-requests/');
        setRequests(Array.isArray(requestsResponse.data) ? requestsResponse.data : []);
      } else {
        setRequests([]);
      }
    } catch (err) {
      const message = err.userMessage || err?.response?.data?.detail || t('templeDirectory.messages.loadFailed');
      setLoadError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  }, [isPlatformSuperAdmin, showError, t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDeactivateTemple = async (temple) => {
    const label = getDisplayName(temple);
    const confirmed = window.confirm(t('templeDirectory.deactivateConfirm', { label }));
    if (!confirmed) {
      return;
    }

    const actionKey = `deactivate-${temple.id}`;
    try {
      setTenantActionKey(actionKey);
      await api.post(`/api/v1/temples/${temple.id}/deactivate`);
      showSuccess(t('templeDirectory.messages.deactivated', { label }));
      await fetchData();
    } catch (err) {
      showError(err.userMessage || err?.response?.data?.detail || t('templeDirectory.messages.deactivateFailed'));
    } finally {
      setTenantActionKey('');
    }
  };

  const handleActivateTemple = async (temple) => {
    const label = getDisplayName(temple);
    const confirmed = window.confirm(t('templeDirectory.activateConfirm', { label }));
    if (!confirmed) {
      return;
    }

    const actionKey = `activate-${temple.id}`;
    try {
      setTenantActionKey(actionKey);
      await api.post(`/api/v1/temples/${temple.id}/activate`);
      showSuccess(t('templeDirectory.messages.activated', { label }));
      await fetchData();
    } catch (err) {
      showError(err.userMessage || err?.response?.data?.detail || t('templeDirectory.messages.activateFailed'));
    } finally {
      setTenantActionKey('');
    }
  };

  const handleRemoveTemple = async (temple) => {
    const label = getDisplayName(temple);
    const expectedConfirmation = `DELETE ${temple.id}`;
    const confirmation = window.prompt(t('templeDirectory.removePrompt', { expected: expectedConfirmation, label }));
    if (confirmation === null) {
      return;
    }

    const normalizedConfirmation = String(confirmation || '').trim().replace(/\s+/g, ' ').toUpperCase();
    if (normalizedConfirmation !== expectedConfirmation) {
      showError(t('templeDirectory.confirmationMismatch', { expected: expectedConfirmation }));
      return;
    }

    const actionKey = `remove-${temple.id}`;
    try {
      setTenantActionKey(actionKey);
      await api.delete(`/api/v1/temples/${temple.id}/remove`, {
        data: { confirm_text: expectedConfirmation },
      });
      showSuccess(t('templeDirectory.messages.removed', { label }));
      await fetchData();
    } catch (err) {
      showError(err.userMessage || err?.response?.data?.detail || t('templeDirectory.messages.removeFailed'));
    } finally {
      setTenantActionKey('');
    }
  };

  const handleResendCredentials = async (request, temple) => {
    const requestIds = getRequestIdCandidates(request);
    if (requestIds.length === 0) {
      showError(t('templeDirectory.noApprovedRequest'));
      return;
    }

    const templeLabel = getDisplayName(temple);
    const confirmed = window.confirm(t('templeDirectory.resendConfirm', { label: templeLabel }));
    if (!confirmed) {
      return;
    }

    try {
      setResendLoadingRequestId(requestIds[0]);
      let response = null;
      let lastError = null;
      for (const requestId of requestIds) {
        try {
          response = await api.post(`/api/v1/onboarding-requests/${requestId}/resend-credentials`, {});
          break;
        } catch (error) {
          lastError = error;
          if (error?.response?.status !== 404) {
            throw error;
          }
        }
      }
      if (!response) {
        throw lastError || new Error(t('templeDirectory.messages.resendFailed'));
      }
      setApprovalSummary({ ...(response.data || {}), _action: 'resent' });
      if (response.data?.email_sent) {
        showSuccess(t('templeDirectory.messages.resendSuccess', { email: response.data.admin_email }));
      } else {
        showError(response.data?.email_error || t('templeDirectory.sharePasswordManually'));
      }
      await fetchData();
    } catch (err) {
      showError(err.userMessage || err?.response?.data?.detail || t('templeDirectory.messages.resendFailed'));
    } finally {
      setResendLoadingRequestId(null);
    }
  };

  const handleOpenDemoWorkspace = (temple) => {
    if (!temple?.platform_can_write) {
      showError(t('templeDirectory.demoWorkspaceOnly'));
      return;
    }

    const resolvedTempleId = Number.parseInt(String(temple?.id || temple?.temple_id || ''), 10);
    if (!Number.isInteger(resolvedTempleId) || resolvedTempleId <= 0) {
      showError(t('templeDirectory.invalidTempleId'));
      return;
    }

    setActiveTempleId(resolvedTempleId, temple?.tenant_id);
    emitActiveTempleChanged(resolvedTempleId, temple?.tenant_id);
    navigate('/dashboard');
  };

  if (!isPlatformSuperAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const activeTempleCount = temples.filter((temple) => temple.is_active !== false).length;
  const pendingRequests = requests.filter((request) => ['pending', 'payment_received', 'under_review'].includes(request.status));
  const approvedRequests = requests.filter((request) => request.status === 'approved');
  const approvedRequestByTenant = approvedRequests.reduce((acc, request) => {
    const tenantKey = String(request?.approved_tenant_id || '').trim();
    if (tenantKey && !acc[tenantKey]) {
      acc[tenantKey] = request;
    }
    return acc;
  }, {});
  const approvedRequestByName = approvedRequests.reduce((acc, request) => {
    const key = normalizeName(request?.tenant_name || request?.temple_name || request?.trust_name || '');
    if (key && !acc[key]) {
      acc[key] = request;
    }
    return acc;
  }, {});

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2} sx={{ mb: 3 }}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            <TempleHinduIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            {t('templeDirectory.title')}
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <Button variant="outlined" onClick={() => navigate('/settings')} startIcon={<AddBusinessIcon />}>
              {t('templeDirectory.createDemoTenant')}
            </Button>
            <Button variant="outlined" onClick={() => { setActiveTempleId(null); emitActiveTempleChanged(null); navigate('/settings'); }}>
              {t('templeDirectory.openPlatformConsole')}
            </Button>
          </Stack>
        </Stack>

        {approvalSummary && (
          <Alert severity="success" sx={{ mb: 3 }}>
            {t('templeDirectory.summaryResent', {
                email: approvalSummary.admin_email,
                password: approvalSummary.temporary_password,
                status: approvalSummary.email_sent
                  ? t('templeDirectory.emailSent')
                  : approvalSummary.email_error
                    ? t('templeDirectory.emailFailed', { error: approvalSummary.email_error })
                    : t('templeDirectory.sharePasswordManually')
              })}
          </Alert>
        )}

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, minmax(0, 1fr))' }, gap: 2, mb: 3 }}>
          <Card sx={{ borderLeft: '5px solid #FF9933' }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">{t('templeDirectory.totalOnboarded')}</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>{temples.length}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ borderLeft: '5px solid #2E7D32' }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">{t('templeDirectory.active')}</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>{activeTempleCount}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ borderLeft: '5px solid #1565C0' }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">{t('templeDirectory.pendingApproval')}</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>{pendingRequests.length}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ borderLeft: '5px solid #1565C0' }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">{t('templeDirectory.accessModel')}</Typography>
              <Typography variant="body1" sx={{ mt: 1 }}>{t('templeDirectory.accessModelDescription')}</Typography>
            </CardContent>
          </Card>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        ) : loadError ? (
          <Alert severity="error">{loadError}</Alert>
        ) : (
          <Stack spacing={3}>
            {isPlatformSuperAdmin && (
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                    <PendingActionsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                    {t('templeDirectory.pendingSection')}
                  </Typography>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Tenant onboarding approval is handled in the combined Platform Owner workspace for LegalMitra, MandirMitra, GruhaMitra, and MitraBooks.
                  </Alert>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ xs: 'stretch', sm: 'center' }}>
                    <Button
                      variant="contained"
                      onClick={() => { window.location.href = '/mitrabooks-erp/'; }}
                    >
                      Open Combined Platform Owner Console
                    </Button>
                    <Typography variant="body2" color="text.secondary">
                      {pendingRequests.length} MandirMitra request(s) need platform-owner review.
                    </Typography>
                  </Stack>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                  {t('templeDirectory.onboardedSection')}
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.id')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.templeTrust')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.trustName')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.primaryDeity')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.city')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.state')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.phone')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.email')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.status')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.platformAccess')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{t('templeDirectory.table.verification')}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align="right">{t('templeDirectory.table.action')}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {temples.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={12}>
                            <Alert severity="info">{t('templeDirectory.noOnboarded')}</Alert>
                          </TableCell>
                        </TableRow>
                      ) : (
                        temples.map((temple) => {
                          const tenantKey = String(temple?.tenant_id || '').trim();
                          const nameLookupKey = normalizeName(temple?.name || temple?.temple_name || temple?.trust_name || '');
                          const linkedApprovedRequest = approvedRequestByTenant[tenantKey] || approvedRequestByName[nameLookupKey] || null;
                          const linkedRequestId = getRequestId(linkedApprovedRequest);
                          const hasApprovedRequest = Boolean(linkedApprovedRequest);
                          const resolvedTempleName = normalizeName(getDisplayName(temple));
                          const hasPlaceholderName = resolvedTempleName === 'temple' || resolvedTempleName === 'temple trust';
                          const hasContact = Boolean(temple?.phone || temple?.email);
                          const hasLocation = Boolean(temple?.city || temple?.state);
                          const needsReview = !hasApprovedRequest || hasPlaceholderName || !hasContact || !hasLocation;
                          const resendLabel = !linkedRequestId
                            ? t('templeDirectory.noApprovedRequestAction')
                            : (resendLoadingRequestId === linkedRequestId ? t('templeDirectory.resending') : t('templeDirectory.resendEmail'));
                          const canOpenDemoWorkspace = Boolean(temple.platform_can_write) && temple.is_active !== false;
                          const canRemoveCompletely = Boolean(temple.platform_can_write);
                          return (
                            <TableRow key={temple.id} hover>
                              <TableCell>{temple.id}</TableCell>
                              <TableCell sx={{ fontWeight: 600 }}>{getDisplayName(temple)}</TableCell>
                              <TableCell>{temple.trust_name || t('common.notAvailable')}</TableCell>
                              <TableCell>{temple.primary_deity || t('common.notAvailable')}</TableCell>
                              <TableCell>{temple.city || t('common.notAvailable')}</TableCell>
                              <TableCell>{temple.state || t('common.notAvailable')}</TableCell>
                              <TableCell>{temple.phone || t('common.notAvailable')}</TableCell>
                              <TableCell>{temple.email || t('common.notAvailable')}</TableCell>
                              <TableCell>
                                <Chip size="small" color={temple.is_active === false ? 'default' : 'success'} label={temple.is_active === false ? t('templeDirectory.inactive') : t('templeDirectory.active')} variant={temple.is_active === false ? 'outlined' : 'filled'} />
                              </TableCell>
                              <TableCell>
                                <Chip size="small" color={temple.platform_can_write ? 'warning' : 'default'} label={temple.platform_can_write ? t('templeDirectory.demoEditable') : t('templeDirectory.readOnly')} variant={temple.platform_can_write ? 'filled' : 'outlined'} />
                              </TableCell>
                              <TableCell>
                                <Chip
                                  size="small"
                                  color={needsReview ? 'warning' : 'default'}
                                  label={needsReview ? t('templeDirectory.needsReview') : t('templeDirectory.reviewed')}
                                  variant={needsReview ? 'filled' : 'outlined'}
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="flex-end">
                                  {canOpenDemoWorkspace && (
                                    <Button
                                      size="small"
                                      variant="contained"
                                      onClick={() => handleOpenDemoWorkspace(temple)}
                                    >
                                      {t('templeDirectory.openDemoWorkspace')}
                                    </Button>
                                  )}
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    disabled={!linkedRequestId || resendLoadingRequestId === linkedRequestId}
                                    onClick={() => handleResendCredentials(linkedApprovedRequest, temple)}
                                  >
                                    {resendLabel}
                                  </Button>
                                  {temple.is_active === false ? (
                                    <Button
                                      size="small"
                                      variant="outlined"
                                      color="success"
                                      disabled={tenantActionKey === `activate-${temple.id}`}
                                      onClick={() => handleActivateTemple(temple)}
                                    >
                                      {tenantActionKey === `activate-${temple.id}` ? t('templeDirectory.activating') : t('templeDirectory.activate')}
                                    </Button>
                                  ) : (
                                    <Button
                                      size="small"
                                      variant="outlined"
                                      color="warning"
                                      disabled={tenantActionKey === `deactivate-${temple.id}`}
                                      onClick={() => handleDeactivateTemple(temple)}
                                    >
                                      {tenantActionKey === `deactivate-${temple.id}` ? t('templeDirectory.deactivating') : t('templeDirectory.deactivate')}
                                    </Button>
                                  )}
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    color="error"
                                    disabled={!canRemoveCompletely || tenantActionKey === `remove-${temple.id}`}
                                    onClick={() => {
                                      if (canRemoveCompletely) {
                                        handleRemoveTemple(temple);
                                      }
                                    }}
                                  >
                                    {tenantActionKey === `remove-${temple.id}`
                                      ? t('templeDirectory.removing')
                                      : canRemoveCompletely
                                        ? t('templeDirectory.removeCompletely')
                                        : t('templeDirectory.deleteRequestOnly')}
                                  </Button>
                                </Stack>
                              </TableCell>
                            </TableRow>
                          );
                        })
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Stack>
        )}
      </Box>
    </Layout>
  );
}

export default TempleDirectory;

