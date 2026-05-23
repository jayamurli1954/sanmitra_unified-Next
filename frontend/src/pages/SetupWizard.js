import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';

const DEFAULT_INVITE_ROLE_OPTIONS = [
  { role_key: 'treasurer', display_name: 'Treasurer' },
  { role_key: 'counter_clerk', display_name: 'Counter Clerk' },
  { role_key: 'accounts_clerk', display_name: 'Accounts Clerk' },
  { role_key: 'priest_operator', display_name: 'Priest / Temple Operator' },
];

function SetupWizard() {
  const navigate = useNavigate();
  const { showSuccess, showError } = useNotification();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [users, setUsers] = useState([]);
  const [roleOptions, setRoleOptions] = useState(DEFAULT_INVITE_ROLE_OPTIONS);
  const [savingTemple, setSavingTemple] = useState(false);
  const [savingBank, setSavingBank] = useState(false);
  const [savingInvite, setSavingInvite] = useState(false);
  const [templeForm, setTempleForm] = useState({
    name: '',
    trust_name: '',
    primary_deity: '',
    address: '',
    city: '',
    state: '',
    phone: '',
    email: '',
    financial_year_start_month: 4,
    receipt_prefix_donation: 'DON',
    receipt_prefix_seva: 'SEVA',
  });
  const [bankForm, setBankForm] = useState({
    account_name: '',
    bank_name: '',
    branch_name: '',
    account_number: '',
    ifsc_code: '',
    account_type: 'Savings',
    is_primary: true,
    is_active: true,
  });
  const [inviteForm, setInviteForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    role: 'treasurer',
    password: '',
    is_active: true,
  });

  const fetchWizardData = async () => {
    try {
      setLoading(true);
      const [statusRes, templeRes, bankRes, usersRes, roleOptionsRes] = await Promise.allSettled([
        api.get('/api/v1/setup-wizard/status'),
        api.get('/api/v1/temples/'),
        api.get('/api/v1/bank-accounts/'),
        api.get('/api/v1/users/'),
        api.get('/api/v1/role-permissions/assignable'),
      ]);

      if (statusRes.status === 'fulfilled') {
        setStatus(statusRes.value.data);
      }

      if (templeRes.status === 'fulfilled') {
        const temple = Array.isArray(templeRes.value.data) ? templeRes.value.data[0] : templeRes.value.data;
        if (temple) {
          setTempleForm({
            name: temple.name || '',
            trust_name: temple.trust_name || '',
            primary_deity: temple.primary_deity || '',
            address: temple.address || '',
            city: temple.city || '',
            state: temple.state || '',
            phone: temple.phone || '',
            email: temple.email || '',
            financial_year_start_month: temple.financial_year_start_month || 4,
            receipt_prefix_donation: temple.receipt_prefix_donation || 'DON',
            receipt_prefix_seva: temple.receipt_prefix_seva || 'SEVA',
          });
        }
      }

      if (bankRes.status === 'fulfilled') {
        setBankAccounts(bankRes.value.data || []);
      }

      if (usersRes.status === 'fulfilled') {
        setUsers(usersRes.value.data || []);
      }

      if (roleOptionsRes.status === 'fulfilled') {
        setRoleOptions(roleOptionsRes.value.data?.roles || DEFAULT_INVITE_ROLE_OPTIONS);
      }
    } catch (error) {
      console.error('Failed to load setup wizard data', error);
      showError('Failed to load setup wizard');
    } finally {
      setLoading(false);
    }
  };

  // Initial wizard bootstrap happens once on mount; later refreshes are explicit after saves.
  useEffect(() => {
    fetchWizardData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSaveTemple = async () => {
    const resolvedTempleName = (templeForm.name || '').trim();
    const resolvedTrustName = (templeForm.trust_name || '').trim();
    if (!resolvedTempleName && !resolvedTrustName) {
      showError('Fill Temple Name or Trust Name');
      return;
    }

    try {
      setSavingTemple(true);
      await api.put('/api/v1/temples/current', {
        name: resolvedTempleName,
        trust_name: resolvedTrustName || null,
        primary_deity: templeForm.primary_deity || null,
        address: templeForm.address,
        city: templeForm.city,
        state: templeForm.state,
        phone: templeForm.phone,
        email: templeForm.email,
        financial_year_start_month: Number(templeForm.financial_year_start_month),
        receipt_prefix_donation: templeForm.receipt_prefix_donation,
        receipt_prefix_seva: templeForm.receipt_prefix_seva,
      });
      showSuccess('Temple / Trust setup saved');
      await fetchWizardData();
    } catch (error) {
      showError(error?.response?.data?.detail || 'Failed to save temple setup');
    } finally {
      setSavingTemple(false);
    }
  };

  const handleCreateBankAccount = async () => {
    try {
      setSavingBank(true);
      await api.post('/api/v1/bank-accounts/', bankForm);
      showSuccess('Bank account added');
      setBankForm({
        account_name: '',
        bank_name: '',
        branch_name: '',
        account_number: '',
        ifsc_code: '',
        account_type: 'Savings',
        is_primary: true,
        is_active: true,
      });
      await fetchWizardData();
    } catch (error) {
      showError(error?.response?.data?.detail || 'Failed to add bank account');
    } finally {
      setSavingBank(false);
    }
  };

  const handleInviteUser = async () => {
    try {
      setSavingInvite(true);
      await api.post('/api/v1/users/', inviteForm);
      showSuccess('User invited successfully');
      setInviteForm({
        full_name: '',
        email: '',
        phone: '',
        role: 'treasurer',
        password: '',
        is_active: true,
      });
      await fetchWizardData();
    } catch (error) {
      showError(error?.response?.data?.detail || 'Failed to invite user');
    } finally {
      setSavingInvite(false);
    }
  };

  const steps = status?.steps || [];
  const activeStep = typeof status?.active_step === 'number' ? status.active_step : 0;

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 1 }}>
          First-Time Setup Wizard
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Complete the required temple or trust setup before regular operations begin.
        </Typography>

        {loading ? (
          <Alert severity="info">Loading setup wizard...</Alert>
        ) : (
          <>
            <Stepper activeStep={activeStep} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
              {steps.map((step) => (
                <Step key={step.id} completed={step.completed}>
                  <StepLabel>{step.title}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {status?.setup_complete ? (
              <Alert severity="success" sx={{ mb: 3 }}>
                Temple setup is complete. You can continue to the dashboard.
              </Alert>
            ) : (
              <Alert severity={status?.force_setup ? 'warning' : 'info'} sx={{ mb: 3 }}>
                {status?.force_setup
                  ? 'Complete temple or trust details, receipt settings, and at least one bank account to finish onboarding.'
                  : 'Setup details are incomplete for the selected temple/trust, but platform super admin can continue and return later.'}
              </Alert>
            )}

            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Card sx={{ mb: 3, borderLeft: '5px solid #1565C0' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Temple / Trust Details</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Temple Name" helperText="Shown in top banner if filled" value={templeForm.name} onChange={(e) => setTempleForm({ ...templeForm, name: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Trust Name" helperText="Used in top banner when Temple Name is blank" value={templeForm.trust_name} onChange={(e) => setTempleForm({ ...templeForm, trust_name: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Primary Deity" value={templeForm.primary_deity} onChange={(e) => setTempleForm({ ...templeForm, primary_deity: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Temple / Trust Email" value={templeForm.email} onChange={(e) => setTempleForm({ ...templeForm, email: e.target.value })} /></Grid>
                      <Grid item xs={12}><TextField fullWidth label="Address" value={templeForm.address} onChange={(e) => setTempleForm({ ...templeForm, address: e.target.value })} /></Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth label="City" value={templeForm.city} onChange={(e) => setTempleForm({ ...templeForm, city: e.target.value })} /></Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth label="State" value={templeForm.state} onChange={(e) => setTempleForm({ ...templeForm, state: e.target.value })} /></Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth label="Phone" value={templeForm.phone} onChange={(e) => setTempleForm({ ...templeForm, phone: e.target.value })} /></Grid>
                    </Grid>
                  </CardContent>
                </Card>

                <Card sx={{ mb: 3, borderLeft: '5px solid #FF9933' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Receipt & Financial Settings</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={4}>
                        <TextField select fullWidth label="Financial Year Start" value={templeForm.financial_year_start_month} onChange={(e) => setTempleForm({ ...templeForm, financial_year_start_month: e.target.value })}>
                          <MenuItem value={1}>January</MenuItem>
                          <MenuItem value={4}>April</MenuItem>
                        </TextField>
                      </Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth label="Donation Receipt Prefix" value={templeForm.receipt_prefix_donation} onChange={(e) => setTempleForm({ ...templeForm, receipt_prefix_donation: e.target.value })} /></Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth label="Seva Receipt Prefix" value={templeForm.receipt_prefix_seva} onChange={(e) => setTempleForm({ ...templeForm, receipt_prefix_seva: e.target.value })} /></Grid>
                    </Grid>
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                      <Button variant="contained" onClick={handleSaveTemple} disabled={savingTemple}>
                        {savingTemple ? 'Saving...' : 'Save Temple Setup'}
                      </Button>
                    </Box>
                  </CardContent>
                </Card>

                <Card sx={{ mb: 3, borderLeft: '5px solid #2E7D32' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Primary Bank Account</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Account Name" value={bankForm.account_name} onChange={(e) => setBankForm({ ...bankForm, account_name: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Bank Name" value={bankForm.bank_name} onChange={(e) => setBankForm({ ...bankForm, bank_name: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Branch Name" value={bankForm.branch_name} onChange={(e) => setBankForm({ ...bankForm, branch_name: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Account Number" value={bankForm.account_number} onChange={(e) => setBankForm({ ...bankForm, account_number: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="IFSC Code" value={bankForm.ifsc_code} onChange={(e) => setBankForm({ ...bankForm, ifsc_code: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField select fullWidth label="Account Type" value={bankForm.account_type} onChange={(e) => setBankForm({ ...bankForm, account_type: e.target.value })}><MenuItem value="Savings">Savings</MenuItem><MenuItem value="Current">Current</MenuItem></TextField></Grid>
                    </Grid>
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {bankAccounts.map((account) => (
                          <Chip key={account.id} label={`${account.bank_name}  ${account.account_number}`} color={account.is_primary ? 'success' : 'default'} />
                        ))}
                      </Box>
                      <Button variant="contained" color="success" onClick={handleCreateBankAccount} disabled={savingBank}>
                        {savingBank ? 'Saving...' : 'Add Bank Account'}
                      </Button>
                    </Box>
                  </CardContent>
                </Card>

                <Card sx={{ borderLeft: '5px solid #1565C0' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Invite Staff Users</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Optional during setup, but recommended so the temple is ready for operations.
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Full Name" value={inviteForm.full_name} onChange={(e) => setInviteForm({ ...inviteForm, full_name: e.target.value })} /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth label="Email" value={inviteForm.email} onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })} /></Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth label="Phone" value={inviteForm.phone} onChange={(e) => setInviteForm({ ...inviteForm, phone: e.target.value })} /></Grid>
                      <Grid item xs={12} md={4}><TextField select fullWidth label="Role" value={inviteForm.role} onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}>{roleOptions.map((option) => (<MenuItem key={option.role_key || option.value} value={option.role_key || option.value}>{option.display_name || option.label}</MenuItem>))}</TextField></Grid>
                      <Grid item xs={12} md={4}><TextField fullWidth type="password" label="Temporary Password" value={inviteForm.password} onChange={(e) => setInviteForm({ ...inviteForm, password: e.target.value })} /></Grid>
                    </Grid>
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {users.filter((user) => user.is_active).map((user) => (
                          <Chip key={user.id} label={`${user.full_name}  ${user.role}`} variant="outlined" />
                        ))}
                      </Box>
                      <Button variant="contained" color="secondary" onClick={handleInviteUser} disabled={savingInvite}>
                        {savingInvite ? 'Inviting...' : 'Invite User'}
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Setup Progress</Typography>
                    <Box sx={{ display: 'grid', gap: 1.5 }}>
                      {steps.map((step) => (
                        <Alert key={step.id} severity={step.completed ? 'success' : step.required ? 'warning' : 'info'}>
                          <strong>{step.title}</strong><br />{step.description}
                        </Alert>
                      ))}
                    </Box>
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                      <Button variant="contained" disabled={Boolean(status?.force_setup)} onClick={() => navigate('/dashboard', { replace: true })}>
                        Continue to Dashboard
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </>
        )}
      </Box>
    </Layout>
  );
}

export default SetupWizard;

