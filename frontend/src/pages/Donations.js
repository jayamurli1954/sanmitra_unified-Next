import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  Grid,
  MenuItem,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import PrintIcon from '@mui/icons-material/Print';
import Layout from '../components/Layout';
import api from '../services/api';
import { ACTIVE_TEMPLE_EVENT } from '../utils/activeTemple';

const createEmptyDonationEntry = () => ({
  name_prefix: 'Sri',
  devotee_name: '',
  devotee_phone: '',
  email: '',
  pan_number: '',
  donation_nature: 'monetary', // monetary | sponsorship | material | precious
  amount: '',
  category: '',
  payment_mode: 'Cash',
  payment_account_id: '',
  bank_sub_mode: '',
  sender_upi_id: '',
  upi_reference_number: '',
  card_number: '',
  card_holder_name: '',
  utr_number: '',
  payer_name: '',
  cheque_number: '',
  cheque_date: '',
  cheque_bank_name: '',
  cheque_branch: '',
  item_name: '',
  item_description: '',
  quantity: '',
  unit: '',
  event_name: '',
  event_date: '',
  sponsorship_category: '',
  appraised_by: '',
  appraisal_date: '',
  purity: '',
  weight_gross: '',
  weight_net: '',
  notes: '',
  mobile_verified: false,
  lookup_status: 'idle', // idle | found | not_found
  searching: false,
});

function Donations() {
  const [donations, setDonations] = useState([createEmptyDonationEntry()]);
  const [categories, setCategories] = useState([]);
  const [paymentAccounts, setPaymentAccounts] = useState({ cash_accounts: [], bank_accounts: [] });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [donationList, setDonationList] = useState([]);

  const paymentModes = ['Cash', 'Bank'];
  const donationNatures = [
    { value: 'monetary', label: 'Monetary (Cash/Bank)' },
    { value: 'sponsorship', label: 'Sponsorship (Service/Event)' },
    { value: 'material', label: 'Physical Materials' },
    { value: 'precious', label: 'Precious Articles' },
  ];
  const bankSubModeOptions = [
    { value: 'UPI', label: 'UPI' },
    { value: 'Online', label: 'Online Transfer' },
    { value: 'Cheque', label: 'Cheque' },
    { value: 'Card', label: 'Card' },
  ];
  const sponsorshipCategories = [
    'Annadanam Sponsorship',
    'Flower Decoration',
    'Temple Lighting',
    'Pooja Samagri Sponsorship',
    'Festival Sponsorship',
    'Other Sponsorship',
  ];
  const inventoryUnits = ['kg', 'grams', 'litre', 'ml', 'packets', 'pieces', 'bags', 'boxes'];
  const emptyBankPaymentFields = {
    sender_upi_id: '',
    upi_reference_number: '',
    card_number: '',
    card_holder_name: '',
    utr_number: '',
    payer_name: '',
    cheque_number: '',
    cheque_date: '',
    cheque_bank_name: '',
    cheque_branch: '',
  };

  const resetDonationRecording = () => {
    setDonations([createEmptyDonationEntry()]);
  };

  useEffect(() => {
    fetchCategories();
    fetchPaymentAccounts();
    fetchDonations();
  }, []);

  useEffect(() => {
    const handleActiveTempleChange = () => {
      fetchCategories();
      fetchPaymentAccounts();
      fetchDonations();
    };

    window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
    return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
  }, []);

  const fetchCategories = async () => {
    const fallbackCategories = [
      'General Donation',
      'Annadanam',
      'Construction Fund',
      'Gold/Silver Donation',
      'Corpus Fund'
    ];

    try {
      const response = await api.get('/api/v1/donations/categories/');
      const categoryNames = Array.isArray(response.data)
        ? response.data.map((cat) => cat?.name).filter(Boolean)
        : [];
      setCategories(categoryNames.length > 0 ? categoryNames : fallbackCategories);
    } catch (err) {
      console.error('Error fetching categories:', err);
      setCategories(fallbackCategories);
    }
  };

  const fetchDonations = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/donations');
      if (response.data) {
        setDonationList(response.data);
      }
    } catch (err) {
      console.error('Error fetching donations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddRow = () => {
    if (donations.length < 5) {
      setDonations([...donations, createEmptyDonationEntry()]);
    }
  };

  const fetchPaymentAccounts = async () => {
    try {
      const response = await api.get('/api/v1/donations/payment-accounts');
      const data = response?.data || {};
      setPaymentAccounts({
        cash_accounts: Array.isArray(data.cash_accounts) ? data.cash_accounts : [],
        bank_accounts: Array.isArray(data.bank_accounts) ? data.bank_accounts : [],
      });
    } catch (err) {
      console.error('Error fetching payment accounts:', err);
      setPaymentAccounts({ cash_accounts: [], bank_accounts: [] });
    }
  };

  const handleRemoveRow = (index) => {
    if (donations.length > 1) {
      setDonations(donations.filter((_, i) => i !== index));
    }
  };

  const handleChange = (index, field, value) => {
    if (error) setError('');
    if (success) setSuccess('');
    const updated = [...donations];
    if (field === 'devotee_phone') {
      const normalizedPhone = value.replace(/\D/g, '').slice(0, 10);
      updated[index].devotee_phone = normalizedPhone;
      updated[index].mobile_verified = false;
      updated[index].lookup_status = 'idle';
      updated[index].searching = false;
      updated[index].devotee_name = '';
      updated[index].email = '';
      updated[index].pan_number = '';
      updated[index].name_prefix = 'Sri';
    } else {
      updated[index][field] = value;
      if (field === 'donation_nature' && value !== 'monetary') {
        updated[index].payment_mode = 'Cash';
        updated[index].payment_account_id = '';
        updated[index].bank_sub_mode = '';
        Object.assign(updated[index], emptyBankPaymentFields);
        updated[index].amount = '';
      }
      if (field === 'payment_mode') {
        updated[index].payment_account_id = '';
      }
      if (field === 'payment_mode' && value !== 'Bank') {
        updated[index].bank_sub_mode = '';
        Object.assign(updated[index], emptyBankPaymentFields);
      }
      if (field === 'bank_sub_mode') {
        Object.assign(updated[index], emptyBankPaymentFields);
      }
    }

    setDonations(updated);
  };

  const splitFullName = (fullName = '') => {
    const trimmed = (fullName || '').trim();
    if (!trimmed) {
      return { first: '', last: '' };
    }
    const parts = trimmed.split(/\s+/).filter(Boolean);
    if (parts.length === 1) {
      return { first: parts[0], last: '' };
    }
    return { first: parts[0], last: parts.slice(1).join(' ') };
  };

  const isValidPan = (value) => /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(String(value || '').trim().toUpperCase());

  const handleSearchByMobile = async (index) => {
    const row = donations[index];
    const phone = (row.devotee_phone || '').trim();
    if (phone.length !== 10) {
      setError(`Entry ${index + 1}: Please enter a valid 10-digit mobile number`);
      return;
    }

    setError('');
    setSuccess('');
    setDonations((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], searching: true, lookup_status: 'idle', mobile_verified: false };
      return next;
    });

    try {
      const response = await api.get(`/api/v1/devotees/search/by-mobile/${phone}`);
      const list = Array.isArray(response.data) ? response.data : [];
      const devotee = list[0];

      if (devotee) {
        const fullName = devotee.name || `${devotee.first_name || ''} ${devotee.last_name || ''}`.trim();
        const parsed = splitFullName(fullName);
        const displayName = `${parsed.first} ${parsed.last}`.trim() || fullName;

        setDonations((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            devotee_phone: phone,
            name_prefix: devotee.name_prefix || next[index].name_prefix || 'Sri',
            devotee_name: displayName,
            email: devotee.email || '',
            pan_number: devotee.pan_number || devotee.pan || '',
            mobile_verified: true,
            lookup_status: 'found',
            searching: false,
          };
          return next;
        });
      } else {
        setDonations((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            devotee_phone: phone,
            devotee_name: '',
            email: '',
            pan_number: '',
            mobile_verified: true,
            lookup_status: 'not_found',
            searching: false,
          };
          return next;
        });
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setDonations((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            devotee_phone: phone,
            devotee_name: '',
            email: '',
            pan_number: '',
            mobile_verified: true,
            lookup_status: 'not_found',
            searching: false,
          };
          return next;
        });
      } else {
        setDonations((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            searching: false,
            mobile_verified: false,
            lookup_status: 'idle',
          };
          return next;
        });
        setError(`Entry ${index + 1}: Could not search devotee right now. Please try again.`);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const entriesToSubmit = donations
        .map((d, idx) => ({ ...d, _row_index: idx }))
        .filter((d) => d.devotee_name || d.devotee_phone || d.amount || d.category);

      if (entriesToSubmit.length === 0) {
        setError('Please fill at least one donation entry');
        setSaving(false);
        return;
      }

      for (let i = 0; i < entriesToSubmit.length; i++) {
        const entry = entriesToSubmit[i];
        const entryNo = entry._row_index + 1;
        const isMonetary = entry.donation_nature === 'monetary';
        const isSponsorship = entry.donation_nature === 'sponsorship';
        const isMaterial = entry.donation_nature === 'material';
        const isPrecious = entry.donation_nature === 'precious';

        if (!entry.devotee_phone || entry.devotee_phone.length !== 10) {
          setError(`Entry ${entryNo}: Please enter a valid 10-digit mobile number`);
          setSaving(false);
          return;
        }
        if (!entry.mobile_verified) {
          setError(`Entry ${entryNo}: Search mobile number first. If not found, enter devotee name and continue.`);
          setSaving(false);
          return;
        }
        if (!entry.devotee_name || !entry.category) {
          setError(`Entry ${entryNo}: Please complete devotee name and category`);
          setSaving(false);
          return;
        }
        if (entry.pan_number && !isValidPan(entry.pan_number)) {
          setError(`Entry ${entryNo}: PAN format must be AAAAA9999A`);
          setSaving(false);
          return;
        }
        if (isMonetary && (!entry.amount || Number(entry.amount) <= 0)) {
          setError(`Entry ${entryNo}: Please enter donation amount`);
          setSaving(false);
          return;
        }
        if (!isMonetary && (!entry.amount || Number(entry.amount) <= 0)) {
          setError(`Entry ${entryNo}: Please enter assessed value for in-kind donation`);
          setSaving(false);
          return;
        }
        if (!isMonetary && !entry.item_name?.trim()) {
          setError(`Entry ${entryNo}: Please enter item/service name`);
          setSaving(false);
          return;
        }
        if (isMonetary && entry.payment_mode === 'Bank' && !entry.bank_sub_mode) {
          setError(`Entry ${entryNo}: Please select Bank Sub-Category (UPI/Card/Cheque/Online Transfer)`);
          setSaving(false);
          return;
        }
        if (isMonetary && !entry.payment_account_id) {
          setError(
            `Entry ${entryNo}: Please select ${
              entry.payment_mode === 'Bank' ? 'bank' : 'cash'
            } account code`
          );
          setSaving(false);
          return;
        }
        if (isMonetary && entry.payment_mode === 'Bank' && entry.bank_sub_mode === 'UPI') {
          if (!entry.upi_reference_number?.trim()) {
            setError(`Entry ${entryNo}: Please enter UPI transaction reference`);
            setSaving(false);
            return;
          }
        }
        if (isMonetary && entry.payment_mode === 'Bank' && entry.bank_sub_mode === 'Card') {
          if (!entry.card_number?.trim()) {
            setError(`Entry ${entryNo}: Please enter card number / transaction reference`);
            setSaving(false);
            return;
          }
        }
        if (isMonetary && entry.payment_mode === 'Bank' && entry.bank_sub_mode === 'Online') {
          if (!entry.utr_number?.trim()) {
            setError(`Entry ${entryNo}: Please enter UTR reference number`);
            setSaving(false);
            return;
          }
        }
        if (isMonetary && entry.payment_mode === 'Bank' && entry.bank_sub_mode === 'Cheque') {
          if (
            !entry.cheque_number?.trim() ||
            !entry.cheque_date ||
            !entry.cheque_bank_name?.trim() ||
            !entry.cheque_branch?.trim()
          ) {
            setError(`Entry ${entryNo}: Please enter cheque number, date, bank name and branch`);
            setSaving(false);
            return;
          }
        }
        if (isSponsorship && !entry.sponsorship_category) {
          setError(`Entry ${entryNo}: Please select sponsorship category`);
          setSaving(false);
          return;
        }
        if (isMaterial && (!entry.quantity || Number(entry.quantity) <= 0 || !entry.unit)) {
          setError(`Entry ${entryNo}: Please enter quantity and unit for physical materials`);
          setSaving(false);
          return;
        }
        if (isPrecious && !entry.appraised_by?.trim()) {
          setError(`Entry ${entryNo}: Please enter appraiser name for precious articles`);
          setSaving(false);
          return;
        }
      }

      // Save each donation
      const promises = entriesToSubmit.map((donation) => {
        const isMonetary = donation.donation_nature === 'monetary';
        const isSponsorship = donation.donation_nature === 'sponsorship';
        const isMaterial = donation.donation_nature === 'material';
        const isPrecious = donation.donation_nature === 'precious';

        const inkindSubtype = isSponsorship
          ? 'event_sponsorship'
          : isMaterial
            ? 'inventory'
            : isPrecious
              ? 'asset'
              : null;

        const selectedPaymentAccountId = donation.payment_account_id
          ? Number(donation.payment_account_id)
          : null;
        const selectedBank = paymentAccounts.bank_accounts.find(
          (acc) => String(acc.account_id) === String(selectedPaymentAccountId)
        );

        return api.post('/api/v1/donations', {
          name_prefix: donation.name_prefix,
          devotee_name: donation.devotee_name,
          devotee_phone: donation.devotee_phone,
          email: donation.email?.trim() || null,
          pan_number: donation.pan_number?.trim() || null,
          category: donation.category,
          donation_type: isMonetary ? 'cash' : 'in_kind',
          amount: parseFloat(donation.amount),
          payment_mode: isMonetary ? donation.payment_mode : null,
          payment_account_id: isMonetary ? selectedPaymentAccountId : null,
          bank_account_id:
            isMonetary && donation.payment_mode === 'Bank' && selectedBank?.bank_account_id
              ? selectedBank.bank_account_id
              : null,
          payment_sub_mode:
            isMonetary && donation.payment_mode === 'Bank' ? donation.bank_sub_mode : null,
          sender_upi_id:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'UPI'
              ? donation.sender_upi_id?.trim() || null
              : null,
          upi_reference_number:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'UPI'
              ? donation.upi_reference_number?.trim() || null
              : null,
          card_number:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Card'
              ? donation.card_number?.trim() || null
              : null,
          card_holder_name:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Card'
              ? donation.card_holder_name?.trim() || null
              : null,
          utr_number:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Online'
              ? donation.utr_number?.trim() || null
              : null,
          payer_name:
            isMonetary &&
            donation.payment_mode === 'Bank' &&
            (donation.bank_sub_mode === 'Online' || donation.bank_sub_mode === 'Cheque')
              ? donation.payer_name?.trim() || null
              : null,
          cheque_number:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Cheque'
              ? donation.cheque_number?.trim() || null
              : null,
          cheque_date:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Cheque'
              ? donation.cheque_date || null
              : null,
          cheque_bank_name:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Cheque'
              ? donation.cheque_bank_name?.trim() || null
              : null,
          cheque_branch:
            isMonetary && donation.payment_mode === 'Bank' && donation.bank_sub_mode === 'Cheque'
              ? donation.cheque_branch?.trim() || null
              : null,
          notes: donation.notes?.trim() || null,
          inkind_subtype: !isMonetary ? inkindSubtype : null,
          item_name: !isMonetary ? donation.item_name?.trim() : null,
          item_description: !isMonetary ? donation.item_description?.trim() || null : null,
          value_assessed: !isMonetary ? parseFloat(donation.amount) : null,
          quantity: isMaterial ? parseFloat(donation.quantity) : null,
          unit: isMaterial ? donation.unit : null,
          event_name: isSponsorship ? donation.event_name?.trim() || null : null,
          event_date: isSponsorship && donation.event_date ? donation.event_date : null,
          sponsorship_category: isSponsorship ? donation.sponsorship_category : null,
          appraised_by: isPrecious ? donation.appraised_by?.trim() || null : null,
          appraisal_date: isPrecious && donation.appraisal_date ? donation.appraisal_date : null,
          purity: isPrecious ? donation.purity?.trim() || null : null,
          weight_gross: isPrecious && donation.weight_gross ? parseFloat(donation.weight_gross) : null,
          weight_net: isPrecious && donation.weight_net ? parseFloat(donation.weight_net) : null,
        });
      });

      await Promise.all(promises);

      setSuccess(`Successfully recorded ${entriesToSubmit.length} donation(s)!`);
      resetDonationRecording();
      fetchDonations();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error recording donations');
      resetDonationRecording();
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

  const handleDownloadReceipt = async (donationId, receiptNumber) => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/donations/${donationId}/receipt/pdf`, {
        responseType: 'blob',
        params: { lang: 'kannada' },
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `receipt_${receiptNumber || donationId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading receipt:', err);
      setError('Failed to download receipt');
    } finally {
      setLoading(false);
    }
  };

  const handlePrintReceipt = async (donationId, _receiptNumber) => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/donations/${donationId}/receipt/pdf`, {
        responseType: 'blob',
        params: { lang: 'kannada' },
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const printWindow = window.open(url, '_blank');
      if (!printWindow) {
        throw new Error('Pop-up blocked. Please allow pop-ups to print receipts.');
      }
      printWindow.onload = () => {
        printWindow.focus();
        printWindow.print();
      };
      setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch (err) {
      console.error('Error printing receipt:', err);
      setError(err.message || 'Failed to print receipt');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Donations
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      <Paper sx={{ p: 3, mt: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Record Donations (Up to 5 entries)
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAddRow}
            disabled={donations.length >= 5}
          >
            Add Entry
          </Button>
        </Box>

        <Box component="form" onSubmit={handleSubmit}>
          {donations.map((donation, index) => (
            <Paper key={index} sx={{ p: 2, mb: 2, bgcolor: '#f9f9f9' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                  Entry {index + 1}
                </Typography>
                {donations.length > 1 && (
                  <IconButton
                    color="error"
                    onClick={() => handleRemoveRow(index)}
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                )}
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={1} sx={{ order: 3 }}>
                  <TextField
                    fullWidth
                    select
                    label="Prefix"
                    value={donation.name_prefix}
                    onChange={(e) => handleChange(index, 'name_prefix', e.target.value)}
                    required
                    size="small"
                    disabled={!donation.mobile_verified || donation.searching}
                  >
                    {['Sri', 'Smt.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'M/s.'].map((prefix) => (
                      <MenuItem key={prefix} value={prefix}>
                        {prefix}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6} md={2} sx={{ order: 4 }}>
                  <TextField
                    fullWidth
                    label="Devotee Name"
                    value={donation.devotee_name}
                    onChange={(e) => handleChange(index, 'devotee_name', e.target.value)}
                    required
                    size="small"
                    disabled={!donation.mobile_verified || donation.searching}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3} sx={{ order: 5 }}>
                  <TextField
                    fullWidth
                    label="Email Address"
                    placeholder="Enter email address (optional)"
                    value={donation.email}
                    onChange={(e) => handleChange(index, 'email', e.target.value)}
                    size="small"
                    disabled={!donation.mobile_verified || donation.searching}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={2.5} sx={{ order: 5 }}>
                  <TextField
                    fullWidth
                    label="PAN"
                    placeholder="PAN details (optional)"
                    value={donation.pan_number}
                    onChange={(e) => handleChange(index, 'pan_number', e.target.value.toUpperCase())}
                    size="small"
                    inputProps={{ maxLength: 10 }}
                    disabled={!donation.mobile_verified || donation.searching}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={2} sx={{ order: -2 }}>
                  <TextField
                    fullWidth
                    label="Phone"
                    value={donation.devotee_phone}
                    onChange={(e) => handleChange(index, 'devotee_phone', e.target.value)}
                    required
                    size="small"
                    inputProps={{ maxLength: 10 }}
                    helperText={
                      !donation.mobile_verified
                        ? 'Search mobile first'
                        : donation.lookup_status === 'found'
                          ? 'Devotee found'
                          : 'No devotee found, enter name'
                    }
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={1.5} sx={{ order: -1 }}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={() => handleSearchByMobile(index)}
                    disabled={donation.searching || donation.devotee_phone.length !== 10}
                    sx={{ height: '40px' }}
                  >
                    {donation.searching ? <CircularProgress size={18} /> : 'Search'}
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={2.5}>
                  <TextField
                    fullWidth
                    select
                    label="Donation Nature"
                    value={donation.donation_nature}
                    onChange={(e) => handleChange(index, 'donation_nature', e.target.value)}
                    required
                    size="small"
                  >
                    {donationNatures.map((nature) => (
                      <MenuItem key={nature.value} value={nature.value}>
                        {nature.label}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <TextField
                    fullWidth
                    label={donation.donation_nature === 'monetary' ? 'Amount (₹)' : 'Assessed Value (₹)'}
                    type="number"
                    value={donation.amount}
                    onChange={(e) => handleChange(index, 'amount', e.target.value)}
                    required
                    size="small"
                    inputProps={{ min: 1, step: 0.01 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={2.5}>
                  <TextField
                    fullWidth
                    select
                    label="Category"
                    value={donation.category}
                    onChange={(e) => handleChange(index, 'category', e.target.value)}
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
                <Grid item xs={12} sm={6} md={2.5}>
                  <TextField
                    fullWidth
                    select
                    label="Payment Mode"
                    value={donation.payment_mode}
                    onChange={(e) => handleChange(index, 'payment_mode', e.target.value)}
                    required={donation.donation_nature === 'monetary'}
                    disabled={donation.donation_nature !== 'monetary'}
                    size="small"
                  >
                    {paymentModes.map((mode) => (
                      <MenuItem key={mode} value={mode}>
                        {mode}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                {donation.donation_nature === 'monetary' && donation.payment_mode === 'Cash' && (
                  <Grid item xs={12} sm={6} md={3.5}>
                    <TextField
                      fullWidth
                      select
                      label="Cash Account Code"
                      value={donation.payment_account_id}
                      onChange={(e) => handleChange(index, 'payment_account_id', e.target.value)}
                      required
                      size="small"
                      helperText="Select the cash account to credit/debit"
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
                {donation.donation_nature === 'monetary' && donation.payment_mode === 'Bank' && (
                  <Grid item xs={12} sm={6} md={3.5}>
                    <TextField
                      fullWidth
                      select
                      label="Bank Account Code"
                      value={donation.payment_account_id}
                      onChange={(e) => handleChange(index, 'payment_account_id', e.target.value)}
                      required
                      size="small"
                      helperText="Select the bank account to credit/debit"
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
                )}
                {donation.donation_nature === 'monetary' && donation.payment_mode === 'Bank' && (
                  <>
                    <Grid item xs={12} sm={6} md={2.5}>
                      <TextField
                        fullWidth
                        select
                        label="Bank Sub-Category"
                        value={donation.bank_sub_mode}
                        onChange={(e) => handleChange(index, 'bank_sub_mode', e.target.value)}
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

                    {donation.bank_sub_mode === 'UPI' && (
                      <>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="UPI Transaction Reference"
                            value={donation.upi_reference_number}
                            onChange={(e) => handleChange(index, 'upi_reference_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="Sender UPI ID (Optional)"
                            value={donation.sender_upi_id}
                            onChange={(e) => handleChange(index, 'sender_upi_id', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}

                    {donation.bank_sub_mode === 'Card' && (
                      <>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="Card Number / Txn Reference"
                            value={donation.card_number}
                            onChange={(e) => handleChange(index, 'card_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="Card Holder Name (Optional)"
                            value={donation.card_holder_name}
                            onChange={(e) => handleChange(index, 'card_holder_name', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}

                    {donation.bank_sub_mode === 'Online' && (
                      <>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="UTR Reference Number"
                            value={donation.utr_number}
                            onChange={(e) => handleChange(index, 'utr_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="Payer Name (Optional)"
                            value={donation.payer_name}
                            onChange={(e) => handleChange(index, 'payer_name', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}

                    {donation.bank_sub_mode === 'Cheque' && (
                      <>
                        <Grid item xs={12} sm={6} md={2}>
                          <TextField
                            fullWidth
                            label="Cheque Number"
                            value={donation.cheque_number}
                            onChange={(e) => handleChange(index, 'cheque_number', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={2}>
                          <TextField
                            fullWidth
                            label="Cheque Date"
                            type="date"
                            value={donation.cheque_date}
                            onChange={(e) => handleChange(index, 'cheque_date', e.target.value)}
                            required
                            size="small"
                            InputLabelProps={{ shrink: true }}
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={2.5}>
                          <TextField
                            fullWidth
                            label="Drawn On Bank Name"
                            value={donation.cheque_bank_name}
                            onChange={(e) => handleChange(index, 'cheque_bank_name', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={2.5}>
                          <TextField
                            fullWidth
                            label="Branch Name"
                            value={donation.cheque_branch}
                            onChange={(e) => handleChange(index, 'cheque_branch', e.target.value)}
                            required
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <TextField
                            fullWidth
                            label="Payer Name (Optional)"
                            value={donation.payer_name}
                            onChange={(e) => handleChange(index, 'payer_name', e.target.value)}
                            size="small"
                          />
                        </Grid>
                      </>
                    )}
                  </>
                )}
                {donation.donation_nature !== 'monetary' && (
                  <>
                    <Grid item xs={12} sm={6} md={3}>
                      <TextField
                        fullWidth
                        label="Item / Service Name"
                        value={donation.item_name}
                        onChange={(e) => handleChange(index, 'item_name', e.target.value)}
                        required
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="In-kind Type"
                        value={
                          donation.donation_nature === 'sponsorship'
                            ? 'Sponsorship'
                            : donation.donation_nature === 'material'
                              ? 'Physical Materials'
                              : 'Precious Articles'
                        }
                        disabled
                        size="small"
                      />
                    </Grid>
                  </>
                )}
                {donation.donation_nature === 'sponsorship' && (
                  <>
                    <Grid item xs={12} sm={6} md={3}>
                      <TextField
                        fullWidth
                        select
                        label="Sponsorship Category"
                        value={donation.sponsorship_category}
                        onChange={(e) => handleChange(index, 'sponsorship_category', e.target.value)}
                        required
                        size="small"
                      >
                        {sponsorshipCategories.map((cat) => (
                          <MenuItem key={cat} value={cat}>
                            {cat}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <TextField
                        fullWidth
                        label="Event Name"
                        value={donation.event_name}
                        onChange={(e) => handleChange(index, 'event_name', e.target.value)}
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="Event Date"
                        type="date"
                        value={donation.event_date}
                        onChange={(e) => handleChange(index, 'event_date', e.target.value)}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                      />
                    </Grid>
                  </>
                )}
                {donation.donation_nature === 'material' && (
                  <>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="Quantity"
                        type="number"
                        value={donation.quantity}
                        onChange={(e) => handleChange(index, 'quantity', e.target.value)}
                        required
                        size="small"
                        inputProps={{ min: 0.01, step: 0.01 }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        select
                        label="Unit"
                        value={donation.unit}
                        onChange={(e) => handleChange(index, 'unit', e.target.value)}
                        required
                        size="small"
                      >
                        {inventoryUnits.map((unit) => (
                          <MenuItem key={unit} value={unit}>
                            {unit}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                  </>
                )}
                {donation.donation_nature === 'precious' && (
                  <>
                    <Grid item xs={12} sm={6} md={3}>
                      <TextField
                        fullWidth
                        label="Appraised By"
                        value={donation.appraised_by}
                        onChange={(e) => handleChange(index, 'appraised_by', e.target.value)}
                        required
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="Appraisal Date"
                        type="date"
                        value={donation.appraisal_date}
                        onChange={(e) => handleChange(index, 'appraisal_date', e.target.value)}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="Purity"
                        placeholder="24K / 22K / 925"
                        value={donation.purity}
                        onChange={(e) => handleChange(index, 'purity', e.target.value)}
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="Gross Wt (g)"
                        type="number"
                        value={donation.weight_gross}
                        onChange={(e) => handleChange(index, 'weight_gross', e.target.value)}
                        size="small"
                        inputProps={{ min: 0, step: 0.01 }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField
                        fullWidth
                        label="Net Wt (g)"
                        type="number"
                        value={donation.weight_net}
                        onChange={(e) => handleChange(index, 'weight_net', e.target.value)}
                        size="small"
                        inputProps={{ min: 0, step: 0.01 }}
                      />
                    </Grid>
                  </>
                )}
                {donation.donation_nature !== 'monetary' && (
                  <Grid item xs={12}>
                    <Alert severity="info" sx={{ py: 0 }}>
                      No direct money is received. Receipt will use assessed value.
                    </Alert>
                  </Grid>
                )}
                {donation.lookup_status === 'found' && (
                  <Grid item xs={12}>
                    <Alert severity="success" sx={{ py: 0 }}>
                      Devotee found. Details loaded.
                    </Alert>
                  </Grid>
                )}
                {donation.lookup_status === 'not_found' && (
                  <Grid item xs={12}>
                    <Alert severity="info" sx={{ py: 0 }}>
                      No devotee found for this mobile number. Enter details and continue.
                    </Alert>
                  </Grid>
                )}
              </Grid>
            </Paper>
          ))}

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            <Button
              type="submit"
              variant="contained"
              startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
              disabled={saving}
              size="large"
            >
              {saving ? 'Saving...' : 'Save All Donations'}
            </Button>
            <Button
              variant="outlined"
              onClick={resetDonationRecording}
            >
              Clear All
            </Button>
          </Box>
        </Box>
      </Paper>

      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
          Recent Donations
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : donationList.length > 0 ? (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Devotee</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Payment</TableCell>
                  <TableCell>Receipt #</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {donationList.slice(0, 10).map((donation) => (
                  <TableRow key={donation.id}>
                    <TableCell>{new Date(donation.donation_date || donation.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>{donation.devotee?.name || 'N/A'}</TableCell>
                    <TableCell>{formatCurrency(donation.amount)}</TableCell>
                    <TableCell>
                      <Chip label={donation.category?.name || 'General'} size="small" />
                    </TableCell>
                    <TableCell>
                      {donation.payment_mode || (donation.donation_type === 'in_kind' ? 'IN-KIND' : 'Cash')}
                    </TableCell>
                    <TableCell>{donation.receipt_number || 'N/A'}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        color="secondary"
                        size="small"
                        onClick={() => handlePrintReceipt(donation.id, donation.receipt_number)}
                        title="Print Receipt"
                      >
                        <PrintIcon />
                      </IconButton>
                      <IconButton
                        color="primary"
                        size="small"
                        onClick={() => handleDownloadReceipt(donation.id, donation.receipt_number)}
                        title="Download Receipt"
                      >
                        <PictureAsPdfIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
            No donations recorded yet
          </Typography>
        )}
      </Paper>
    </Layout>
  );
}

export default Donations;
