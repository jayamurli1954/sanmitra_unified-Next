import React, { useState, useEffect, useRef } from 'react';
import {
  Typography,
  Box,
  Grid,
  Paper,
  Card,
  CardContent,
  TextField,
  Button,
  MenuItem,
  Alert,
  CircularProgress,
  InputAdornment,
  Stack,
  Chip,
  Divider,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import EventIcon from '@mui/icons-material/Event';
import SaveIcon from '@mui/icons-material/Save';
import DashboardIcon from '@mui/icons-material/Dashboard';
import CurrencyRupeeIcon from '@mui/icons-material/CurrencyRupee';
import GroupsIcon from '@mui/icons-material/Groups';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import VolunteerActivismIcon from '@mui/icons-material/VolunteerActivism';
import EventAvailableIcon from '@mui/icons-material/EventAvailable';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import Layout from '../components/Layout';
import PanchangDisplay from '../components/PanchangDisplay';
import api from '../services/api';
import { ACTIVE_TEMPLE_EVENT, getActiveTempleId } from '../utils/activeTemple';

const bankSubModeOptions = [
  { value: 'UPI', label: 'UPI' },
  { value: 'Online', label: 'Online Transfer' },
  { value: 'Cheque', label: 'Cheque' },
  { value: 'DD', label: 'DD' },
];

const emptyBankPaymentFields = {
  bank_sub_mode: '',
  sender_upi_id: '',
  upi_reference_number: '',
  utr_number: '',
  payer_name: '',
  cheque_number: '',
  cheque_date: '',
  cheque_bank_name: '',
  cheque_branch: '',
};

const getInitialDonationForm = () => ({
  name_prefix: 'Sri',
  first_name: '',
  last_name: '',
  devotee_phone: '',
  email: '',
  pan_number: '',
  amount: '',
  category: '',
  payment_mode: 'Cash',
  payment_account_id: '',
  ...emptyBankPaymentFields,
  address: '',  // Street address
  pincode: '',
  city: '',
  state: '',
  country: 'India',
});

function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [stats, setStats] = useState({
    donations: {
      today: { amount: 0, count: 0 },
      month: { amount: 0, count: 0 },
      year: { amount: 0, count: 0 }
    },
    sevas: {
      today: { amount: 0, count: 0 },
      month: { amount: 0, count: 0 },
      year: { amount: 0, count: 0 }
    }
  });
  const [panchangData, setPanchangData] = useState(null);
  const [donationForm, setDonationForm] = useState(getInitialDonationForm());
  const [pincodeLoading, setPincodeLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [paymentAccounts, setPaymentAccounts] = useState({ cash_accounts: [], bank_accounts: [] });
  const [paymentAccountsWarning, setPaymentAccountsWarning] = useState('');
  const [recentDonations, setRecentDonations] = useState([]);
  const [recentSevas, setRecentSevas] = useState([]);
  const [saving, setSaving] = useState(false);
  const [searchingDevotee, setSearchingDevotee] = useState(false);
  const [foundDevotee, setFoundDevotee] = useState(null);
  const [mobileVerified, setMobileVerified] = useState(false);
  const [lookupStatus, setLookupStatus] = useState('idle'); // idle | found | not_found
  const firstNameInputRef = useRef(null);

  const namePrefixes = ['Sri', 'Smt.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'M/s.'];
  const sleep = (delayMs) => new Promise((resolve) => window.setTimeout(resolve, delayMs));

  const isTransientApiError = (err) => {
    const status = err?.response?.status;
    if (!status) {
      return true;
    }
    return status >= 500 || status === 429;
  };

  const runWithRetry = async (requestFn, retries = 1, retryDelayMs = 1000) => {
    let lastError = null;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      try {
        return await requestFn();
      } catch (err) {
        lastError = err;
        if (attempt >= retries || !isTransientApiError(err)) {
          throw err;
        }
        await sleep(retryDelayMs);
      }
    }
    throw lastError || new Error('Request failed');
  };

  const getFriendlyApiError = (err, fallbackMessage) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    const detailText = Array.isArray(detail)
      ? detail.map((item) => item?.msg || String(item)).join(', ')
      : (typeof detail === 'string' ? detail : '');
    const normalizedDetail = detailText.toLowerCase();

    if (normalizedDetail.includes('temple context is required')) {
      return 'Please select a temple first and then retry.';
    }

    if (status === 403 && normalizedDetail.includes('read-only')) {
      return 'This tenant is read-only for the current platform administrator.';
    }

    if (status === 403) {
      return 'You do not have permission to access this temple data.';
    }

    if (err?.code === 'ERR_NETWORK' || err?.code === 'ECONNABORTED' || err?.message?.includes('Network Error')) {
      return 'Backend is not reachable right now. Render may be waking up. Please retry in a few seconds.';
    }

    if (status >= 500) {
      return 'Backend service is temporarily unavailable. Please retry shortly.';
    }

    if (detailText) {
      return detailText;
    }

    return fallbackMessage;
  };

  useEffect(() => {
    fetchDashboardStats();
    fetchPanchangData();
    fetchCategories();
    fetchPaymentAccounts();
    fetchDashboardActivity();
  }, []);

  useEffect(() => {
    const handleActiveTempleChanged = () => {
      fetchDashboardStats();
      fetchPanchangData();
      fetchCategories();
      fetchPaymentAccounts();
      fetchDashboardActivity();
    };

    window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChanged);
    window.addEventListener('storage', handleActiveTempleChanged);

    if (getActiveTempleId()) {
      handleActiveTempleChanged();
    }

    return () => {
      window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChanged);
      window.removeEventListener('storage', handleActiveTempleChanged);
    };
  }, []);

  useEffect(() => {
    if (lookupStatus === 'not_found' && mobileVerified && firstNameInputRef.current) {
      setTimeout(() => {
        firstNameInputRef.current?.focus();
      }, 0);
    }
  }, [lookupStatus, mobileVerified]);

  const fetchDashboardStats = async () => {
    try {
      setLoading(true);
      const statsRes = await api.get('/api/v1/dashboard/stats');
      if (statsRes?.data) {
        setStats(statsRes.data);
        return;
      }
    } catch (err) {
      console.error('Error fetching dashboard stats:', err);
    } finally {
      setLoading(false);
    }

    setStats({
      donations: { today: { amount: 0, count: 0 }, month: { amount: 0, count: 0 }, year: { amount: 0, count: 0 } },
      sevas: { today: { amount: 0, count: 0 }, month: { amount: 0, count: 0 }, year: { amount: 0, count: 0 } }
    });
  };

  const fetchPanchangData = async () => {
    try {
      const [panchangSettingsRes, panchangDataRes] = await Promise.allSettled([
        api.get('/api/v1/panchang/display-settings/'),
        api.get('/api/v1/panchang/today'),
      ]);

      let panchangSettings = null;
      let panchangData = null;

      if (panchangSettingsRes.status === 'fulfilled' && panchangSettingsRes.value.data) {
        panchangSettings = panchangSettingsRes.value.data;
      }

      if (panchangDataRes.status === 'fulfilled' && panchangDataRes.value.data) {
        panchangData = panchangDataRes.value.data;
      } else if (panchangDataRes.status === 'rejected') {
        const error = panchangDataRes.reason;
        if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
          console.warn('Panchang API not reachable');
        } else {
          console.log('Panchang data API failed:', error);
        }
      }

      if (panchangData) {
        setPanchangData({
          ...panchangData,
          ...(panchangSettings || {})
        });
      } else if (panchangSettings) {
        setPanchangData(panchangSettings);
      }
    } catch (err) {
      console.error('Error fetching panchang data:', err);
    }
  };

  const fetchCategories = async () => {
    try {
      setCategories([
        'General Donation',
        'Annadanam',
        'Construction Fund',
        'Gold/Silver Donation',
        'Corpus Fund'
      ]);
    } catch (err) {
      console.error('Error fetching categories:', err);
    }
  };

  const fetchPaymentAccounts = async () => {
    try {
      const response = await runWithRetry(() => api.get('/api/v1/donations/payment-accounts'), 1, 1200);
      const data = response?.data || {};
      const cashAccounts = Array.isArray(data.cash_accounts) ? data.cash_accounts : [];
      const bankAccounts = Array.isArray(data.bank_accounts) ? data.bank_accounts : [];

      setPaymentAccounts({
        cash_accounts: cashAccounts,
        bank_accounts: bankAccounts,
      });

      if (cashAccounts.length === 0 && bankAccounts.length === 0) {
        setPaymentAccountsWarning('No active cash or bank accounts found for this temple. Please configure accounts in Accounting.');
      } else {
        setPaymentAccountsWarning('');
      }
    } catch (err) {
      console.error('Error fetching payment accounts:', err);
      setPaymentAccounts({ cash_accounts: [], bank_accounts: [] });
      setPaymentAccountsWarning(getFriendlyApiError(err, 'Could not fetch payment accounts right now.'));
    }
  };

  const handleDonationChange = (field, value) => {
    let normalizedValue = value;

    if (field === 'devotee_phone') {
      normalizedValue = value.replace(/\D/g, '').slice(0, 10);
      setMobileVerified(false);
      setFoundDevotee(null);
      setLookupStatus('idle');
    }

    setDonationForm((prev) => {
      const updated = { ...prev, [field]: normalizedValue };

      if (field === 'payment_mode') {
        updated.payment_account_id = '';
        if (normalizedValue !== 'Bank') {
          updated.bank_sub_mode = '';
          Object.assign(updated, emptyBankPaymentFields);
        }
      }

      if (field === 'bank_sub_mode') {
        Object.assign(updated, emptyBankPaymentFields);
        updated.bank_sub_mode = normalizedValue;
      }

      if (field === 'pincode' && normalizedValue.length < 6) {
        updated.city = '';
        updated.state = '';
      }

      return updated;
    });

    // Auto-fill City and State when PIN code is entered (6 digits)
    if (field === 'pincode' && normalizedValue.length === 6) {
      fetchPincodeDetails(normalizedValue);
    }
  };

  const splitFullName = (fullName = '') => {
    const trimmedName = (fullName || '').trim();
    if (!trimmedName) {
      return { firstName: '', lastName: '' };
    }

    const parts = trimmedName.split(/\s+/).filter(Boolean);
    if (parts.length === 1) {
      return { firstName: parts[0], lastName: '' };
    }

    return {
      firstName: parts[0],
      lastName: parts.slice(1).join(' '),
    };
  };

  const fetchDashboardActivity = async () => {
    try {
      const [donationsRes, sevasRes] = await Promise.allSettled([
        api.get('/api/v1/donations', { params: { limit: 8 } }),
        api.get('/api/v1/sevas/bookings', { params: { limit: 8 } }),
      ]);

      setRecentDonations(
        donationsRes.status === 'fulfilled' && Array.isArray(donationsRes.value?.data)
          ? donationsRes.value.data
          : []
      );
      setRecentSevas(
        sevasRes.status === 'fulfilled' && Array.isArray(sevasRes.value?.data)
          ? sevasRes.value.data
          : []
      );
    } catch (err) {
      console.error('Error fetching dashboard activity:', err);
      setRecentDonations([]);
      setRecentSevas([]);
    }
  };

  const isValidPan = (value) => /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(String(value || '').trim().toUpperCase());

  const handleSearchByMobile = async () => {
    const phone = donationForm.devotee_phone.trim();
    if (phone.length !== 10) {
      setError('Please enter a valid 10-digit mobile number');
      return;
    }

    setSearchingDevotee(true);
    setError('');
    setSuccess('');

    try {
      const response = await runWithRetry(() => api.get(`/api/v1/devotees/search/by-mobile/${phone}`), 1, 1000);
      const devoteeList = Array.isArray(response.data) ? response.data : [];
      const devotee = devoteeList[0];

      if (devotee) {
        const parsedName = splitFullName(devotee.name);

        setDonationForm((prev) => ({
          ...prev,
          devotee_phone: phone,
          name_prefix: devotee.name_prefix || prev.name_prefix || 'Sri',
          first_name: parsedName.firstName,
          last_name: parsedName.lastName,
          email: devotee.email || '',
          pan_number: devotee.pan_number || devotee.pan || '',
          address: devotee.address || '',
          pincode: devotee.pincode || '',
          city: devotee.city || '',
          state: devotee.state || '',
          country: devotee.country || prev.country || 'India',
        }));

        setFoundDevotee(devotee);
        setLookupStatus('found');
      } else {
        setFoundDevotee(null);
        setLookupStatus('not_found');
        setDonationForm((prev) => ({
          ...prev,
          devotee_phone: phone,
          first_name: '',
          last_name: '',
          email: '',
          pan_number: '',
          address: '',
          pincode: '',
          city: '',
          state: '',
          country: prev.country || 'India',
        }));
      }

      setMobileVerified(true);
    } catch (err) {
      if (err.response?.status === 404) {
        setFoundDevotee(null);
        setLookupStatus('not_found');
        setMobileVerified(true);
        setDonationForm((prev) => ({
          ...prev,
          devotee_phone: phone,
          first_name: '',
          last_name: '',
          email: '',
          pan_number: '',
          address: '',
          pincode: '',
          city: '',
          state: '',
          country: prev.country || 'India',
        }));
      } else {
        setMobileVerified(false);
        setLookupStatus('idle');
        setError(getFriendlyApiError(err, 'Could not search devotee right now. Please try again.'));
      }
    } finally {
      setSearchingDevotee(false);
    }
  };
  const fetchPincodeDetails = async (pincode) => {
    if (!pincode || pincode.length !== 6) return;

    try {
      setPincodeLoading(true);
      const response = await api.get('/api/v1/pincode/lookup', {
        params: { pincode },
      });

      const lookup = response.data || {};
      setDonationForm((prev) => ({
        ...prev,
        city: lookup.found ? (lookup.city || lookup.district || '') : '',
        state: lookup.found ? (lookup.state || '') : '',
      }));
    } catch (err) {
      console.error('Error fetching PIN code details:', err);
      // Don't show error to user, just silently fail
    } finally {
      setPincodeLoading(false);
    }
  };

  const handleDonationSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    if (!mobileVerified) {
      setError('Search mobile number first. If devotee is not found, you can enter details and continue.');
      setSaving(false);
      return;
    }

    if (!donationForm.devotee_phone || donationForm.devotee_phone.length !== 10) {
      setError('Please enter a valid 10-digit mobile number');
      setSaving(false);
      return;
    }

    const amountNum = Number(donationForm.amount);
    if (!Number.isFinite(amountNum) || amountNum <= 0) {
      setError('Please enter a valid donation amount greater than zero.');
      setSaving(false);
      return;
    }

    if (!donationForm.payment_account_id) {
      setError(`Please select ${donationForm.payment_mode === 'Bank' ? 'bank' : 'cash'} account code.`);
      setSaving(false);
      return;
    }

    if (donationForm.pan_number && !isValidPan(donationForm.pan_number)) {
      setError('PAN format must be AAAAA9999A');
      setSaving(false);
      return;
    }

    if (donationForm.payment_mode === 'Bank' && !donationForm.bank_sub_mode) {
      setError('Please select Bank Sub-Category (UPI/Online Transfer/Cheque/DD).');
      setSaving(false);
      return;
    }

    if (donationForm.payment_mode === 'Bank' && donationForm.bank_sub_mode === 'UPI' && !donationForm.upi_reference_number?.trim()) {
      setError('Please enter UPI transaction reference.');
      setSaving(false);
      return;
    }

    if (donationForm.payment_mode === 'Bank' && donationForm.bank_sub_mode === 'Online' && !donationForm.utr_number?.trim()) {
      setError('Please enter UTR reference number.');
      setSaving(false);
      return;
    }

    if (donationForm.payment_mode === 'Bank' && ['Cheque', 'DD'].includes(donationForm.bank_sub_mode)) {
      if (!donationForm.cheque_number?.trim() || !donationForm.cheque_date || !donationForm.cheque_bank_name?.trim() || !donationForm.cheque_branch?.trim()) {
        setError(`Please enter ${donationForm.bank_sub_mode} number, date, bank name and branch.`);
        setSaving(false);
        return;
      }
    }

    try {
      const devoteeName = [
        donationForm.name_prefix?.trim(),
        donationForm.first_name?.trim(),
        donationForm.last_name?.trim(),
      ]
        .filter(Boolean)
        .join(' ');

      const finalPaymentMode =
        donationForm.payment_mode === 'Bank' ? donationForm.bank_sub_mode : donationForm.payment_mode;
      const selectedPaymentAccountId = donationForm.payment_account_id
        ? Number(donationForm.payment_account_id)
        : null;
      const selectedBank = paymentAccounts.bank_accounts.find(
        (acc) => String(acc.account_id) === String(selectedPaymentAccountId)
      );

      const response = await api.post('/api/v1/donations/', {
        devotee_name: devoteeName,
        devotee_phone: donationForm.devotee_phone,
        email: donationForm.email?.trim() || null,
        pan_number: donationForm.pan_number?.trim() || null,
        amount: amountNum,
        category: donationForm.category,
        payment_mode: finalPaymentMode,
        payment_sub_mode: donationForm.payment_mode === 'Bank' ? donationForm.bank_sub_mode : null,
        payment_account_id: selectedPaymentAccountId,
        bank_account_id:
          donationForm.payment_mode === 'Bank' && selectedBank?.bank_account_id
            ? selectedBank.bank_account_id
            : null,
        sender_upi_id:
          donationForm.payment_mode === 'Bank' && donationForm.bank_sub_mode === 'UPI'
            ? donationForm.sender_upi_id?.trim() || null
            : null,
        upi_reference_number:
          donationForm.payment_mode === 'Bank' && donationForm.bank_sub_mode === 'UPI'
            ? donationForm.upi_reference_number?.trim() || null
            : null,
        utr_number:
          donationForm.payment_mode === 'Bank' && donationForm.bank_sub_mode === 'Online'
            ? donationForm.utr_number?.trim() || null
            : null,
        payer_name:
          donationForm.payment_mode === 'Bank' &&
          ['Online', 'Cheque', 'DD'].includes(donationForm.bank_sub_mode)
            ? donationForm.payer_name?.trim() || null
            : null,
        cheque_number:
          donationForm.payment_mode === 'Bank' && ['Cheque', 'DD'].includes(donationForm.bank_sub_mode)
            ? donationForm.cheque_number?.trim() || null
            : null,
        cheque_date:
          donationForm.payment_mode === 'Bank' && ['Cheque', 'DD'].includes(donationForm.bank_sub_mode)
            ? donationForm.cheque_date || null
            : null,
        cheque_bank_name:
          donationForm.payment_mode === 'Bank' && ['Cheque', 'DD'].includes(donationForm.bank_sub_mode)
            ? donationForm.cheque_bank_name?.trim() || null
            : null,
        cheque_branch:
          donationForm.payment_mode === 'Bank' && ['Cheque', 'DD'].includes(donationForm.bank_sub_mode)
            ? donationForm.cheque_branch?.trim() || null
            : null,
        address: donationForm.address || null,
        pincode: donationForm.pincode || null,
        city: donationForm.city || null,
        state: donationForm.state || null,
        country: donationForm.country || 'India',
      });

      setSuccess(`Donation recorded successfully! Receipt: ${response.data.receipt_number || 'N/A'}`);
      setDonationForm(getInitialDonationForm());
      setFoundDevotee(null);
      setMobileVerified(false);
      setLookupStatus('idle');
      fetchDashboardStats();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      console.error('Donation error:', err);
      console.error('Error details:', err.response?.data);

      if (err.response?.status === 404) {
        setError('API endpoint not found. Please ensure the backend server is running on http://localhost:8000 and the endpoint /api/v1/donations/ exists.');
      } else if (err.response?.status === 500) {
        const errorDetail = err.response?.data?.detail || 'Unknown server error';
        setError(`Server error: ${errorDetail}. Please check backend logs.`);
      } else if (err.response?.status === 422) {
        const errorDetail = err.response?.data?.detail || 'Validation error';
        setError(`Validation error: ${Array.isArray(errorDetail) ? errorDetail.map(e => e.msg || e).join(', ') : errorDetail}`);
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.message) {
        setError(`Error: ${err.message}. Please check if backend is running.`);
      } else if (err.code === 'ECONNREFUSED' || err.code === 'ERR_NETWORK') {
        setError('Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000');
      } else {
        setError(`Error recording donation: ${JSON.stringify(err.response?.data || err.message || 'Unknown error')}. Please try again.`);
      }
    } finally {
      setSaving(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const safeAmount = (value) => {
    const amount = Number(value);
    return Number.isFinite(amount) ? amount : 0;
  };

  const formatCompactCurrency = (amount) => {
    const value = safeAmount(amount);
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)}Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
    if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
    return formatCurrency(value);
  };

  const formatShortDate = (value) => {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value).slice(0, 10) || '-';
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  };

  const getDonationDevoteeName = (donation) => (
    donation?.devotee?.name
    || donation?.devotee_name
    || donation?.donor_name
    || donation?.name
    || 'Devotee'
  );

  const getDonationCategory = (donation) => (
    donation?.category?.name
    || donation?.category
    || donation?.donation_category
    || 'General'
  );

  const getSevaName = (booking) => (
    booking?.seva_name
    || booking?.seva
    || booking?.seva_type
    || 'Seva'
  );

  const activeDevotees = new Set(
    recentDonations
      .map((donation) => String(donation.devotee_phone || donation.phone || donation.devotee?.phone || '').trim())
      .filter(Boolean)
  ).size;

  const donationBreakdown = Object.entries(
    recentDonations.reduce((bucket, donation) => {
      const category = getDonationCategory(donation);
      bucket[category] = (bucket[category] || 0) + safeAmount(donation.amount);
      return bucket;
    }, {})
  )
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 4);

  const maxBreakdownAmount = Math.max(...donationBreakdown.map((item) => item.value), 1);

  const paymentModes = ['Cash', 'Bank'];
  const canEditDevoteeDetails = mobileVerified && !searchingDevotee;

  const summaryCards = [
    {
      title: 'Donations Today',
      value: formatCurrency(stats.donations.today.amount),
      subtitle: `${stats.donations.today.count} donations`,
      icon: <CurrencyRupeeIcon />,
      color: '#0f766e',
      tone: '#e0f2f1',
    },
    {
      title: 'Month Collection',
      value: formatCurrency(stats.donations.month.amount),
      subtitle: `${stats.donations.month.count} donations`,
      icon: <ReceiptLongIcon />,
      color: '#b7791f',
      tone: '#fff7e6',
    },
    {
      title: 'Recent Donors',
      value: activeDevotees,
      subtitle: activeDevotees ? 'unique recent mobile numbers' : 'no recent donor data',
      icon: <GroupsIcon />,
      color: '#2563eb',
      tone: '#e8f1ff',
    },
    {
      title: 'Sevas Today',
      value: formatCurrency(stats.sevas.today.amount),
      subtitle: `${stats.sevas.today.count} bookings`,
      icon: <EventAvailableIcon />,
      color: '#c2410c',
      tone: '#fff1e6',
    },
  ];

  const performanceRows = [
    {
      label: 'Donations',
      today: stats.donations.today.amount,
      month: stats.donations.month.amount,
      year: stats.donations.year.amount,
      color: '#0f766e',
    },
    {
      label: 'Sevas',
      today: stats.sevas.today.amount,
      month: stats.sevas.month.amount,
      year: stats.sevas.year.amount,
      color: '#c2410c',
    },
  ];

  const maxPerformanceAmount = Math.max(...performanceRows.map((row) => safeAmount(row.year)), 1);

  if (loading) {
    return (
      <Layout>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
          <CircularProgress />
        </Box>
      </Layout>
    );
  }

  return (
    <Layout>
      <Box
        sx={{
          borderRadius: 2,
          p: { xs: 2.25, md: 3 },
          mb: 3,
          color: '#fff',
          background: 'linear-gradient(135deg, #173042 0%, #0f766e 58%, #b7791f 100%)',
          boxShadow: '0 10px 30px rgba(15, 48, 66, 0.18)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            opacity: 0.12,
            backgroundImage:
              'linear-gradient(90deg, rgba(255,255,255,0.18) 1px, transparent 1px), linear-gradient(rgba(255,255,255,0.18) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
        <Box sx={{ position: 'relative', display: 'flex', alignItems: { xs: 'flex-start', sm: 'center' }, justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <DashboardIcon fontSize="small" />
              <Typography variant="overline" sx={{ letterSpacing: 0, fontWeight: 700, opacity: 0.85 }}>
                MandirMitra Admin
              </Typography>
            </Stack>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 800, letterSpacing: 0 }}>
              Temple Operations Dashboard
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.75, opacity: 0.9 }}>
              Daily temple operations overview.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              variant="contained"
              onClick={() => navigate('/donations')}
              sx={{ bgcolor: '#fff', color: '#173042', '&:hover': { bgcolor: '#f8fafc' } }}
            >
              Donations
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate('/sevas')}
              sx={{ borderColor: 'rgba(255,255,255,0.75)', color: '#fff', '&:hover': { borderColor: '#fff', bgcolor: 'rgba(255,255,255,0.08)' } }}
            >
              Book Seva
            </Button>
          </Stack>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {paymentAccountsWarning && (
        <Alert severity="warning" sx={{ mb: 3 }} onClose={() => setPaymentAccountsWarning('')}>
          {paymentAccountsWarning}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      <Grid container spacing={2.25} sx={{ mb: 3 }}>
        {summaryCards.map((stat) => (
          <Grid item xs={12} sm={6} lg={3} key={stat.title}>
            <Card sx={{ height: '100%', borderRadius: 2, boxShadow: '0 8px 24px rgba(15, 23, 42, 0.08)', border: '1px solid #eee7d8' }}>
              <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 } }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 700 }}>
                      {stat.title}
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 0.75, fontWeight: 800, letterSpacing: 0 }}>
                      {stat.value}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {stat.subtitle}
                    </Typography>
                  </Box>
                  <Box sx={{ width: 44, height: 44, borderRadius: '50%', display: 'grid', placeItems: 'center', bgcolor: stat.tone, color: stat.color }}>
                    {stat.icon}
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 2.5, borderRadius: 2, boxShadow: 2 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <TrendingUpIcon sx={{ color: '#0f766e' }} />
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Collection Performance
              </Typography>
            </Stack>
            <Grid container spacing={2}>
              {performanceRows.map((row) => (
                <Grid item xs={12} key={row.label}>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '120px 1fr 120px' }, gap: 1.5, alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {row.label}
                    </Typography>
                    <Box sx={{ height: 12, borderRadius: 999, bgcolor: '#f1f5f9', overflow: 'hidden' }}>
                      <Box sx={{ width: `${Math.max(4, Math.round((safeAmount(row.year) / maxPerformanceAmount) * 100))}%`, height: '100%', bgcolor: row.color }} />
                    </Box>
                    <Typography variant="body2" align="right" sx={{ fontWeight: 700 }}>
                      {formatCompactCurrency(row.year)}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    <Chip size="small" label={`Today ${formatCompactCurrency(row.today)}`} />
                    <Chip size="small" label={`Month ${formatCompactCurrency(row.month)}`} />
                    <Chip size="small" label={`Year ${formatCompactCurrency(row.year)}`} />
                  </Stack>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 2.5, borderRadius: 2, boxShadow: 2, height: '100%' }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <VolunteerActivismIcon sx={{ color: '#b7791f' }} />
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Recent Donation Purpose
              </Typography>
            </Stack>
            {donationBreakdown.length > 0 ? (
              <Stack spacing={1.4}>
                {donationBreakdown.map((item) => (
                  <Box key={item.label}>
                    <Stack direction="row" justifyContent="space-between" spacing={1}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{item.label}</Typography>
                      <Typography variant="body2">{formatCompactCurrency(item.value)}</Typography>
                    </Stack>
                    <Box sx={{ mt: 0.75, height: 8, borderRadius: 999, bgcolor: '#f3ead7', overflow: 'hidden' }}>
                      <Box sx={{ width: `${Math.max(6, Math.round((item.value / maxBreakdownAmount) * 100))}%`, height: '100%', bgcolor: '#b7791f' }} />
                    </Box>
                  </Box>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Recent donation purpose mix will appear after donations are recorded.
              </Typography>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 2.5, borderRadius: 2, boxShadow: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Recent Donations
              </Typography>
              <Button size="small" onClick={() => navigate('/donations')}>View All</Button>
            </Stack>
            <Divider sx={{ mb: 1 }} />
            {recentDonations.length > 0 ? (
              <Stack spacing={0.75}>
                {recentDonations.slice(0, 5).map((donation) => (
                  <Box key={donation.id || donation.donation_id || donation.receipt_number} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '88px 1fr 110px' }, gap: 1.5, py: 1, alignItems: 'center' }}>
                    <Typography variant="body2" color="text.secondary">{formatShortDate(donation.donation_date || donation.created_at)}</Typography>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{getDonationDevoteeName(donation)}</Typography>
                      <Typography variant="caption" color="text.secondary">{getDonationCategory(donation)} • {donation.payment_mode || 'Cash'}</Typography>
                    </Box>
                    <Typography variant="body2" align="right" sx={{ fontWeight: 800 }}>{formatCurrency(donation.amount)}</Typography>
                  </Box>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                No recent donations available.
              </Typography>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 2.5, borderRadius: 2, boxShadow: 2, height: '100%' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Upcoming / Recent Sevas
              </Typography>
              <Button size="small" onClick={() => navigate('/sevas')}>Book</Button>
            </Stack>
            <Divider sx={{ mb: 1 }} />
            {recentSevas.length > 0 ? (
              <Stack spacing={1}>
                {recentSevas.slice(0, 5).map((booking) => (
                  <Box key={booking.id || booking.booking_id || booking.receipt_number} sx={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 1.5, py: 1 }}>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{getSevaName(booking)}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {booking.devotee_name || booking.devotee_names || 'Devotee'}
                      </Typography>
                    </Box>
                    <Chip size="small" icon={<EventIcon />} label={formatShortDate(booking.booking_date || booking.created_at)} />
                  </Box>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                No seva bookings available.
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        {/* Donation Entry Form */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, boxShadow: 2 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
              Quick Donation Entry
            </Typography>
            <Box component="form" onSubmit={handleDonationSubmit}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={8}>
                  <TextField
                    fullWidth
                    label="Phone Number"
                    value={donationForm.devotee_phone}
                    onChange={(e) => handleDonationChange('devotee_phone', e.target.value)}
                    required
                    size="small"
                    inputProps={{ maxLength: 10 }}
                    helperText={
                      !mobileVerified
                        ? 'Search by mobile first. If not found, enter devotee details manually.'
                        : lookupStatus === 'found'
                          ? 'Existing devotee loaded. You can review/edit before saving.'
                          : 'No devotee found. Enter details and continue.'
                    }
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={handleSearchByMobile}
                    disabled={searchingDevotee || donationForm.devotee_phone.length !== 10}
                    sx={{ height: '40px' }}
                  >
                    {searchingDevotee ? <CircularProgress size={20} /> : 'Search Mobile'}
                  </Button>
                </Grid>
                {lookupStatus === 'found' && foundDevotee && (
                  <Grid item xs={12}>
                    <Alert severity="success">
                      Devotee found for {foundDevotee.phone}. Details auto-filled.
                    </Alert>
                  </Grid>
                )}
                {lookupStatus === 'not_found' && (
                  <Grid item xs={12}>
                    <Alert severity="info">
                      No devotee found for this mobile number. Please enter details and proceed.
                    </Alert>
                  </Grid>
                )}
                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    select
                    label="Prefix"
                    value={donationForm.name_prefix}
                    onChange={(e) => handleDonationChange('name_prefix', e.target.value)}
                    required
                    size="small"
                    disabled={!canEditDevoteeDetails}
                  >
                    {namePrefixes.map((prefix) => (
                      <MenuItem key={prefix} value={prefix}>
                        {prefix}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={5}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={donationForm.first_name}
                    onChange={(e) => handleDonationChange('first_name', e.target.value)}
                    required
                    size="small"
                    disabled={!canEditDevoteeDetails}
                    inputRef={firstNameInputRef}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={donationForm.last_name}
                    onChange={(e) => handleDonationChange('last_name', e.target.value)}
                    required
                    size="small"
                    disabled={!canEditDevoteeDetails}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Email (Optional)"
                    type="email"
                    placeholder="devotee@example.com"
                    value={donationForm.email || ''}
                    onChange={(e) => handleDonationChange('email', e.target.value)}
                    size="small"
                    disabled={!canEditDevoteeDetails}
                    helperText="For sending donation receipt via email"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="PAN"
                    placeholder="PAN details (optional)"
                    value={donationForm.pan_number || ''}
                    onChange={(e) => handleDonationChange('pan_number', e.target.value.toUpperCase())}
                    size="small"
                    inputProps={{ maxLength: 10 }}
                    disabled={!canEditDevoteeDetails}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Amount (INR)"
                    type="number"
                    value={donationForm.amount}
                    onChange={(e) => handleDonationChange('amount', e.target.value)}
                    required
                    size="small"
                    inputProps={{ min: 1, step: 0.01 }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Street Address (Optional)"
                    placeholder="House/Flat No., Building, Street, Area"
                    value={donationForm.address}
                    onChange={(e) => handleDonationChange('address', e.target.value)}
                    size="small"
                    multiline
                    rows={2}
                    disabled={!canEditDevoteeDetails}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="PIN Code"
                    placeholder="6 digit PIN code"
                    value={donationForm.pincode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                      handleDonationChange('pincode', value);
                    }}
                    size="small"
                    inputProps={{ maxLength: 6 }}
                    disabled={!canEditDevoteeDetails}
                    InputProps={{
                      endAdornment: pincodeLoading && (
                        <InputAdornment position="end">
                          <CircularProgress size={20} />
                        </InputAdornment>
                      )
                    }}
                    helperText={donationForm.pincode.length === 6 ? "City & State will auto-fill" : ""}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="City"
                    placeholder="City"
                    value={donationForm.city}
                    onChange={(e) => handleDonationChange('city', e.target.value)}
                    size="small"
                    disabled={!canEditDevoteeDetails || pincodeLoading}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="State"
                    placeholder="State"
                    value={donationForm.state}
                    onChange={(e) => handleDonationChange('state', e.target.value)}
                    size="small"
                    disabled={!canEditDevoteeDetails || pincodeLoading}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Country"
                    placeholder="Country"
                    value={donationForm.country}
                    onChange={(e) => handleDonationChange('country', e.target.value)}
                    size="small"
                    disabled={!canEditDevoteeDetails}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Category"
                    value={donationForm.category}
                    onChange={(e) => handleDonationChange('category', e.target.value)}
                    required
                    size="small"
                  >
                    {categories.map((cat) => (
                      <MenuItem key={cat} value={cat}>
                        {cat}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    select
                    label="Payment Mode"
                    value={donationForm.payment_mode}
                    onChange={(e) => handleDonationChange('payment_mode', e.target.value)}
                    required
                    size="small"
                  >
                    {paymentModes.map((mode) => (
                      <MenuItem key={mode} value={mode}>
                        {mode}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                {donationForm.payment_mode === 'Cash' && (
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      select
                      label="Cash Account Code"
                      value={donationForm.payment_account_id}
                      onChange={(e) => handleDonationChange('payment_account_id', e.target.value)}
                      required
                      size="small"
                      helperText="Select the cash account"
                    >
                      {paymentAccounts.cash_accounts.length === 0 ? (
                        <MenuItem value="" disabled>
                          No cash accounts found
                        </MenuItem>
                      ) : (
                        paymentAccounts.cash_accounts.map((acc) => (
                          <MenuItem key={acc.account_id} value={String(acc.account_id)}>
                            {acc.account_code} - {acc.account_name}
                          </MenuItem>
                        ))
                      )}
                    </TextField>
                  </Grid>
                )}
                {donationForm.payment_mode === 'Bank' && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        select
                        label="Bank Account Code"
                        value={donationForm.payment_account_id}
                        onChange={(e) => handleDonationChange('payment_account_id', e.target.value)}
                        required
                        size="small"
                        helperText="Select the bank account"
                      >
                        {paymentAccounts.bank_accounts.length === 0 ? (
                          <MenuItem value="" disabled>
                            No bank accounts found
                          </MenuItem>
                        ) : (
                          paymentAccounts.bank_accounts.map((acc) => (
                            <MenuItem key={acc.account_id} value={String(acc.account_id)}>
                              {acc.account_code} - {acc.account_name}
                            </MenuItem>
                          ))
                        )}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        select
                        label="Bank Sub-Category"
                        value={donationForm.bank_sub_mode}
                        onChange={(e) => handleDonationChange('bank_sub_mode', e.target.value)}
                        required
                        size="small"
                      >
                        {bankSubModeOptions.map((mode) => (
                          <MenuItem key={mode.value} value={mode.value}>
                            {mode.label}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>

                    {donationForm.bank_sub_mode === 'UPI' && (
                      <>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="UPI Transaction Reference"
                            value={donationForm.upi_reference_number}
                            onChange={(e) => handleDonationChange('upi_reference_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Sender UPI ID (Optional)"
                            value={donationForm.sender_upi_id}
                            onChange={(e) => handleDonationChange('sender_upi_id', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}

                    {donationForm.bank_sub_mode === 'Online' && (
                      <>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="UTR Reference Number"
                            value={donationForm.utr_number}
                            onChange={(e) => handleDonationChange('utr_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Payer Name (Optional)"
                            value={donationForm.payer_name}
                            onChange={(e) => handleDonationChange('payer_name', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}

                    {['Cheque', 'DD'].includes(donationForm.bank_sub_mode) && (
                      <>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label={`${donationForm.bank_sub_mode} Number`}
                            value={donationForm.cheque_number}
                            onChange={(e) => handleDonationChange('cheque_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label={`${donationForm.bank_sub_mode} Date`}
                            type="date"
                            value={donationForm.cheque_date}
                            onChange={(e) => handleDonationChange('cheque_date', e.target.value)}
                            required
                            size="small"
                            InputLabelProps={{ shrink: true }}
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Drawn On Bank Name"
                            value={donationForm.cheque_bank_name}
                            onChange={(e) => handleDonationChange('cheque_bank_name', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Branch Name"
                            value={donationForm.cheque_branch}
                            onChange={(e) => handleDonationChange('cheque_branch', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Payer Name (Optional)"
                            value={donationForm.payer_name}
                            onChange={(e) => handleDonationChange('payer_name', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}
                  </>
                )}
                <Grid item xs={12}>
                  <Button
                    type="submit"
                    variant="contained"
                    fullWidth
                    startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                    disabled={saving}
                    size="large"
                  >
                    {saving ? 'Saving...' : 'Record Donation'}
                  </Button>
                </Grid>
              </Grid>
            </Box>
          </Paper>
        </Grid>

        {/* Panchang Display - Side by side with donation form */}
        <Grid item xs={12} md={6}>
          {panchangData ? (
            <>
              <PanchangDisplay
                data={panchangData}
                settings={panchangData}
                compact={true}
              />
              <Button
                variant="outlined"
                fullWidth
                size="small"
                sx={{ mt: 2 }}
                onClick={() => navigate('/panchang')}
              >
                View Full Panchang</Button>
            </>
          ) : (
            <Paper sx={{ p: 3, boxShadow: 2, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Panchang data will be displayed here once connected to panchang service API.
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Layout>
  );
}

export default Dashboard;
