import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Container, Paper, Typography, TextField, MenuItem,
  Button, Stepper, Step, StepLabel, Divider, Alert,
  CircularProgress, Chip, Grid, InputAdornment, ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { QRCodeSVG } from 'qrcode.react';
import SearchIcon from '@mui/icons-material/Search';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import VolunteerActivismIcon from '@mui/icons-material/VolunteerActivism';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import { buildApiUrl } from '../utils/apiBaseUrl';
import { useTranslation } from 'react-i18next';

const GOTHRA_OPTIONS = [
  'Kashyapa', 'Bharadvaja', 'Vasishtha', 'Vishvamitra', 'Jamadagni',
  'Gautama', 'Atri', 'Agastya', 'Angirasa', 'Kaundinya',
  'Parashara', 'Garga', 'Sandilya', 'Vatsa', 'Other',
];

const NAKSHTRA_OPTIONS = [
  'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
  'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni',
  'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha',
  'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha',
  'Shravana', 'Dhanishtha', 'Shatabhisha', 'Purva Bhadrapada',
  'Uttara Bhadrapada', 'Revati',
];

const RASHI_OPTIONS = [
  'Mesha (Aries)', 'Vrishabha (Taurus)', 'Mithuna (Gemini)',
  'Karka (Cancer)', 'Simha (Leo)', 'Kanya (Virgo)',
  'Tula (Libra)', 'Vrishchika (Scorpio)', 'Dhanu (Sagittarius)',
  'Makara (Capricorn)', 'Kumbha (Aquarius)', 'Meena (Pisces)',
];

// STEPS is built dynamically inside the component using t() — see below

const emptyForm = {
  seva_id: '', seva_name: '', amount: '',
  category_id: '', category_name: '',
  phone: '', name: '', email: '', address: '',
  pincode: '', city: '', state: '',
  gothra: '', nakshtra: '', rashi: '',
};

const buildUpiIntentUri = (result) => {
  if (!result?.upi_id) return '';
  const params = [
    ['pa', result.upi_id],
    ['pn', result.upi_payee_name || 'Temple'],
    ['cu', 'INR'],
  ];
  if (result.amount) params.push(['am', Number(result.amount).toFixed(2)]);
  const note = (result.seva_name || result.payment_type || 'Temple payment').slice(0, 50);
  if (note) params.push(['tn', note]);
  return `upi://pay?${params.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&')}`;
};

export default function PublicSevaPayment() {
  const { t } = useTranslation();
  const STEPS = [t('publicPayment.steps.select'), t('publicPayment.steps.devoteeDetails'), t('publicPayment.steps.makePayment')];

  const params = new URLSearchParams(window.location.search);
  const initialTempleId = params.get('temple_id') || '';

  const [templeId, setTempleId] = useState(initialTempleId);
  const [templeList, setTempleList] = useState([]);
  const [templeListLoading, setTempleListLoading] = useState(!initialTempleId);

  const [activeStep, setActiveStep] = useState(0);
  const [paymentType, setPaymentType] = useState('seva');
  const [templeInfo, setTempleInfo] = useState(null);
  const [sevas, setSevas] = useState([]);
  const [donationCategories, setDonationCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [paymentResult, setPaymentResult] = useState(null);
  const [upiIntentDetails, setUpiIntentDetails] = useState(null);
  const [copied, setCopied] = useState(false);
  const [pincodeLoading, setPincodeLoading] = useState(false);
  const [mobileSearching, setMobileSearching] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState(emptyForm);
  const [utr, setUtr] = useState('');
  const [whatsappSent, setWhatsappSent] = useState(false);
  const [confirmationCopied, setConfirmationCopied] = useState(false);
  const [idempotencyKey] = useState(() => {
    // Generate once per page load — prevents duplicate submissions on retry/double-tap
    const arr = new Uint8Array(16);
    crypto.getRandomValues(arr);
    return Array.from(arr).map((b) => b.toString(16).padStart(2, '0')).join('');
  });

  // Load temple list if no temple_id in URL
  useEffect(() => {
    if (initialTempleId) return;
    setTempleListLoading(true);
    fetch(buildApiUrl('/api/v1/public/temples'))
      .then((r) => r.ok ? r.json() : [])
      .then(setTempleList)
      .catch(() => {})
      .finally(() => setTempleListLoading(false));
  }, [initialTempleId]);

  // Load temple data when templeId is set
  useEffect(() => {
    if (!templeId) return;
    setLoading(true);
    Promise.all([
      fetch(buildApiUrl(`/api/v1/public/temples/${templeId}/info`)),
      fetch(buildApiUrl(`/api/v1/public/temples/${templeId}/sevas`)),
      fetch(buildApiUrl(`/api/v1/public/temples/${templeId}/donation-categories`)),
    ]).then(async ([infoRes, sevasRes, donRes]) => {
      if (infoRes.ok) setTempleInfo(await infoRes.json());
      if (sevasRes.ok) setSevas(await sevasRes.json());
      if (donRes.ok) setDonationCategories(await donRes.json());
    }).catch(() => {
      setError('Unable to load temple information. Please try again.');
    }).finally(() => setLoading(false));
  }, [templeId]);

  const handleTempleSelect = (temple) => {
    if (!temple) return;
    setTempleId(String(temple.temple_id));
    setTempleInfo(null);
    setSevas([]);
    setDonationCategories([]);
    setForm(emptyForm);
    setActiveStep(0);
    setPaymentType('seva');
  };

  const handleSevaSelect = (seva) => {
    setForm((f) => ({ ...f, seva_id: seva.seva_id, seva_name: seva.seva_name, amount: seva.amount || '', category_id: '', category_name: '' }));
  };

  const handleDonationSelect = (cat) => {
    setForm((f) => ({ ...f, category_id: cat.id, category_name: cat.name, amount: '', seva_id: '', seva_name: '' }));
  };

  const handlePaymentTypeChange = (_, newType) => {
    if (!newType) return;
    setPaymentType(newType);
    setForm((f) => ({ ...f, seva_id: '', seva_name: '', category_id: '', category_name: '', amount: '', gothra: '', nakshtra: '', rashi: '' }));
  };

  const handleMobileBlur = useCallback(async () => {
    if (form.phone.length < 10) return;
    setMobileSearching(true);
    try {
      const res = await fetch(buildApiUrl(`/api/v1/public/temples/${templeId}/devotee/autofill/${form.phone}`));
      if (res.ok) {
        const data = await res.json();
        if (data.found && data.devotee) setForm((f) => ({ ...f, ...data.devotee }));
      }
    } catch (_e) { /* best-effort */ }
    finally { setMobileSearching(false); }
  }, [form.phone, templeId]);

  const handlePincodeBlur = useCallback(async () => {
    if (form.pincode.length !== 6) return;
    setPincodeLoading(true);
    try {
      const res = await fetch(buildApiUrl(`/api/v1/public/location/pincode/${form.pincode}`));
      if (res.ok) {
        const data = await res.json();
        if (data.found) setForm((f) => ({ ...f, city: data.city, state: data.state }));
      }
    } catch (_e) { /* best-effort */ }
    finally { setPincodeLoading(false); }
  }, [form.pincode]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const body = {
        payment_type: paymentType,
        phone: form.phone, name: form.name, email: form.email,
        address: form.address, pincode: form.pincode, city: form.city, state: form.state,
        amount: form.amount,
        idempotency_key: idempotencyKey,
        ...(paymentType === 'seva'
          ? { seva_id: form.seva_id, seva_name: form.seva_name, gothra: form.gothra, nakshtra: form.nakshtra, rashi: form.rashi }
          : { category_id: form.category_id, category_name: form.category_name }),
      };
      const res = await fetch(buildApiUrl(`/api/v1/public/temples/${templeId}/seva-payments`), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || t('publicPayment.submissionFailed')); return; }
      setPaymentResult(data);
      await loadUpiIntent(data);
      setActiveStep(2);
    } catch (_e) {
      setError(t('publicPayment.networkError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = (text) => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  const loadUpiIntent = async (result) => {
    if (!templeId) return;
    const params = new URLSearchParams();
    const amount = result?.amount || form.amount;
    if (amount) params.set('amount', String(amount));
    params.set('purpose', result?.seva_name || form.seva_name || form.category_name || 'Temple payment');
    if (result?.payment_id) params.set('reference', result.payment_id);
    try {
      const url = `/api/v1/public/temples/${templeId}/upi-intent${params.toString() ? `?${params.toString()}` : ''}`;
      const res = await fetch(buildApiUrl(url));
      if (res.ok) {
        setUpiIntentDetails(await res.json());
      } else {
        setUpiIntentDetails(null);
      }
    } catch (_e) {
      setUpiIntentDetails(null);
    }
  };

  const buildWhatsappMessage = (result, utrValue) => {
    const template = result.whatsapp_message_template || '';
    return utrValue
      ? template.replace('[PASTE UTR HERE]', utrValue.trim())
      : template;
  };

  // Build WhatsApp link with UTR substituted into the template
  const buildWhatsappLink = (result, utrValue) => {
    if (!result?.admin_whatsapp) return null;
    const phone = result.admin_whatsapp.replace(/\D/g, '');
    const msg = buildWhatsappMessage(result, utrValue);
    try {
      return `https://wa.me/${phone}?text=${encodeURIComponent(msg)}`;
    } catch (_e) { /* best-effort */ return result.whatsapp_link; }
  };

  const handleCopyConfirmation = (result, utrValue) => {
    const phone = result?.admin_whatsapp ? `Temple WhatsApp: ${result.admin_whatsapp}\n\n` : '';
    navigator.clipboard.writeText(`${phone}${buildWhatsappMessage(result, utrValue)}`);
    setConfirmationCopied(true);
    setTimeout(() => setConfirmationCopied(false), 2500);
  };

  const resetForm = () => {
    setActiveStep(0); setPaymentResult(null); setPaymentType('seva'); setForm(emptyForm);
    setUpiIntentDetails(null); setUtr(''); setWhatsappSent(false); setConfirmationCopied(false);
    if (!initialTempleId) { setTempleId(''); setTempleInfo(null); }
  };

  const step0Valid = paymentType === 'seva' ? !!form.seva_name : !!form.category_name;
  const paymentDetails = paymentResult ? {
    ...paymentResult,
    upi_id: paymentResult.upi_id || upiIntentDetails?.upi_id || templeInfo?.upi_id || null,
    upi_payee_name: paymentResult.upi_payee_name || upiIntentDetails?.payee_name || templeInfo?.upi_payee_name || templeInfo?.trust_name || templeInfo?.temple_name || null,
    qr_code_image_url: paymentResult.qr_code_image_url || templeInfo?.qr_code_image_url || null,
    admin_whatsapp: paymentResult.admin_whatsapp || templeInfo?.admin_whatsapp || null,
  } : null;
  const upiIntentUri = buildUpiIntentUri(paymentDetails);
  const directUpiUri = upiIntentDetails?.intent_uri || upiIntentUri;
  const qrPayload = upiIntentDetails?.qr_payload || upiIntentUri;

  // ── HEADER ──────────────────────────────────────────────────────────────
  const HeaderBar = () => (
    <Paper elevation={3} sx={{ mb: 3, overflow: 'hidden' }}>
      {/* MandirMitra brand strip */}
      <Box sx={{ bgcolor: '#1a1a2e', px: 2, py: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box component="img" src="/branding/mandirmitra_logo1.jpg" alt="MandirMitra"
          sx={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover' }} />
        <Typography variant="caption" sx={{ color: '#FF9933', fontWeight: 'bold', letterSpacing: 1 }}>
          MANDIRMITRA · Temple Management System
        </Typography>
      </Box>
      {/* Temple name strip */}
      <Box sx={{ bgcolor: '#FF9933', px: 2, py: 1.5, textAlign: 'center' }}>
        {templeInfo ? (
          <>
            <Typography variant="h6" fontWeight="bold" color="white">
              {templeInfo.trust_name || templeInfo.temple_name || 'Temple'}
            </Typography>
            {templeInfo.trust_name && templeInfo.temple_name && (
              <Typography variant="body2" color="white" sx={{ opacity: 0.9 }}>{templeInfo.temple_name}</Typography>
            )}
            {(templeInfo.city || templeInfo.state) && (
              <Box display="flex" justifyContent="center" alignItems="center" gap={0.5} mt={0.3}>
                <LocationOnIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.8)' }} />
                <Typography variant="caption" color="white" sx={{ opacity: 0.85 }}>
                  {[templeInfo.city, templeInfo.state].filter(Boolean).join(', ')}
                </Typography>
              </Box>
            )}
          </>
        ) : (
          <Typography variant="h6" fontWeight="bold" color="white">Seva &amp; Donation Portal</Typography>
        )}
      </Box>
    </Paper>
  );

  // ── TEMPLE SELECTOR (shown when no temple_id in URL) ────────────────────
  if (!templeId) {
    return (
      <Box sx={{ minHeight: '100vh', bgcolor: '#FFF8F0', py: 3 }}>
        <Container maxWidth="sm">
          <HeaderBar />
          <Paper elevation={1} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom fontWeight="bold">{t('publicPayment.selectTemple')}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {t('publicPayment.selectTempleDesc')}
            </Typography>
            {templeListLoading ? (
              <Box display="flex" justifyContent="center" py={3}><CircularProgress /></Box>
            ) : templeList.length === 0 ? (
              <Alert severity="info">{t('publicPayment.noTemples')}</Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                {templeList.map((t) => (
                  <Paper key={t.temple_id} variant="outlined" onClick={() => handleTempleSelect(t)}
                    sx={{ p: 2, cursor: 'pointer', '&:hover': { borderColor: '#FF9933', bgcolor: '#FFF3E0' } }}>
                    <Typography fontWeight="bold">{t.trust_name || t.temple_name}</Typography>
                    {t.trust_name && t.temple_name && <Typography variant="caption" color="text.secondary">{t.temple_name}</Typography>}
                    {(t.city || t.state) && (
                      <Box display="flex" alignItems="center" gap={0.5} mt={0.3}>
                        <LocationOnIcon sx={{ fontSize: 13, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          {[t.city, t.state].filter(Boolean).join(', ')}
                        </Typography>
                      </Box>
                    )}
                  </Paper>
                ))}
              </Box>
            )}
          </Paper>
          <Typography variant="caption" color="text.secondary" display="block" textAlign="center" mt={3}>
            {t('publicPayment.poweredBy')} <strong>MandirMitra</strong>
          </Typography>
        </Container>
      </Box>
    );
  }

  // ── LOADING ──────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="100vh" gap={2}>
        <Box component="img" src="/branding/mandirmitra_logo1.jpg" alt="MandirMitra" sx={{ width: 64, height: 64, borderRadius: '50%' }} />
        <CircularProgress sx={{ color: '#FF9933' }} />
      </Box>
    );
  }

  // ── MAIN PAGE ────────────────────────────────────────────────────────────
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#FFF8F0', py: 3 }}>
      <Container maxWidth={activeStep === 2 ? "md" : "sm"}>
        <HeaderBar />

        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {STEPS.map((label) => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
        </Stepper>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

        {/* ── STEP 0 — Select ───────────────────────────────────────────── */}
        {activeStep === 0 && (
          <Paper elevation={1} sx={{ p: 3 }}>
            <Box display="flex" justifyContent="center" mb={3}>
              <ToggleButtonGroup value={paymentType} exclusive onChange={handlePaymentTypeChange} color="primary" size="small">
                <ToggleButton value="seva" sx={{ px: 3, gap: 0.5 }}>
                  <TempleHinduIcon fontSize="small" /> {t('publicPayment.bookASeva')}
                </ToggleButton>
                <ToggleButton value="donation" sx={{ px: 3, gap: 0.5 }}>
                  <VolunteerActivismIcon fontSize="small" /> {t('publicPayment.makeADonation')}
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>
            <Divider sx={{ mb: 2 }} />

            {/* SEVA list */}
            {paymentType === 'seva' && (
              <>
                <Typography variant="subtitle1" fontWeight="bold" gutterBottom>{t('publicPayment.selectSeva')}</Typography>
                {sevas.length === 0 ? (
                  <Alert severity="info">{t('publicPayment.noSevas')}</Alert>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {sevas.map((seva) => (
                      <Paper key={seva.seva_id} variant="outlined" onClick={() => handleSevaSelect(seva)}
                        sx={{ p: 2, cursor: 'pointer', border: form.seva_id === seva.seva_id ? '2px solid #FF9933' : '1px solid #ddd', bgcolor: form.seva_id === seva.seva_id ? '#FFF3E0' : 'white' }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center">
                          <Typography fontWeight={form.seva_id === seva.seva_id ? 'bold' : 'normal'}>{seva.seva_name}</Typography>
                          {seva.amount > 0 && <Chip label={`₹${seva.amount}`} color="primary" size="small" />}
                        </Box>
                        {seva.description && <Typography variant="caption" color="text.secondary">{seva.description}</Typography>}
                        {seva.frequency === 'annual' && <Chip label="Annual" size="small" sx={{ mt: 0.5 }} color="warning" variant="outlined" />}
                      </Paper>
                    ))}
                  </Box>
                )}
                {form.seva_name && (
                  <TextField label={t('publicPayment.amount')} value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                    fullWidth sx={{ mt: 2 }} type="number" helperText={t('publicPayment.amountHelp')} />
                )}
              </>
            )}

            {/* DONATION list */}
            {paymentType === 'donation' && (
              <>
                <Typography variant="subtitle1" fontWeight="bold" gutterBottom>{t('publicPayment.selectDonation')}</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {donationCategories.map((cat) => (
                    <Paper key={cat.id} variant="outlined" onClick={() => handleDonationSelect(cat)}
                      sx={{ p: 2, cursor: 'pointer', border: form.category_id === cat.id ? '2px solid #FF9933' : '1px solid #ddd', bgcolor: form.category_id === cat.id ? '#FFF3E0' : 'white' }}>
                      <Typography fontWeight={form.category_id === cat.id ? 'bold' : 'normal'}>{cat.name}</Typography>
                      {cat.description && <Typography variant="caption" color="text.secondary">{cat.description}</Typography>}
                    </Paper>
                  ))}
                </Box>
                {form.category_name && (
                  <TextField label={t('publicPayment.donationAmount')} value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                    fullWidth sx={{ mt: 2 }} type="number" required />
                )}
              </>
            )}

            <Button variant="contained" fullWidth sx={{ mt: 3, bgcolor: '#FF9933', '&:hover': { bgcolor: '#e68900' } }}
              disabled={!step0Valid || (paymentType === 'donation' && !form.amount)}
              onClick={() => setActiveStep(1)}>
              {t('publicPayment.continue')}
            </Button>

            {!initialTempleId && (
              <Button variant="text" fullWidth size="small" sx={{ mt: 1, color: 'text.secondary' }}
                onClick={() => { setTempleId(''); setTempleInfo(null); }}>
                {t('publicPayment.chooseDifferentTemple')}
              </Button>
            )}
          </Paper>
        )}

        {/* ── STEP 1 — Devotee Details ──────────────────────────────────── */}
        {activeStep === 1 && (
          <Paper elevation={1} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom fontWeight="bold">{t('publicPayment.devoteeDetailsTitle')}</Typography>
            {paymentType === 'seva'
              ? <Alert severity="info" sx={{ mb: 2 }} icon={<TempleHinduIcon />}><strong>Seva:</strong> {form.seva_name}{form.amount && ` — ₹${form.amount}`}</Alert>
              : <Alert severity="success" sx={{ mb: 2 }} icon={<VolunteerActivismIcon />}><strong>Donation:</strong> {form.category_name} — ₹{form.amount}</Alert>}
            <Divider sx={{ mb: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField label={t('publicPayment.mobile')} value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  onBlur={handleMobileBlur} fullWidth inputProps={{ maxLength: 10 }}
                  InputProps={{ endAdornment: <InputAdornment position="end">{mobileSearching ? <CircularProgress size={18} /> : <SearchIcon color="action" />}</InputAdornment> }}
                  helperText={t('publicPayment.mobileHelp')} />
              </Grid>
              <Grid item xs={12}>
                <TextField label={t('publicPayment.fullName')} value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} fullWidth />
              </Grid>
              <Grid item xs={12}>
                <TextField label={t('publicPayment.email')} value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} fullWidth type="email" />
              </Grid>
              <Grid item xs={12}>
                <TextField label={t('publicPayment.address')} value={form.address} onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} fullWidth multiline rows={2} />
              </Grid>
              <Grid item xs={4}>
                <TextField label={t('publicPayment.pincode')} value={form.pincode} onChange={(e) => setForm((f) => ({ ...f, pincode: e.target.value }))}
                  onBlur={handlePincodeBlur} fullWidth inputProps={{ maxLength: 6 }}
                  InputProps={{ endAdornment: pincodeLoading ? <InputAdornment position="end"><CircularProgress size={16} /></InputAdornment> : null }} />
              </Grid>
              <Grid item xs={4}><TextField label={t('publicPayment.city')} value={form.city} onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))} fullWidth /></Grid>
              <Grid item xs={4}><TextField label={t('publicPayment.state')} value={form.state} onChange={(e) => setForm((f) => ({ ...f, state: e.target.value }))} fullWidth /></Grid>

              {paymentType === 'seva' && (
                <>
                  <Grid item xs={12}><Divider><Typography variant="caption" color="text.secondary">{t('publicPayment.astroSection')}</Typography></Divider></Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField select label={t('publicPayment.gothra')} value={form.gothra} onChange={(e) => setForm((f) => ({ ...f, gothra: e.target.value }))} fullWidth>
                      <MenuItem value="">{t('publicPayment.select')}</MenuItem>
                      {GOTHRA_OPTIONS.map((g) => <MenuItem key={g} value={g}>{g}</MenuItem>)}
                    </TextField>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField select label={t('publicPayment.nakshtra')} value={form.nakshtra} onChange={(e) => setForm((f) => ({ ...f, nakshtra: e.target.value }))} fullWidth>
                      <MenuItem value="">{t('publicPayment.select')}</MenuItem>
                      {NAKSHTRA_OPTIONS.map((n) => <MenuItem key={n} value={n}>{n}</MenuItem>)}
                    </TextField>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField select label={t('publicPayment.rashi')} value={form.rashi} onChange={(e) => setForm((f) => ({ ...f, rashi: e.target.value }))} fullWidth>
                      <MenuItem value="">{t('publicPayment.select')}</MenuItem>
                      {RASHI_OPTIONS.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                    </TextField>
                  </Grid>
                </>
              )}
            </Grid>

            <Box display="flex" gap={2} mt={3}>
              <Button variant="outlined" onClick={() => setActiveStep(0)} sx={{ flex: 1 }}>{t('publicPayment.back')}</Button>
              <Button variant="contained" sx={{ flex: 2, bgcolor: '#FF9933', '&:hover': { bgcolor: '#e68900' } }}
                disabled={!form.phone || !form.name || submitting} onClick={handleSubmit}>
                {submitting ? <CircularProgress size={22} color="inherit" /> : t('publicPayment.proceedToPayment')}
              </Button>
            </Box>
          </Paper>
        )}

        {/* ── STEP 2 — Make Payment ─────────────────────────────────────── */}
        {activeStep === 2 && paymentResult && (
          <Paper elevation={1} sx={{ p: 3 }}>
            <Box textAlign="center" mb={2}>
              <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main' }} />
              <Typography variant="h6" fontWeight="bold" mt={1}>{t('publicPayment.detailsSaved')}</Typography>
              <Chip label={t('publicPayment.paymentId', { id: paymentResult.payment_id })} color="primary" sx={{ mt: 1 }} />
            </Box>
            <Divider sx={{ mb: 2 }} />

            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>{paymentResult.payment_type === 'donation' ? 'Donation' : 'Seva'}:</strong>{' '}
              {paymentResult.seva_name}{paymentResult.amount && ` — ₹${paymentResult.amount}`}
            </Alert>

            {(paymentDetails?.qr_code_image_url || qrPayload) && (
              <Box
                textAlign="center"
                sx={{
                  mb: 2,
                  width: '100%',
                  float: 'none',
                  pr: 0,
                }}
              >
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {paymentDetails?.qr_code_image_url ? 'Bank QR Code to Pay' : t('publicPayment.scanQR')}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
                  {paymentDetails?.qr_code_image_url
                    ? 'Use the bank-provided QR if the generated UPI link fails.'
                    : t('publicPayment.scanQRDesc')}
                </Typography>
                <Box
                  display="inline-block"
                  p={1.25}
                  border="1px solid #ddd"
                  borderRadius={2}
                  bgcolor="white"
                  sx={{
                    maxWidth: '100%',
                    '& svg': {
                      width: { xs: 176, sm: 196, md: 206 },
                      height: { xs: 176, sm: 196, md: 206 },
                      display: 'block',
                    },
                  }}
                >
                  {paymentDetails?.qr_code_image_url ? (
                    <Box
                      component="img"
                      src={paymentDetails.qr_code_image_url}
                      alt="Bank UPI QR code"
                      sx={{
                        width: { xs: 176, sm: 196, md: 206 },
                        height: { xs: 176, sm: 196, md: 206 },
                        objectFit: 'contain',
                        display: 'block',
                      }}
                    />
                  ) : (
                    <QRCodeSVG
                      value={qrPayload}
                      size={206}
                      level="H"
                      includeMargin={false}
                    />
                  )}
                </Box>
                <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                  {t('publicPayment.upiApps')}
                </Typography>
              </Box>
            )}

            {paymentDetails?.upi_id && (
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  mb: 2,
                  textAlign: 'center',
                  bgcolor: '#F9F9F9',
                  width: '100%',
                  float: 'none',
                  clear: 'both',
                  overflowWrap: 'anywhere',
                }}
              >
                <Typography variant="body2" color="text.secondary">{t('publicPayment.upiId')}</Typography>
                <Typography variant="h6" fontWeight="bold" letterSpacing={0.5}>{paymentDetails.upi_id}</Typography>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<AccountBalanceWalletIcon />}
                  href={directUpiUri}
                  sx={{ mt: 1.25, mb: 0.75, bgcolor: '#FF9933', '&:hover': { bgcolor: '#e65c00' } }}
                >
                  {t('publicPayment.openUpiApp')}
                </Button>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.75}>
                  {t('publicPayment.openUpiAppDesc')}
                </Typography>
                <Button size="small" startIcon={copied ? <CheckCircleIcon /> : <ContentCopyIcon />}
                  onClick={() => handleCopy(paymentDetails.upi_id)} sx={{ mt: 0.5 }}>
                  {copied ? 'Copied!' : 'Copy UPI ID'}
                </Button>
                <Alert severity="warning" sx={{ mt: 1.5, textAlign: 'left' }}>
                  If your UPI app says receiver is not allowed, do not send confirmation yet. The temple must verify this UPI ID / bank QR with its bank or provide another payment option.
                </Alert>
              </Paper>
            )}

            {!paymentDetails?.upi_id && !paymentDetails?.qr_code_image_url && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Payment details not configured yet. Please contact the temple for payment instructions.
              </Alert>
            )}

            {/* ── 3-step admin notification card ── */}
            <Box
              sx={{
                border: '2px solid #FF9933',
                borderRadius: 2,
                p: 2,
                mb: 2,
                mt: 0,
                bgcolor: '#FFFDE7',
                width: '100%',
                float: 'none',
              }}
            >
              <Typography variant="subtitle1" fontWeight="bold" color="#e65c00" gutterBottom>
                📋 Important — 3 Steps to complete your booking
              </Typography>

              {/* Step 1 */}
              <Box sx={{ display: 'flex', gap: 1.5, mb: 1.5 }}>
                <Box sx={{ width: 28, height: 28, borderRadius: '50%', bgcolor: '#FF9933', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', flexShrink: 0, mt: 0.5 }}>1</Box>
                <Box>
                  <Typography variant="body2" fontWeight="bold">Make the UPI payment</Typography>
                  <Typography variant="caption" color="text.secondary">Tap Open UPI App on this phone, or scan the QR from another phone</Typography>
                </Box>
              </Box>

              {/* Step 2 — UTR */}
              <Box sx={{ display: 'flex', gap: 1.5, mb: 1.5 }}>
                <Box sx={{ width: 28, height: 28, borderRadius: '50%', bgcolor: '#FF9933', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', flexShrink: 0, mt: 0.5 }}>2</Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" fontWeight="bold">Note your UTR / Transaction Reference</Typography>
                  <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                    After payment, your UPI app shows a UTR or transaction ID. Enter it here:
                  </Typography>
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="e.g. 4125789632014"
                    label={t('publicPayment.enterUtr')}
                    value={utr}
                    onChange={(e) => setUtr(e.target.value)}
                    sx={{ bgcolor: '#fff' }}
                  />
                </Box>
              </Box>

              {/* Step 3 — WhatsApp */}
              <Box sx={{ display: 'flex', gap: 1.5 }}>
                <Box sx={{ width: 28, height: 28, borderRadius: '50%', bgcolor: whatsappSent ? '#25D366' : '#FF9933', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', flexShrink: 0, mt: 0.5 }}>
                  {whatsappSent ? '✓' : '3'}
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    Send WhatsApp confirmation to the temple admin
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                    {whatsappSent
                      ? 'Confirmation opened. The admin will verify the UTR and confirm your booking.'
                      : 'After payment, enter the UTR above. Then open WhatsApp or copy the message for desktop/laptop use.'}
                  </Typography>
                  {paymentDetails?.admin_whatsapp && (
                    <>
                      {!utr.trim() && (
                        <Alert severity="warning" sx={{ mb: 1 }}>
                          Please complete the UPI payment and enter the UTR / transaction reference before sending confirmation.
                        </Alert>
                      )}
                      <Button
                        variant="contained"
                        fullWidth
                        startIcon={<WhatsAppIcon />}
                        href={utr.trim() ? buildWhatsappLink(paymentDetails, utr) : undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        disabled={!utr.trim()}
                        onClick={() => setWhatsappSent(true)}
                        sx={{
                          bgcolor: whatsappSent ? '#128C7E' : '#25D366',
                          '&:hover': { bgcolor: '#075E54' },
                          fontWeight: 'bold',
                          py: 1.2,
                          fontSize: { xs: 13, sm: 14 },
                          whiteSpace: 'normal',
                          lineHeight: 1.2,
                        }}
                      >
                        {whatsappSent ? 'Send Again / Resend' : 'Send WhatsApp to Temple Admin'}
                      </Button>
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={confirmationCopied ? <CheckCircleIcon /> : <ContentCopyIcon />}
                        disabled={!utr.trim()}
                        onClick={() => handleCopyConfirmation(paymentDetails, utr)}
                        sx={{ mt: 1, bgcolor: '#fff', fontWeight: 'bold' }}
                      >
                        {confirmationCopied ? 'Confirmation copied' : 'Copy confirmation message'}
                      </Button>
                      <Typography variant="caption" color="text.secondary" display="block" mt={0.75}>
                        On desktop/laptop, WhatsApp opens in the browser. If it is not available, copy the message and send it manually to the temple WhatsApp number.
                      </Typography>
                    </>
                  )}
                  {!paymentDetails?.admin_whatsapp && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      Please call or visit the temple office to confirm your payment.
                    </Alert>
                  )}
                </Box>
              </Box>
            </Box>

            <Button variant="outlined" fullWidth onClick={resetForm} sx={{ clear: 'both' }}>{t('publicPayment.bookAnother')}</Button>
          </Paper>
        )}

        <Typography variant="caption" color="text.secondary" display="block" textAlign="center" mt={3}>
          {t('publicPayment.poweredBy')} <strong>MandirMitra</strong> · Temple Management System
        </Typography>
      </Container>
    </Box>
  );
}
