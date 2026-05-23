import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Paper,
  Stack,
  CircularProgress,
  Tab,
  Tabs,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import PrintIcon from '@mui/icons-material/Print';
import MinimizeIcon from '@mui/icons-material/Minimize';
import api from '../services/api';
import { useCurrentUser } from '../contexts/CurrentUserContext';
import { ACTIVE_TEMPLE_EVENT, getActiveTempleId } from '../utils/activeTemple';

function Sevas() {
  const bankSubModeOptions = [
    { value: 'UPI', label: 'UPI' },
    { value: 'Card', label: 'Card' },
    { value: 'Cheque', label: 'Cheque' },
    { value: 'Online', label: 'Online Transfer' },
  ];

  const emptyBankPaymentFields = {
    bank_sub_mode: '',
    sender_upi_id: '',
    upi_reference_number: '',
    card_number: '',
    cheque_number: '',
    cheque_date: '',
    cheque_bank_name: '',
    cheque_branch: '',
    utr_number: '',
  };

  const getInitialBookingForm = (seva = null) => ({
    devotee_id: '',
    booking_date: new Date().toISOString().split('T')[0],
    booking_time: seva?.time_slot ?? '',
    amount_paid: seva?.amount ?? '',
    payment_method: 'Cash',
    payment_account_id: '',
    ...emptyBankPaymentFields,
    devotee_names: '',
    gotra: '',
    nakshatra: '',
    rashi: '',
    special_request: '',
    priest_id: ''
  });

  const getInitialNewDevoteeData = () => ({
    first_name: '',
    last_name: '',
    email: '',
    name_prefix: 'Sri',
    address: '',
    city: '',
    state: '',
    pincode: ''
  });

  const navigate = useNavigate();
  const { user, loading: currentUserLoading } = useCurrentUser();
  const canManageSevas = !currentUserLoading && (
    ['admin', 'super_admin', 'temple_manager'].includes(user?.role) || Boolean(user?.is_superuser)
  );
  const [sevas, setSevas] = useState([]);
  const [filteredSevas, setFilteredSevas] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [priests, setPriests] = useState([]);
  const [lastBooking, setLastBooking] = useState(null);

  // Booking dialog state
  const [bookingDialogOpen, setBookingDialogOpen] = useState(false);
  const [bookingDialogMinimized, setBookingDialogMinimized] = useState(false);
  const [selectedSeva, setSelectedSeva] = useState(null);
  const [_devotees, setDevotees] = useState([]);
  const [bookingForm, setBookingForm] = useState(getInitialBookingForm());
  const [bookingSuccess, setBookingSuccess] = useState(false);
  const [bookingError, setBookingError] = useState(null);
  const [bookingDateError, setBookingDateError] = useState('');
  const [bookingDateStatus, setBookingDateStatus] = useState(null);
  const [checkingBookingDate, setCheckingBookingDate] = useState(false);
  const [downloadingReceipt, setDownloadingReceipt] = useState(false);
  const [paymentAccounts, setPaymentAccounts] = useState({ cash_accounts: [], bank_accounts: [] });

  // Mobile-first workflow state
  const [mobileNumber, setMobileNumber] = useState('');
  const [searchingDevotee, setSearchingDevotee] = useState(false);
  const [foundDevotee, setFoundDevotee] = useState(null);
  const [showNewDevoteeForm, setShowNewDevoteeForm] = useState(false);
  const [pincodeLoading, setPincodeLoading] = useState(false);
  const [newDevoteeData, setNewDevoteeData] = useState(getInitialNewDevoteeData());

  // Dropdown options state
  const [dropdownOptions, setDropdownOptions] = useState({
    gothras: [],
    nakshatras: [],
    rashis: []
  });
  const [tenantAccessLoading, setTenantAccessLoading] = useState(true);
  const [tenantWriteBlocked, setTenantWriteBlocked] = useState(false);
  const [tenantReadOnlyMessage, setTenantReadOnlyMessage] = useState('');

  const systemRole = user?.system_role || user?.role;
  const isPlatformSuperAdmin = !currentUserLoading && (Boolean(user?.is_superuser) || systemRole === 'super_admin');
  const bookingBlockedReason = tenantReadOnlyMessage || 'This tenant is read-only for the current platform administrator';

  useEffect(() => {
    fetchSevas();
    fetchDevotees();
    fetchDropdownOptions();
    fetchPriests();
    fetchPaymentAccounts();
  }, []);

  useEffect(() => {
    const handleActiveTempleChange = () => {
      fetchSevas();
      fetchDevotees();
      fetchDropdownOptions();
      fetchPriests();
      fetchPaymentAccounts();
    };

    window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
    return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
  }, []);

  // Filtering intentionally tracks the seva list and category only.
  useEffect(() => {
    filterSevas();
  }, [sevas, selectedCategory]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false;

    const evaluateTenantWriteAccess = async () => {
      if (currentUserLoading) {
        return;
      }

      if (!isPlatformSuperAdmin) {
        if (!cancelled) {
          setTenantWriteBlocked(false);
          setTenantReadOnlyMessage('');
          setTenantAccessLoading(false);
        }
        return;
      }

      const activeTempleId = getActiveTempleId();
      if (!activeTempleId) {
        if (!cancelled) {
          setTenantWriteBlocked(true);
          setTenantReadOnlyMessage('Select an onboarded tenant from the top selector before creating bookings.');
          setTenantAccessLoading(false);
        }
        return;
      }

      try {
        if (!cancelled) {
          setTenantAccessLoading(true);
        }
        const response = await api.get('/api/v1/temples/current', { params: { temple_id: activeTempleId } });
        const temple = response?.data || {};
        const canWrite = Boolean(temple?.platform_can_write);

        if (!cancelled) {
          setTenantWriteBlocked(!canWrite);
          setTenantReadOnlyMessage(
            canWrite
              ? ''
              : `${temple?.name || temple?.trust_name || 'Selected tenant'} is read-only for the current platform administrator`
          );
          setTenantAccessLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setTenantWriteBlocked(false);
          setTenantReadOnlyMessage('');
          setTenantAccessLoading(false);
        }
      }
    };

    evaluateTenantWriteAccess();
    window.addEventListener(ACTIVE_TEMPLE_EVENT, evaluateTenantWriteAccess);
    return () => {
      cancelled = true;
      window.removeEventListener(ACTIVE_TEMPLE_EVENT, evaluateTenantWriteAccess);
    };
  }, [currentUserLoading, isPlatformSuperAdmin]);

  const fetchSevas = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/sevas/');
      setSevas(response.data);

      // Extract unique categories
      const uniqueCategories = [...new Set(response.data.map(s => s.category))];
      setCategories(uniqueCategories);

      setLoading(false);
    } catch (err) {
      setError('Failed to load sevas');
      setLoading(false);
    }
  };

  const fetchDevotees = async () => {
    try {
      const response = await api.get('/api/v1/devotees/');
      setDevotees(response.data);
    } catch (err) {
      console.error('Failed to load devotees');
    }
  };

  const selectDevoteeForBooking = (devotee) => {
    if (!devotee) return;
    setFoundDevotee(devotee);
    setShowNewDevoteeForm(false);
    setBookingError(null);
    setBookingForm((prev) => ({ ...prev, devotee_id: String(devotee.id || '') }));
  };

  const resolveDevoteeByMobile = async (mobile) => {
    if (!mobile) return null;
    try {
      const response = await api.get(`/api/v1/devotees/search/by-mobile/${mobile}`);
      const devotee = Array.isArray(response.data) && response.data.length > 0 ? response.data[0] : null;
      if (devotee) {
        selectDevoteeForBooking(devotee);
      }
      return devotee;
    } catch (err) {
      console.error('Failed to resolve devotee by mobile:', err);
      return null;
    }
  };

  const fetchPriests = async () => {
    try {
      const response = await api.get('/api/v1/sevas/lists/priests');
      setPriests(response.data);
    } catch (err) {
      console.error('Failed to load priests:', err);
    }
  };

  const fetchDropdownOptions = async () => {
    try {
      const response = await api.get('/api/v1/sevas/dropdown-options');
      console.log('Dropdown options response:', response.data);
      if (response.data) {
        const gothras = Array.isArray(response.data.gothras)
          ? response.data.gothras
          : (Array.isArray(response.data.GOTHRAS) ? response.data.GOTHRAS : []);
        const nakshatras = Array.isArray(response.data.nakshatras)
          ? response.data.nakshatras
          : (Array.isArray(response.data.NAKSHATRAS) ? response.data.NAKSHATRAS : []);
        const rashis = Array.isArray(response.data.rashis)
          ? response.data.rashis
          : (Array.isArray(response.data.RASHIS) ? response.data.RASHIS : []);

        if (gothras.length === 0 && nakshatras.length === 0 && rashis.length === 0) {
          throw new Error('Dropdown options payload missing gothra/nakshatra/rashi lists');
        }

        setDropdownOptions({
          gothras,
          nakshatras,
          rashis,
        });
      }
    } catch (err) {
      console.error('Failed to load dropdown options:', err);
      // Fallback to hardcoded values if API fails
      setDropdownOptions({
        gothras: [
          "Agastya", "Angirasa", "Atri", "Bharadwaja", "Bhargava", "Bhrigu",
          "Dhananjaya", "Garga", "Gautama", "Harita", "Jamadagni", "Kashyapa",
          "Katyayana", "Kaundinya", "Kausika", "Kaushika", "Kratu", "Kutsa",
          "Lomasha", "Mandavya", "Marichi", "Moudgalya", "Naidhruva", "Parashara",
          "Pulaha", "Pulastya", "Sandilya", "Shandilya", "Sankrithi", "Srivatsa",
          "Upamanyu", "Valmiki", "Vashishta", "Vatsa", "Vishwamitra", "Viswamitra",
          "Vrigu", "Yaska", "Kanva", "Mudgala", "Raibhya", "Uddalaka", "Agni",
          "Aliman", "Kapi", "Krivi", "Saunaka", "Vadula", "Vasistha"
        ],
        nakshatras: [
          "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
          "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
          "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
          "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
          "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
        ],
        rashis: [
          "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)", "Karka (Cancer)",
          "Simha (Leo)", "Kanya (Virgo)", "Tula (Libra)", "Vrishchika (Scorpio)",
          "Dhanu (Sagittarius)", "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)"
        ]
      });
    }
  };

  const filterSevas = () => {
    // Exclude quick token sevas from the regular sevas display
    const regularSevas = sevas.filter(s => !s.quick_ticket_enabled);

    if (selectedCategory === 'all') {
      setFilteredSevas(regularSevas);
    } else {
      setFilteredSevas(regularSevas.filter(s => s.category === selectedCategory));
    }
  };

  const fetchPaymentAccounts = async () => {
    try {
      const response = await api.get('/api/v1/sevas/payment-accounts');
      const data = response?.data || {};
      setPaymentAccounts({
        cash_accounts: Array.isArray(data.cash_accounts) ? data.cash_accounts : [],
        bank_accounts: Array.isArray(data.bank_accounts) ? data.bank_accounts : [],
      });
    } catch (err) {
      console.error('Failed to load payment accounts:', err);
      setPaymentAccounts({ cash_accounts: [], bank_accounts: [] });
    }
  };

  const getSevaAvailabilityLabel = (seva) => {
    if (!seva) return '';
    if (seva.specific_day !== null && seva.specific_day !== undefined) {
      const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      return `${days[seva.specific_day]} Only`;
    }
    if (seva.except_day !== null && seva.except_day !== undefined) {
      const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      return `Except ${days[seva.except_day]}`;
    }
    return formatCategory(seva.availability || 'daily');
  };

  const normalizeBookingDate = (value) => {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (/^\d{2}-\d{2}-\d{4}$/.test(raw)) {
      return `${raw.slice(6, 10)}-${raw.slice(3, 5)}-${raw.slice(0, 2)}`;
    }
    return raw;
  };

  const validateSevaDateLocally = (seva, dateValue) => {
    const normalizedDate = normalizeBookingDate(dateValue);
    if (!seva || !normalizedDate) return '';

    const selectedDate = new Date(`${normalizedDate}T00:00:00`);
    if (Number.isNaN(selectedDate.getTime())) {
      return 'Please enter a valid booking date.';
    }

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const selectedDay = selectedDate.getDay();
    if (seva.specific_day !== null && seva.specific_day !== undefined && selectedDay !== Number(seva.specific_day)) {
      return `This seva is available only on ${days[Number(seva.specific_day)]}. Please select a ${days[Number(seva.specific_day)]} date.`;
    }
    if (seva.except_day !== null && seva.except_day !== undefined && selectedDay === Number(seva.except_day)) {
      return `This seva is not available on ${days[Number(seva.except_day)]}. Please select another date.`;
    }
    if (seva.availability === 'weekday' && (selectedDay === 0 || selectedDay === 6)) {
      return 'This seva is available only on weekdays.';
    }
    if (seva.availability === 'weekend' && selectedDay !== 0 && selectedDay !== 6) {
      return 'This seva is available only on weekends.';
    }
    if (seva.availability === 'festival_only') {
      return 'This seva is available only on configured festival dates.';
    }

    const advanceDays = Number(seva.advance_booking_days || 0);
    if (advanceDays > 0) {
      const maxDate = new Date();
      maxDate.setHours(0, 0, 0, 0);
      maxDate.setDate(maxDate.getDate() + advanceDays);
      if (selectedDate > maxDate) {
        return `This seva can be booked only up to ${advanceDays} day(s) in advance.`;
      }
    }
    return '';
  };

  const checkBookingDateAvailability = async (seva, dateValue) => {
    const normalizedDate = normalizeBookingDate(dateValue);
    const localError = validateSevaDateLocally(seva, normalizedDate);
    setBookingDateStatus(null);
    if (localError) {
      setBookingDateError(localError);
      return;
    }
    if (!seva?.id || !normalizedDate) {
      setBookingDateError('');
      return;
    }

    try {
      setCheckingBookingDate(true);
      const response = await api.get(`/api/v1/sevas/${seva.id}/availability`, {
        params: { booking_date: normalizedDate },
      });
      const availability = response?.data || {};
      setBookingDateStatus(availability);
      const hasFiniteSlots = availability.slots_left !== null && availability.slots_left !== undefined;
      if (availability.available === false || (hasFiniteSlots && Number(availability.slots_left) <= 0)) {
        setBookingDateError(`This seva is fully booked for ${normalizedDate}. Please select another date.`);
      } else {
        setBookingDateError('');
      }
    } catch (err) {
      setBookingDateStatus(null);
      setBookingDateError(err.response?.data?.detail || 'Could not check seva availability for this date.');
    } finally {
      setCheckingBookingDate(false);
    }
  };

  useEffect(() => {
    if (!bookingDialogOpen || !selectedSeva) return undefined;

    const timeoutId = setTimeout(() => {
      checkBookingDateAvailability(selectedSeva, bookingForm.booking_date);
    }, 250);
    return () => clearTimeout(timeoutId);
  }, [bookingDialogOpen, selectedSeva, bookingForm.booking_date]); // eslint-disable-line react-hooks/exhaustive-deps

  const resetBookingWorkflow = (seva = null) => {
    setBookingSuccess(false);
    setBookingError(null);
    setBookingDateError('');
    setBookingDateStatus(null);
    setCheckingBookingDate(false);
    setLastBooking(null);
    setDownloadingReceipt(false);
    setMobileNumber('');
    setSearchingDevotee(false);
    setFoundDevotee(null);
    setShowNewDevoteeForm(false);
    setPincodeLoading(false);
    setNewDevoteeData(getInitialNewDevoteeData());
    setBookingForm(getInitialBookingForm(seva));
    setBookingDialogMinimized(false);
  };

  const handleCloseBookingDialog = () => {
    setBookingDialogOpen(false);
    setBookingDialogMinimized(false);
    setSelectedSeva(null);
    resetBookingWorkflow();
  };

  const handleMinimizeBookingDialog = () => {
    setBookingDialogOpen(false);
    setBookingDialogMinimized(true);
  };

  const handleRestoreBookingDialog = () => {
    setBookingDialogOpen(true);
    setBookingDialogMinimized(false);
  };

  const handleBookingDialogRequestClose = (_event, reason) => {
    if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
      handleMinimizeBookingDialog();
      return;
    }
    handleCloseBookingDialog();
  };

  const handleBookNow = (seva) => {
    if (tenantWriteBlocked) {
      setBookingError(bookingBlockedReason);
      return;
    }
    resetBookingWorkflow(seva);
    setSelectedSeva(seva);
    setBookingDialogOpen(true);
  };

  const handleSearchByMobile = async () => {
    if (!mobileNumber || mobileNumber.length < 10) {
      setBookingError('Please enter a valid 10-digit mobile number');
      return;
    }

    setSearchingDevotee(true);
    setBookingError(null);

    try {
      const devotee = await resolveDevoteeByMobile(mobileNumber);
      if (!devotee) {
        // Devotee not found - show create form
        setFoundDevotee(null);
        setShowNewDevoteeForm(true);
        setNewDevoteeData((prev) => ({ ...prev, first_name: '', last_name: '', email: '' }));
      }
    } catch (err) {
      // Devotee not found - show create form
      setFoundDevotee(null);
      setShowNewDevoteeForm(true);
    } finally {
      setSearchingDevotee(false);
    }
  };

  const handleCreateDevotee = async () => {
    if (!newDevoteeData.first_name?.trim()) {
      setBookingError('Please enter devotee first name');
      return;
    }
    if (tenantWriteBlocked) {
      setBookingError(bookingBlockedReason);
      return;
    }

    try {
      const fullName = `${newDevoteeData.first_name || ''} ${newDevoteeData.last_name || ''}`.trim();
      const devoteeData = {
        name_prefix: newDevoteeData.name_prefix,
        first_name: newDevoteeData.first_name,
        last_name: newDevoteeData.last_name || null,
        name: fullName,
        email: newDevoteeData.email?.trim() || null,
        phone: mobileNumber,
        address: newDevoteeData.address,
        city: newDevoteeData.city,
        state: newDevoteeData.state,
        pincode: newDevoteeData.pincode
      };

      const response = await api.post('/api/v1/devotees/', devoteeData);
      selectDevoteeForBooking(response.data);

      // Refresh devotees list
      fetchDevotees();
    } catch (err) {
      const detail = String(err.response?.data?.detail || '').toLowerCase();
      const isDuplicateDevotee = detail.includes('phone number already exists') || detail.includes('search for this devotee');
      if (isDuplicateDevotee) {
        const recoveredDevotee = await resolveDevoteeByMobile(mobileNumber);
        if (recoveredDevotee) {
          return;
        }
      }
      setBookingError(err.response?.data?.detail || 'Failed to create devotee');
    }
  };

  const fetchPincodeDetails = async (pincode) => {
    if (!pincode || pincode.length !== 6) return;

    try {
      setPincodeLoading(true);
      const response = await api.get('/api/v1/pincode/lookup', {
        params: { pincode },
      });
      const data = response?.data;
      if (data?.found) {
        setNewDevoteeData((prev) => ({
          ...prev,
          city: data.city || '',
          state: data.state || '',
        }));
      }
    } catch (err) {
      // Keep manual entry possible even if lookup fails
      console.error('Failed to lookup pincode:', err);
    } finally {
      setPincodeLoading(false);
    }
  };

  const handleBookingSubmit = async () => {
    try {
      setBookingError(null);
      if (tenantWriteBlocked) {
        setBookingError(bookingBlockedReason);
        return;
      }

      const currentDateError = validateSevaDateLocally(selectedSeva, bookingForm.booking_date) || bookingDateError;
      if (currentDateError) {
        setBookingDateError(currentDateError);
        setBookingError(currentDateError);
        return;
      }
      if (checkingBookingDate) {
        setBookingError('Please wait while we check seva availability for this date.');
        return;
      }

      // Frontend validation for advance booking limit to provide immediate feedback
      const advanceDays = Number(selectedSeva?.advance_booking_days || 0);
      if (advanceDays > 0 && bookingForm.booking_date) {
        const selectedDate = new Date(bookingForm.booking_date);
        const maxDate = new Date();
        maxDate.setHours(0, 0, 0, 0);
        maxDate.setDate(maxDate.getDate() + advanceDays);
        if (selectedDate > maxDate) {
          setBookingError(`This seva can be booked only up to ${advanceDays} day(s) in advance.`);
          return;
        }
      }

      const devoteeId = String(bookingForm.devotee_id || '').trim();
      const amountNum = Number(bookingForm.amount_paid);
      if (!Number.isFinite(amountNum) || amountNum <= 0) {
        setBookingError('Please enter a valid amount greater than zero.');
        return;
      }

      const rawBookingDate = (bookingForm.booking_date || '').trim();
      const normalizedBookingDate = normalizeBookingDate(rawBookingDate);
      if (!normalizedBookingDate || Number.isNaN(Date.parse(normalizedBookingDate))) {
        setBookingError('Please enter a valid booking date.');
        return;
      }

      if (selectedSeva?.quick_ticket_enabled) {
        const quickPaymentMode = bookingForm.payment_method === 'UPI' ? 'UPI' : 'Cash';
        const defaultAccount =
          quickPaymentMode === 'UPI'
            ? paymentAccounts.bank_accounts[0]
            : paymentAccounts.cash_accounts[0];

        if (!defaultAccount?.account_id) {
          setBookingError(
            `No ${quickPaymentMode === 'UPI' ? 'bank' : 'cash'} account is configured for quick seva posting.`
          );
          return;
        }

        const optionalName = bookingForm.devotee_names?.trim() || null;
        const quickPayload = {
          seva_id: String(selectedSeva.id),
          seva_name: selectedSeva.name_english || selectedSeva.name || 'Quick Seva',
          seva_name_local: selectedSeva.name_kannada || null,
          amount: amountNum,
          booking_date: normalizedBookingDate,
          payment_mode: quickPaymentMode,
          payment_status: 'completed',
          ticket_type: 'seva',
          payment_account_id: Number(defaultAccount.account_id),
          devotee_name: optionalName,
          devotee_names: optionalName,
          skip_devotee_save: true,
          quick_ticket: true,
        };

        const response = await api.post('/api/v1/sevas/bookings/quick-ticket', quickPayload);
        const createdBooking = response.data?.record || response.data;
        setBookingSuccess(true);
        setLastBooking(createdBooking);
        await fetchSevas();

        if (createdBooking?.id) {
          await handlePrintReceipt(createdBooking.id, createdBooking.receipt_number);
        }

        setTimeout(() => {
          handleCloseBookingDialog();
        }, 1200);
        return;
      }

      if (!devoteeId) {
        setBookingError('Please select a valid devotee before booking.');
        return;
      }

      const paymentMethod = (bookingForm.payment_method || '').trim();
      const bankSubMode = (bookingForm.bank_sub_mode || '').trim();
      if (!paymentMethod) {
        setBookingError('Please select a payment method.');
        return;
      }
      if (!bookingForm.payment_account_id) {
        setBookingError(
          `Please select ${paymentMethod === 'Bank' ? 'bank' : 'cash'} account code.`
        );
        return;
      }
      if (paymentMethod === 'Bank' && !bankSubMode) {
        setBookingError('Please select Bank Sub-Category (UPI/Card/Cheque/Online Transfer).');
        return;
      }
      if (paymentMethod === 'Bank' && bankSubMode === 'UPI' && !bookingForm.upi_reference_number?.trim()) {
        setBookingError('Please enter UPI transaction reference.');
        return;
      }
      if (paymentMethod === 'Bank' && bankSubMode === 'Card' && !bookingForm.card_number?.trim()) {
        setBookingError('Please enter card number / transaction reference.');
        return;
      }
      if (paymentMethod === 'Bank' && bankSubMode === 'Online' && !bookingForm.utr_number?.trim()) {
        setBookingError('Please enter UTR reference number.');
        return;
      }
      if (paymentMethod === 'Bank' && bankSubMode === 'Cheque') {
        if (!bookingForm.cheque_number?.trim()) {
          setBookingError('Please enter cheque number.');
          return;
        }
        if (!bookingForm.cheque_date) {
          setBookingError('Please select cheque date.');
          return;
        }
        if (!bookingForm.cheque_bank_name?.trim()) {
          setBookingError('Please enter bank name for cheque.');
          return;
        }
        if (!bookingForm.cheque_branch?.trim()) {
          setBookingError('Please enter branch name for cheque.');
          return;
        }
      }

      const finalPaymentMethod = paymentMethod === 'Bank' ? bankSubMode : paymentMethod;
      const isUpiPayment = finalPaymentMethod === 'UPI';
      const isCardPayment = finalPaymentMethod === 'Card';
      const isChequePayment = finalPaymentMethod === 'Cheque';
      const isOnlinePayment = finalPaymentMethod === 'Online';
      const paymentAccountIdNum = Number(bookingForm.payment_account_id);

      const bookingData = {
        ...bookingForm,
        seva_id: String(selectedSeva.id),
        devotee_id: devoteeId,
        booking_date: normalizedBookingDate,
        booking_time: bookingForm.booking_time?.trim() || selectedSeva?.time_slot || null,
        amount_paid: amountNum,
        payment_method: finalPaymentMethod || null,
        payment_account_id:
          Number.isFinite(paymentAccountIdNum) && paymentAccountIdNum > 0
            ? paymentAccountIdNum
            : null,
        payment_reference: isUpiPayment
          ? bookingForm.upi_reference_number?.trim() || null
          : isCardPayment
            ? bookingForm.card_number?.trim() || null
            : isChequePayment
              ? bookingForm.cheque_number?.trim() || null
              : isOnlinePayment
                ? bookingForm.utr_number?.trim() || null
                : null,
        sender_upi_id: isUpiPayment ? bookingForm.sender_upi_id?.trim() || null : null,
        upi_reference_number: isUpiPayment ? bookingForm.upi_reference_number?.trim() || null : null,
        cheque_number: isChequePayment ? bookingForm.cheque_number?.trim() || null : null,
        cheque_date: isChequePayment ? bookingForm.cheque_date || null : null,
        cheque_bank_name: isChequePayment ? bookingForm.cheque_bank_name?.trim() || null : null,
        cheque_branch: isChequePayment ? bookingForm.cheque_branch?.trim() || null : null,
        utr_number: isOnlinePayment ? bookingForm.utr_number?.trim() || null : null,
        devotee_names: bookingForm.devotee_names?.trim() || null,
        gotra: bookingForm.gotra || null,
        nakshatra: bookingForm.nakshatra || null,
        rashi: bookingForm.rashi || null,
        special_request: bookingForm.special_request?.trim() || null,
        priest_id: bookingForm.priest_id ? Number(bookingForm.priest_id) : null,
      };

      console.log('Submitting booking:', bookingData);
      const response = await api.post('/api/v1/sevas/bookings/', bookingData);
      console.log('Booking created successfully:', response.data);

      setBookingSuccess(true);
      setLastBooking(response.data);

      // Refresh sevas list to show updated availability
      await fetchSevas();

      // Reset and close after 2 seconds
      setTimeout(() => {
        handleCloseBookingDialog();
      }, 2000);
    } catch (err) {
      console.error('Booking error:', err);
      let errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to book seva';
      if (Array.isArray(err.response?.data?.detail)) {
        errorMessage = err.response.data.detail
          .map((item) => {
            const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : 'field';
            return `${field}: ${item?.msg || 'invalid value'}`;
          })
          .join(' | ');
      }
      setBookingError(errorMessage);
      console.error('Error details:', err.response?.data);
    }
  };

  const handleDownloadReceipt = async (bookingId, receiptNumber) => {
    try {
      setDownloadingReceipt(true);
      const response = await api.get(`/api/v1/sevas/bookings/${bookingId}/receipt/pdf`, {
        responseType: 'blob',
        params: { lang: 'kannada' },
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `seva_receipt_${receiptNumber || bookingId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading receipt:', err);
      setBookingError('Failed to download receipt');
    } finally {
      setDownloadingReceipt(false);
    }
  };

  const handlePrintReceipt = async (bookingId, _receiptNumber) => {
    try {
      setDownloadingReceipt(true);
      const response = await api.get(`/api/v1/sevas/bookings/${bookingId}/receipt/pdf`, {
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
      setBookingError(err.message || 'Failed to print receipt');
    } finally {
      setDownloadingReceipt(false);
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      abhisheka: '#2E7D32',
      alankara: '#1565C0',
      pooja: '#0D47A1',
      archana: '#F57C00',
      vahana_seva: '#00796B',
      special: '#C62828',
      festival: '#FF6B35'
    };
    return colors[category] || '#666';
  };

  const getCategoryIcon = (category) => {
    const icons = {
      abhisheka: '\u{1F4A7}',
      alankara: '\u{1F338}',
      pooja: '\u{1F549}',
      archana: '\u{1F64F}',
      vahana_seva: '\u{1F6A9}',
      special: '\u2B50',
      festival: '\u{1F389}'
    };
    return icons[category] || '\u{1F6D5}';
  };

  const formatCategory = (category) => {
    return category.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 3, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#fff', mb: 0.5 }}>
              Temple Sevas & Services
            </Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.9)' }}>
              Book divine sevas and poojas for blessings and spiritual upliftment
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate('/dashboard')}
              sx={{
                bgcolor: '#fff',
                color: '#FF6B35',
                '&:hover': { bgcolor: '#f5f5f5' }
              }}
            >
              Back to Dashboard
            </Button>
            <Button
              variant="contained"
              onClick={() => navigate('/reports/sevas/detailed')}
              sx={{
                bgcolor: '#fff',
                color: '#FF6B35',
                '&:hover': { bgcolor: '#f5f5f5' }
              }}
            >
              Bookings / Reschedule
            </Button>
            {canManageSevas && (
              <Button
                variant="contained"
                startIcon={<SettingsIcon />}
                onClick={() => navigate('/sevas/manage')}
                sx={{
                  bgcolor: '#fff',
                  color: '#FF6B35',
                  '&:hover': { bgcolor: '#f5f5f5' }
                }}
              >
                Add / Manage Sevas
              </Button>
            )}
          </Box>
        </Box>
      </Paper>

      {tenantWriteBlocked && !tenantAccessLoading && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {bookingBlockedReason}. You can review this tenant, but booking and create actions are disabled.
        </Alert>
      )}

      {/* Quick Token Counter Section */}
      {sevas.filter(s => s.quick_ticket_enabled).length > 0 && (
        <>
          <Paper sx={{ p: 3, mb: 3, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#fff', mb: 0.5 }}>
              ⚡ Quick Token Counter
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.9)' }}>
              One-click booking for counter sevas — No login required
            </Typography>
          </Paper>

          <Grid container spacing={2} sx={{ mb: 4 }}>
            {sevas.filter(s => s.quick_ticket_enabled).map((seva) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={`quick-${seva.id}`}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    border: '2px solid #FF9933',
                    borderLeft: `4px solid ${getCategoryColor(seva.category)}`,
                    '&:hover': {
                      boxShadow: 6,
                      transform: 'translateY(-2px)',
                      transition: 'all 0.3s'
                    }
                  }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Chip
                      label={`${getCategoryIcon(seva.category)} ${formatCategory(seva.category)}`}
                      size="small"
                      sx={{
                        mb: 1,
                        bgcolor: getCategoryColor(seva.category),
                        color: '#fff',
                        fontWeight: 600
                      }}
                    />

                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: getCategoryColor(seva.category) }}>
                      {seva.name_english}
                    </Typography>
                    {seva.name_kannada && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {seva.name_kannada}
                      </Typography>
                    )}

                    {seva.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {seva.description}
                      </Typography>
                    )}

                    {seva.time_slot && (
                      <Chip
                        label={`🕐 ${seva.time_slot}`}
                        size="small"
                        variant="outlined"
                        sx={{ mb: 1, mr: 1 }}
                      />
                    )}

                    <Box sx={{ mt: 'auto', pt: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: getCategoryColor(seva.category) }}>
                        ₹{seva.amount}
                      </Typography>
                    </Box>
                  </CardContent>

                  <Box sx={{ p: 2, pt: 0 }}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={() => handleBookNow(seva)}
                      disabled={!seva.is_active || tenantWriteBlocked || tenantAccessLoading}
                      sx={{
                        bgcolor: getCategoryColor(seva.category),
                        color: '#fff',
                        '&:hover': {
                          bgcolor: getCategoryColor(seva.category),
                          color: '#fff',
                          filter: 'brightness(0.9)'
                        }
                      }}
                    >
                      {tenantWriteBlocked ? 'Read-only Tenant' : 'Book Now'}
                    </Button>
                  </Box>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: '#333' }}>
            All Sevas & Services
          </Typography>
        </>
      )}

      {/* Category Filter */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Tabs
          value={selectedCategory}
          onChange={(e, newValue) => setSelectedCategory(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="All Sevas" value="all" />
          {categories.map(cat => (
            <Tab
              key={cat}
              label={`${getCategoryIcon(cat)} ${formatCategory(cat)}`}
              value={cat}
            />
          ))}
        </Tabs>
      </Paper>

      {/* Sevas Grid */}
      <Grid container spacing={2}>
        {filteredSevas.map((seva) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={seva.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                borderLeft: `4px solid ${getCategoryColor(seva.category)}`,
                '&:hover': {
                  boxShadow: 6,
                  transform: 'translateY(-2px)',
                  transition: 'all 0.3s'
                }
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                {/* Category Badge */}
                <Chip
                  label={`${getCategoryIcon(seva.category)} ${formatCategory(seva.category)}`}
                  size="small"
                  sx={{
                    mb: 1,
                    bgcolor: getCategoryColor(seva.category),
                    color: '#fff',
                    fontWeight: 600
                  }}
                />

                {/* Seva Name */}
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: getCategoryColor(seva.category) }}>
                  {seva.name_english}
                </Typography>
                {seva.name_kannada && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {seva.name_kannada}
                  </Typography>
                )}

                {/* Description */}
                {seva.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {seva.description}
                  </Typography>
                )}

                {/* Time Slot */}
                {seva.time_slot && (
                  <Chip
                    label={`\u23F0 ${seva.time_slot}`}
                    size="small"
                    variant="outlined"
                    sx={{ mb: 1, mr: 1 }}
                  />
                )}

                {/* Booking Limit */}
                {seva.max_bookings_per_day ? (
                  <Chip
                    label={`Max ${seva.max_bookings_per_day}/day`}
                    size="small"
                    variant="outlined"
                    sx={{ mb: 1, mr: 1 }}
                  />
                ) : null}
                {seva.bookings_available !== null && seva.bookings_available !== undefined ? (
                  <Chip
                    label={`Slots left today: ${seva.bookings_available}`}
                    size="small"
                    variant="outlined"
                    color={seva.bookings_available > 0 ? 'success' : 'warning'}
                    sx={{ mb: 1 }}
                  />
                ) : null}

                {/* Availability */}
                {seva.availability !== 'daily' && (
                  <Chip
                    label={
                      seva.specific_day !== null
                        ? `${['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][seva.specific_day]} Only`
                        : seva.except_day !== null
                          ? `Except ${['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][seva.except_day]}`
                          : formatCategory(seva.availability)
                    }
                    size="small"
                    variant="outlined"
                    sx={{ mb: 1 }}
                  />
                )}

                {/* Availability Status */}
                {seva.is_available_today ? (
                  <Chip
                    label="Available Today"
                    size="small"
                    sx={{ bgcolor: '#E8F5E9', color: '#2E7D32', mb: 1, display: 'block', width: 'fit-content' }}
                  />
                ) : (
                  <Chip
                    label="Not Available Today"
                    size="small"
                    sx={{ bgcolor: '#FFEBEE', color: '#C62828', mb: 1, display: 'block', width: 'fit-content' }}
                  />
                )}

                {/* Price */}
                <Box sx={{ mt: 'auto', pt: 2 }}>
                  {seva.min_amount && seva.max_amount ? (
                    <Typography variant="h6" sx={{ fontWeight: 700, color: getCategoryColor(seva.category) }}>
                      {'\u20B9'}{seva.min_amount} - {'\u20B9'}{seva.max_amount}
                    </Typography>
                  ) : (
                    <Typography variant="h6" sx={{ fontWeight: 700, color: getCategoryColor(seva.category) }}>
                      {'\u20B9'}{seva.amount}
                    </Typography>
                  )}
                </Box>
              </CardContent>

              {/* Book Button */}
              <Box sx={{ p: 2, pt: 0 }}>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={() => handleBookNow(seva)}
                  disabled={!seva.is_active || tenantWriteBlocked || tenantAccessLoading}
                  sx={{
                    bgcolor: getCategoryColor(seva.category),
                    color: '#fff',
                    '&:hover': {
                      bgcolor: getCategoryColor(seva.category),
                      color: '#fff',
                      filter: 'brightness(0.9)'
                    }
                  }}
                >
                  {tenantWriteBlocked ? 'Read-only Tenant' : 'Book Now'}
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Booking Dialog */}
      <Dialog
        open={bookingDialogOpen}
        onClose={handleBookingDialogRequestClose}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ pr: 7 }}>
          <Tooltip title="Minimize">
            <IconButton
              aria-label="minimize booking dialog"
              onClick={handleMinimizeBookingDialog}
              size="small"
              sx={{ position: 'absolute', right: 12, top: 12 }}
            >
              <MinimizeIcon />
            </IconButton>
          </Tooltip>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Book {selectedSeva?.name_english}
          </Typography>
          {selectedSeva?.name_kannada && (
            <Typography variant="body2" color="text.secondary">
              {selectedSeva.name_kannada}
            </Typography>
          )}
          {selectedSeva?.description && (
            <Typography variant="body2" sx={{ mt: 0.75 }} color="text.secondary">
              {selectedSeva.description}
            </Typography>
          )}
          <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {selectedSeva?.time_slot && (
              <Chip
                size="small"
                variant="outlined"
                label={`\u23F0 ${selectedSeva.time_slot}`}
              />
            )}
            {selectedSeva?.availability && selectedSeva.availability !== 'daily' && (
              <Chip
                size="small"
                variant="outlined"
                label={getSevaAvailabilityLabel(selectedSeva)}
              />
            )}
            {selectedSeva?.max_bookings_per_day ? (
              <Chip
                size="small"
                variant="outlined"
                label={`Max ${selectedSeva.max_bookings_per_day} booking(s)/day`}
              />
            ) : null}
            {selectedSeva?.is_available_today !== undefined && (
              <Chip
                size="small"
                color={selectedSeva.is_available_today ? 'success' : 'error'}
                label={selectedSeva.is_available_today ? 'Available Today' : 'Not Available Today'}
              />
            )}
            {selectedSeva?.bookings_available !== null && selectedSeva?.bookings_available !== undefined ? (
              <Chip
                size="small"
                color={selectedSeva.bookings_available > 0 ? 'success' : 'warning'}
                label={`Slots left today: ${selectedSeva.bookings_available}`}
              />
            ) : null}
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          {bookingSuccess && (
            <Box>
              <Alert severity="success" sx={{ mb: 2 }}>
                Seva booked successfully!
                {lastBooking?.receipt_number && ` (Receipt: ${lastBooking.receipt_number})`}
              </Alert>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  color="primary"
                  startIcon={downloadingReceipt ? <CircularProgress size={20} /> : <PictureAsPdfIcon />}
                  onClick={() => handleDownloadReceipt(lastBooking.id, lastBooking.receipt_number)}
                  disabled={downloadingReceipt || !lastBooking}
                >
                  {downloadingReceipt ? 'Processing...' : 'Download Receipt'}
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  color="secondary"
                  startIcon={<PrintIcon />}
                  onClick={() => handlePrintReceipt(lastBooking.id, lastBooking.receipt_number)}
                  disabled={downloadingReceipt || !lastBooking}
                >
                  Print Receipt
                </Button>
              </Stack>
            </Box>
          )}
          {bookingError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {bookingError}
            </Alert>
          )}
          {bookingDateError && !bookingError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {bookingDateError}
            </Alert>
          )}
          {!bookingDateError && bookingDateStatus?.slots_left !== null && bookingDateStatus?.slots_left !== undefined && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {bookingDateStatus.slots_left} slot(s) available for the selected date.
            </Alert>
          )}
          {tenantWriteBlocked && !tenantAccessLoading && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {bookingBlockedReason}
            </Alert>
          )}

          <Stack spacing={2}>
            {selectedSeva?.quick_ticket_enabled && (
              <Box>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Quick Seva counter booking. Mobile number and devotee details are not required.
                </Alert>
                <Stack spacing={2}>
                  <TextField
                    label="Name (Optional)"
                    value={bookingForm.devotee_names}
                    onChange={(e) => setBookingForm({ ...bookingForm, devotee_names: e.target.value })}
                    placeholder="Name to print on receipt, if required"
                    fullWidth
                  />
                  <FormControl fullWidth>
                    <InputLabel>Payment Mode</InputLabel>
                    <Select
                      value={bookingForm.payment_method === 'UPI' ? 'UPI' : 'Cash'}
                      onChange={(e) =>
                        setBookingForm({
                          ...bookingForm,
                          payment_method: e.target.value,
                          payment_account_id: '',
                          ...emptyBankPaymentFields,
                        })
                      }
                      label="Payment Mode"
                    >
                      <MenuItem value="Cash">Cash</MenuItem>
                      <MenuItem value="UPI">UPI</MenuItem>
                    </Select>
                  </FormControl>
                </Stack>
              </Box>
            )}

            {/* Mobile Number Input - STEP 1 */}
            {!selectedSeva?.quick_ticket_enabled && !foundDevotee && !showNewDevoteeForm && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Step 1: Enter Devotee Mobile Number *
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    label="Mobile Number"
                    value={mobileNumber}
                    onChange={(e) => setMobileNumber(e.target.value)}
                    placeholder="Enter 10-digit mobile"
                    fullWidth
                    inputProps={{ maxLength: 10 }}
                  />
                  <Button
                    variant="contained"
                    onClick={handleSearchByMobile}
                    disabled={searchingDevotee || mobileNumber.length < 10}
                    sx={{ minWidth: 100 }}
                  >
                    {searchingDevotee ? <CircularProgress size={24} /> : 'Search'}
                  </Button>
                </Box>
              </Box>
            )}

            {/* Found Devotee - STEP 2a */}
            {!selectedSeva?.quick_ticket_enabled && foundDevotee && (
              <Box>
                <Alert severity="success" sx={{ mb: 2 }}>
                  Devotee Found!
                </Alert>
                <Paper sx={{ p: 2, bgcolor: '#E8F5E9' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Devotee Details:
                  </Typography>
                  <Typography variant="body2"><strong>Name:</strong> {foundDevotee.name_prefix ? `${foundDevotee.name_prefix} ` : ''}{foundDevotee.name}</Typography>
                  <Typography variant="body2"><strong>Phone:</strong> {foundDevotee.phone}</Typography>
                  {foundDevotee.address && (
                    <Typography variant="body2"><strong>Address:</strong> {foundDevotee.address}</Typography>
                  )}
                  <Button
                    size="small"
                    onClick={() => {
                      setFoundDevotee(null);
                      setMobileNumber('');
                      setBookingForm((prev) => ({ ...prev, devotee_id: '' }));
                    }}
                    sx={{ mt: 1 }}
                  >
                    Change Devotee
                  </Button>
                </Paper>
              </Box>
            )}

            {/* New Devotee Form - STEP 2b */}
            {!selectedSeva?.quick_ticket_enabled && showNewDevoteeForm && (
              <Box>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Devotee not found. Please enter details to create new devotee.
                </Alert>
                <Paper sx={{ p: 2, bgcolor: '#FFF3E0' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                    New Devotee Details:
                  </Typography>
                  <Stack spacing={2}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <FormControl sx={{ minWidth: 100 }} size="small">
                        <InputLabel>Prefix</InputLabel>
                        <Select
                          value={newDevoteeData.name_prefix}
                          onChange={(e) => setNewDevoteeData({ ...newDevoteeData, name_prefix: e.target.value })}
                          label="Prefix"
                        >
                          <MenuItem value="Sri">Sri</MenuItem>
                          <MenuItem value="Smt">Smt</MenuItem>
                          <MenuItem value="Mr.">Mr.</MenuItem>
                          <MenuItem value="Ms.">Ms.</MenuItem>
                          <MenuItem value="Dr.">Dr.</MenuItem>
                          <MenuItem value="M/s">M/s</MenuItem>
                        </Select>
                      </FormControl>
                      <TextField
                        label="First Name *"
                        placeholder="Enter first name"
                        value={newDevoteeData.first_name}
                        onChange={(e) => setNewDevoteeData({ ...newDevoteeData, first_name: e.target.value })}
                        fullWidth
                        size="small"
                      />
                      <TextField
                        label="Last Name"
                        placeholder="Enter last name"
                        value={newDevoteeData.last_name}
                        onChange={(e) => setNewDevoteeData({ ...newDevoteeData, last_name: e.target.value })}
                        fullWidth
                        size="small"
                      />
                    </Box>
                    <TextField
                      label="Email Address"
                      placeholder="Enter email address (optional)"
                      value={newDevoteeData.email}
                      onChange={(e) => setNewDevoteeData({ ...newDevoteeData, email: e.target.value })}
                      fullWidth
                      size="small"
                    />
                    <TextField
                      label="Address"
                      value={newDevoteeData.address}
                      onChange={(e) => setNewDevoteeData({ ...newDevoteeData, address: e.target.value })}
                      fullWidth
                      size="small"
                    />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <TextField
                        label="City"
                        value={newDevoteeData.city}
                        onChange={(e) => setNewDevoteeData({ ...newDevoteeData, city: e.target.value })}
                        size="small"
                        sx={{ flex: 1 }}
                      />
                      <TextField
                        label="Pincode"
                        value={newDevoteeData.pincode}
                        onChange={(e) => {
                          const pin = (e.target.value || '').replace(/\D/g, '').slice(0, 6);
                          setNewDevoteeData((prev) => ({
                            ...prev,
                            pincode: pin,
                            ...(pin.length < 6 ? { city: '', state: '' } : {}),
                          }));
                          if (pin.length === 6) {
                            fetchPincodeDetails(pin);
                          }
                        }}
                        size="small"
                        inputProps={{ maxLength: 6 }}
                        InputProps={{
                          endAdornment: pincodeLoading ? (
                            <InputAdornment position="end">
                              <CircularProgress size={16} />
                            </InputAdornment>
                          ) : null,
                        }}
                        helperText={newDevoteeData.pincode.length === 6 ? 'City & State will auto-fill' : ''}
                        sx={{ width: '120px' }}
                      />
                    </Box>
                    <TextField
                      label="State"
                      value={newDevoteeData.state}
                      onChange={(e) => setNewDevoteeData({ ...newDevoteeData, state: e.target.value })}
                      fullWidth
                      size="small"
                    />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        variant="contained"
                        onClick={handleCreateDevotee}
                        fullWidth
                        disabled={!newDevoteeData.first_name?.trim() || tenantWriteBlocked}
                      >
                        Create & Continue
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => {
                          setShowNewDevoteeForm(false);
                          setMobileNumber('');
                        }}
                      >
                        Cancel
                      </Button>
                    </Box>
                  </Stack>
                </Paper>
              </Box>
            )}

            {/* Booking Details - Only show after devotee is selected */}
            {!selectedSeva?.quick_ticket_enabled && foundDevotee && (
              <>
                <Typography variant="subtitle2" sx={{ mt: 2, fontWeight: 600, color: '#FF9933' }}>
                  Step 2: Seva Booking Details
                </Typography>

                {/* Booking Date */}
                <TextField
                  label="Booking Date *"
                  type="date"
                  value={bookingForm.booking_date}
                  onChange={(e) => {
                    setBookingForm({ ...bookingForm, booking_date: e.target.value });
                    setBookingError(null);
                  }}
                  InputLabelProps={{ shrink: true }}
                  inputProps={{
                    min: new Date().toISOString().split('T')[0],
                    max:
                      Number(selectedSeva?.advance_booking_days || 0) > 0
                        ? (() => {
                            const d = new Date();
                            d.setDate(d.getDate() + Number(selectedSeva.advance_booking_days));
                            return d.toISOString().split('T')[0];
                          })()
                        : undefined,
                  }}
                  error={Boolean(bookingDateError)}
                  helperText={
                    bookingDateError ||
                    (checkingBookingDate
                      ? 'Checking availability...'
                      : Number(selectedSeva?.advance_booking_days || 0) > 0
                        ? `Can be booked up to ${selectedSeva.advance_booking_days} day(s) in advance`
                        : '')
                  }
                  fullWidth
                />

                {/* Booking Time (if applicable) */}
                {selectedSeva?.time_slot && (
                  <TextField
                    label="Preferred Time"
                    value={bookingForm.booking_time}
                    onChange={(e) => setBookingForm({ ...bookingForm, booking_time: e.target.value })}
                    helperText={`Recommended: ${selectedSeva.time_slot}`}
                    fullWidth
                  />
                )}

                {/* Amount */}
                <TextField
                  label="Amount *"
                  type="number"
                  value={bookingForm.amount_paid}
                  onChange={(e) => setBookingForm({ ...bookingForm, amount_paid: parseFloat(e.target.value) })}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">{'\u20B9'}</InputAdornment>
                  }}
                  fullWidth
                />

                {/* Payment Method */}
                <FormControl fullWidth>
                  <InputLabel>Payment Method *</InputLabel>
                  <Select
                    value={bookingForm.payment_method}
                    onChange={(e) =>
                      setBookingForm({
                        ...bookingForm,
                        payment_method: e.target.value,
                        payment_account_id: '',
                        ...emptyBankPaymentFields,
                      })
                    }
                    label="Payment Method *"
                  >
                    <MenuItem value="Cash">Cash</MenuItem>
                    <MenuItem value="Bank">Bank</MenuItem>
                  </Select>
                </FormControl>

                {bookingForm.payment_method === 'Cash' && (
                  <FormControl fullWidth>
                    <InputLabel>Cash Account Code *</InputLabel>
                    <Select
                      value={bookingForm.payment_account_id}
                      onChange={(e) =>
                        setBookingForm({ ...bookingForm, payment_account_id: e.target.value })
                      }
                      label="Cash Account Code *"
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
                    </Select>
                  </FormControl>
                )}

                {bookingForm.payment_method === 'Bank' && (
                  <>
                    <FormControl fullWidth>
                      <InputLabel>Bank Account Code *</InputLabel>
                      <Select
                        value={bookingForm.payment_account_id}
                        onChange={(e) =>
                          setBookingForm({ ...bookingForm, payment_account_id: e.target.value })
                        }
                        label="Bank Account Code *"
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
                      </Select>
                    </FormControl>

                    <FormControl fullWidth>
                      <InputLabel>Bank Sub-Category *</InputLabel>
                      <Select
                        value={bookingForm.bank_sub_mode}
                        onChange={(e) =>
                          setBookingForm({
                            ...bookingForm,
                            ...emptyBankPaymentFields,
                            bank_sub_mode: e.target.value,
                          })
                        }
                        label="Bank Sub-Category *"
                      >
                        {bankSubModeOptions.map((mode) => (
                          <MenuItem key={mode.value} value={mode.value}>
                            {mode.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {bookingForm.bank_sub_mode === 'UPI' && (
                      <>
                        <TextField
                          label="UPI Transaction Reference *"
                          value={bookingForm.upi_reference_number}
                          onChange={(e) =>
                            setBookingForm({ ...bookingForm, upi_reference_number: e.target.value })
                          }
                          placeholder="Enter UTR / RRN reference"
                          fullWidth
                        />
                        <TextField
                          label="Sender UPI ID (Optional)"
                          value={bookingForm.sender_upi_id}
                          onChange={(e) =>
                            setBookingForm({ ...bookingForm, sender_upi_id: e.target.value })
                          }
                          placeholder="example@upi"
                          fullWidth
                        />
                      </>
                    )}

                    {bookingForm.bank_sub_mode === 'Card' && (
                      <TextField
                        label="Card Number / Transaction Reference *"
                        value={bookingForm.card_number}
                        onChange={(e) =>
                          setBookingForm({ ...bookingForm, card_number: e.target.value })
                        }
                        placeholder="Enter card number or transaction reference"
                        fullWidth
                      />
                    )}

                    {bookingForm.bank_sub_mode === 'Online' && (
                      <TextField
                        label="UTR Reference Number *"
                        value={bookingForm.utr_number}
                        onChange={(e) =>
                          setBookingForm({ ...bookingForm, utr_number: e.target.value })
                        }
                        placeholder="Enter UTR reference"
                        fullWidth
                      />
                    )}

                    {bookingForm.bank_sub_mode === 'Cheque' && (
                      <>
                        <TextField
                          label="Cheque Number *"
                          value={bookingForm.cheque_number}
                          onChange={(e) =>
                            setBookingForm({ ...bookingForm, cheque_number: e.target.value })
                          }
                          fullWidth
                        />
                        <TextField
                          label="Cheque Date *"
                          type="date"
                          value={bookingForm.cheque_date}
                          onChange={(e) =>
                            setBookingForm({ ...bookingForm, cheque_date: e.target.value })
                          }
                          InputLabelProps={{ shrink: true }}
                          fullWidth
                        />
                        <TextField
                          label="Drawn On Bank Name *"
                          value={bookingForm.cheque_bank_name}
                          onChange={(e) =>
                            setBookingForm({ ...bookingForm, cheque_bank_name: e.target.value })
                          }
                          fullWidth
                        />
                        <TextField
                          label="Branch Name *"
                          value={bookingForm.cheque_branch}
                          onChange={(e) =>
                            setBookingForm({ ...bookingForm, cheque_branch: e.target.value })
                          }
                          fullWidth
                        />
                      </>
                    )}
                  </>
                )}

                {/* Additional Names */}
                <TextField
                  label="Seva In Whose Name (Optional)"
                  value={bookingForm.devotee_names}
                  onChange={(e) => setBookingForm({ ...bookingForm, devotee_names: e.target.value })}
                  placeholder="Enter name(s) for whom seva is to be performed"
                  multiline
                  rows={2}
                  fullWidth
                />

                {/* Gotra */}
                <FormControl fullWidth>
                  <InputLabel>Gotra</InputLabel>
                  <Select
                    value={bookingForm.gotra}
                    onChange={(e) => setBookingForm({ ...bookingForm, gotra: e.target.value })}
                    label="Gotra"
                  >
                    <MenuItem value="">
                      <em>Select Gotra</em>
                    </MenuItem>
                    {dropdownOptions.gothras && dropdownOptions.gothras.length > 0 ? (
                      dropdownOptions.gothras.map((gotra) => (
                        <MenuItem key={gotra} value={gotra}>
                          {gotra}
                        </MenuItem>
                      ))
                    ) : (
                      <MenuItem disabled>Loading...</MenuItem>
                    )}
                  </Select>
                </FormControl>

                {/* Nakshatra */}
                <FormControl fullWidth>
                  <InputLabel>Nakshatra</InputLabel>
                  <Select
                    value={bookingForm.nakshatra}
                    onChange={(e) => setBookingForm({ ...bookingForm, nakshatra: e.target.value })}
                    label="Nakshatra"
                  >
                    <MenuItem value="">
                      <em>Select Nakshatra</em>
                    </MenuItem>
                    {dropdownOptions.nakshatras && dropdownOptions.nakshatras.length > 0 ? (
                      dropdownOptions.nakshatras.map((nakshatra) => (
                        <MenuItem key={nakshatra} value={nakshatra}>
                          {nakshatra}
                        </MenuItem>
                      ))
                    ) : (
                      <MenuItem disabled>Loading...</MenuItem>
                    )}
                  </Select>
                </FormControl>

                {/* Rashi */}
                <FormControl fullWidth>
                  <InputLabel>Rashi</InputLabel>
                  <Select
                    value={bookingForm.rashi}
                    onChange={(e) => setBookingForm({ ...bookingForm, rashi: e.target.value })}
                    label="Rashi"
                  >
                    <MenuItem value="">
                      <em>Select Rashi</em>
                    </MenuItem>
                    {dropdownOptions.rashis && dropdownOptions.rashis.length > 0 ? (
                      dropdownOptions.rashis.map((rashi) => (
                        <MenuItem key={rashi} value={rashi}>
                          {rashi}
                        </MenuItem>
                      ))
                    ) : (
                      <MenuItem disabled>Loading...</MenuItem>
                    )}
                  </Select>
                </FormControl>

                {/* Special Request */}
                <TextField
                  label="Special Request / Instructions"
                  value={bookingForm.special_request}
                  onChange={(e) => setBookingForm({ ...bookingForm, special_request: e.target.value })}
                  multiline
                  rows={3}
                  fullWidth
                />

                {/* Priest Assignment */}
                <FormControl fullWidth>
                  <InputLabel>Assign Priest (Optional)</InputLabel>
                  <Select
                    value={bookingForm.priest_id}
                    onChange={(e) => setBookingForm({ ...bookingForm, priest_id: e.target.value })}
                    label="Assign Priest (Optional)"
                  >
                    <MenuItem value="">
                      <em>System Default</em>
                    </MenuItem>
                    {priests.map((p) => (
                      <MenuItem key={p.id} value={p.id}>
                        {p.name} {p.phone ? `(${p.phone})` : ''}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseBookingDialog}>Cancel</Button>
          <Button
            onClick={handleBookingSubmit}
            variant="contained"
            disabled={
              !bookingForm.amount_paid ||
              bookingSuccess ||
              tenantWriteBlocked ||
              checkingBookingDate ||
              Boolean(bookingDateError) ||
              (!selectedSeva?.quick_ticket_enabled && !bookingForm.devotee_id)
            }
          >
            {selectedSeva?.quick_ticket_enabled ? 'Book & Print' : 'Confirm Booking'}
          </Button>
        </DialogActions>
      </Dialog>

      {bookingDialogMinimized && (
        <Box
          sx={{
            position: 'fixed',
            right: 24,
            bottom: 24,
            zIndex: (theme) => theme.zIndex.modal + 1,
          }}
        >
          <Button variant="contained" color="warning" onClick={handleRestoreBookingDialog}>
            Resume Seva Booking
          </Button>
        </Box>
      )}
    </Box>
  );
}

export default Sevas;


