import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControlLabel,
  Container,
  Checkbox,
  Grid,
  Paper,
  TextField,
  Typography,
  Link,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';

const INITIAL_FORM = {
  temple_name: '',
  trust_name: '',
  temple_slug: '',
  primary_deity: 'Lord Ganesha',
  address: '',
  city: '',
  state: '',
  pincode: '',
  phone: '',
  email: '',
  admin_full_name: '',
  admin_email: '',
  admin_phone: '',
  authority_designation: '',
  authority_designation_other: '',
  request_intent: 'register',
  selected_plan: 'Decide after demo',
  plan_timing: 'After demo/discussion',
  verification_channel: 'email',
  terms_accepted: false,
};

function TempleRegistration() {
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(location.search || '');
    const queryEmail = (params.get('admin_email') || '').trim().toLowerCase();
    const pendingEmail = (sessionStorage.getItem('pending_onboarding_email') || '').trim().toLowerCase();
    const prefillEmail = queryEmail || pendingEmail;

    if (!prefillEmail) {
      return;
    }

    setForm((prev) => ({
      ...prev,
      admin_email: prev.admin_email || prefillEmail,
      email: prev.email || prefillEmail,
    }));
  }, [location.search]);

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (!form.temple_name.trim() && !form.trust_name.trim()) {
      setError('Fill Temple Name or Trust Name');
      return;
    }
    if (!form.admin_full_name.trim() || !form.admin_email.trim()) {
      setError('Temple admin name and email are required');
      return;
    }
    if (!form.authority_designation.trim()) {
      setError('Designation or authority is required');
      return;
    }
    if (form.authority_designation === 'Other' && !form.authority_designation_other.trim()) {
      setError('Please enter the designation or authority for Other');
      return;
    }
    if (!form.terms_accepted) {
      setError('Please confirm authority and accept the Terms of Service and Privacy Policy');
      return;
    }

    try {
      setLoading(true);
      const payload = {
        organization_name: (form.temple_name || form.trust_name).trim() || null,
        organization_type: 'TEMPLE',
        authority_designation: form.authority_designation.trim(),
        authority_designation_other: form.authority_designation === 'Other' ? form.authority_designation_other.trim() : null,
        request_intent: form.request_intent,
        selected_plan: form.selected_plan,
        plan_timing: form.plan_timing,
        verification_channel: form.verification_channel,
        terms_accepted: form.terms_accepted,
        temple_name: form.temple_name.trim() || null,
        trust_name: form.trust_name.trim() || null,
        temple_slug: form.temple_slug.trim() || null,
        primary_deity: form.primary_deity.trim() || 'Lord Ganesha',
        address: form.address.trim() || null,
        city: form.city.trim() || null,
        state: form.state.trim() || null,
        pincode: form.pincode.trim() || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        admin_full_name: form.admin_full_name.trim(),
        admin_email: form.admin_email.trim().toLowerCase(),
        admin_phone: form.admin_phone.trim() || null,
      };

      const response = await fetchWithApiFallback('/api/v1/onboarding-requests/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-App-Key': 'mandirmitra',
        },
        body: JSON.stringify(payload),
      }, { timeoutMs: 90000 });

      const rawBody = await response.text();
      let data = null;
      try {
        data = rawBody ? JSON.parse(rawBody) : null;
      } catch (_parseError) {
        data = null;
      }

      if (!response.ok) {
        const backendMessage =
          data?.detail ||
          data?.message ||
          data?.error?.message ||
          (Array.isArray(data?.detail)
            ? data.detail.map((d) => d?.msg).filter(Boolean).join('; ')
            : '') ||
          rawBody ||
          ('Failed to submit registration request (' + response.status + ')');
        throw new Error(String(backendMessage).trim());
      }

      setSuccess('Registration request submitted successfully. The platform owner will review and approve your temple or trust onboarding.');
      sessionStorage.removeItem('pending_onboarding_email');
      setForm(INITIAL_FORM);
    } catch (err) {
      const message = String(err?.message || '').trim();
      const isNetworkError = /failed to fetch|networkerror|load failed|aborted|aborterror|timed out|timeout/i.test(message);
      if (isNetworkError) {
        setError('Backend is taking too long to respond (possibly waking up). Please wait 30-60 seconds and retry.');
      } else {
        setError(message || 'Failed to submit registration request');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container component="main" maxWidth="md">
      <Box sx={{ my: 6 }}>
        <Paper elevation={3} sx={{ p: { xs: 3, md: 4 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Box
              component="img"
              src="/assets/brand/mandirmitra-logo.jpeg"
              alt="MandirMitra"
              sx={{ width: 28, height: 28, borderRadius: 1, objectFit: 'contain', flexShrink: 0 }}
            />
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              New Temple / Trust Registration
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Submit your temple or trust details here. The platform owner will review the request and approve onboarding before login credentials are issued.
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

          <Box component="form" onSubmit={handleSubmit}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}><TextField fullWidth label="Temple Name" value={form.temple_name} onChange={(e) => updateField('temple_name', e.target.value)} /></Grid>
              <Grid item xs={12} md={6}><TextField fullWidth label="Trust Name" value={form.trust_name} onChange={(e) => updateField('trust_name', e.target.value)} /></Grid>
              <Grid item xs={12} md={6}><TextField fullWidth label="Temple Slug (optional)" value={form.temple_slug} onChange={(e) => updateField('temple_slug', e.target.value)} /></Grid>
              <Grid item xs={12} md={6}><TextField fullWidth label="Primary Deity" value={form.primary_deity} onChange={(e) => updateField('primary_deity', e.target.value)} /></Grid>
              <Grid item xs={12}><TextField fullWidth label="Address" value={form.address} onChange={(e) => updateField('address', e.target.value)} /></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth label="City" value={form.city} onChange={(e) => updateField('city', e.target.value)} /></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth label="State" value={form.state} onChange={(e) => updateField('state', e.target.value)} /></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth label="PIN Code" value={form.pincode} onChange={(e) => updateField('pincode', e.target.value)} /></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth label="Temple Phone" value={form.phone} onChange={(e) => updateField('phone', e.target.value)} /></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth label="Temple Email" value={form.email} onChange={(e) => updateField('email', e.target.value)} /></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth label="Primary Admin Phone" value={form.admin_phone} onChange={(e) => updateField('admin_phone', e.target.value)} /></Grid>
              <Grid item xs={12} md={6}><TextField fullWidth label="Primary Admin Full Name" value={form.admin_full_name} onChange={(e) => updateField('admin_full_name', e.target.value)} /></Grid>
              <Grid item xs={12} md={6}><TextField fullWidth label="Primary Admin Email" value={form.admin_email} onChange={(e) => updateField('admin_email', e.target.value)} /></Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}>
                  Designation / Authority *
                </Typography>
                <TextField
                  fullWidth
                  select
                  SelectProps={{ native: true, inputProps: { 'aria-label': 'Designation / Authority' } }}
                  value={form.authority_designation}
                  onChange={(e) => updateField('authority_designation', e.target.value)}
                >
                  <option value="">Select designation</option>
                  <option value="Trustee">Trustee</option>
                  <option value="Admin">Admin</option>
                  <option value="Treasurer">Treasurer</option>
                  <option value="Secretary">Secretary</option>
                  <option value="President">President</option>
                  <option value="Authorized Signatory">Authorized Signatory</option>
                  <option value="Manager">Manager</option>
                  <option value="Other">Other</option>
                </TextField>
              </Grid>
              {form.authority_designation === 'Other' && (
                <Grid item xs={12} md={6}><TextField fullWidth label="Other Designation / Authority" value={form.authority_designation_other} onChange={(e) => updateField('authority_designation_other', e.target.value)} /></Grid>
              )}
              <Grid item xs={12} md={6}><TextField fullWidth select SelectProps={{ native: true }} label="Request Type" value={form.request_intent} onChange={(e) => updateField('request_intent', e.target.value)}><option value="register">Register</option><option value="demo">Request Demo</option></TextField></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth select SelectProps={{ native: true }} label="Plan" value={form.selected_plan} onChange={(e) => updateField('selected_plan', e.target.value)}><option value="Decide after demo">Decide after demo</option><option value="Starter">Starter</option><option value="Growth">Growth</option><option value="Professional">Professional</option></TextField></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth select SelectProps={{ native: true }} label="Plan Finalization" value={form.plan_timing} onChange={(e) => updateField('plan_timing', e.target.value)}><option value="After demo/discussion">After demo/discussion</option><option value="Ready to activate">Ready to activate</option></TextField></Grid>
              <Grid item xs={12} md={4}><TextField fullWidth select SelectProps={{ native: true }} label="OTP / Verification Channel" value={form.verification_channel} onChange={(e) => updateField('verification_channel', e.target.value)}><option value="email">Email</option><option value="mobile">Mobile</option></TextField></Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={<Checkbox checked={form.terms_accepted} onChange={(e) => updateField('terms_accepted', e.target.checked)} />}
                  label="I confirm I am authorized to register this temple/trust and accept the Terms of Service and Privacy Policy."
                />
              </Grid>
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 3, gap: 2, flexWrap: 'wrap' }}>
              <Link component="button" type="button" variant="body2" onClick={() => navigate('/login')}>
                Back to Login
              </Link>
              <Button type="submit" variant="contained" disabled={loading} sx={{ minWidth: 220 }}>
                {loading ? <CircularProgress size={24} /> : 'Submit Registration'}
              </Button>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}

export default TempleRegistration;






