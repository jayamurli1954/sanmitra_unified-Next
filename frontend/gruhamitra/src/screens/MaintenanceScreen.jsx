import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { authService } from '../services/authService';

const MaintenanceScreen = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Bill Generation Form State
  const [billForm, setBillForm] = useState({
    month: new Date().getMonth(), // 0-indexed, will convert
    year: new Date().getFullYear(),
    // Maintenance Base
    override_sqft_rate: '',
    // Water
    override_water_charges: '',
    adjusted_inmates: {}, // { flat_id: adjusted_count }
    // Fixed Expenses
    selected_fixed_expense_codes: [],
    fixed_calculation_method: 'equal',
    override_fixed_expenses: '',
    // Sinking Fund
    sinking_calculation_method: 'equal',
    override_sinking_fund: '',
    // Repair Fund
    repair_fund_calculation_method: 'equal',
    override_repair_fund: '',
    // Corpus Fund
    corpus_fund_calculation_method: 'equal',
    override_corpus_fund: '',
    // Accounting
    auto_post_to_accounting: true
  });

  const [flats, setFlats] = useState([]);
  const [expenseAccounts, setExpenseAccounts] = useState([]);
  const [existingBills, setExistingBills] = useState([]);
  const [generatedBills, setGeneratedBills] = useState(null);
  const [user, setUser] = useState(null);
  const [selectedBillDetails, setSelectedBillDetails] = useState(null);
  const [showExtraChargeModal, setShowExtraChargeModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showReverseModal, setShowReverseModal] = useState(false);
  const [showRegenerateModal, setShowRegenerateModal] = useState(false);
  const [selectedBillForAction, setSelectedBillForAction] = useState(null);
  const [reverseForm, setReverseForm] = useState({ reversal_reason: '', committee_approval: '' });
  const [extraChargeForm, setExtraChargeForm] = useState({ amount: '', description: '' });
  const [paymentForm, setPaymentForm] = useState({ amount: '', payment_mode: 'bank', reference: '' });
  const [regenerateForm, setRegenerateForm] = useState({
    corrected_occupants: '',
    override_maintenance: '',
    override_water: '',
    override_fixed: '',
    override_sinking: '',
    override_repair: '',
    override_corpus: '',
    notes: ''
  });

  const loadBillsForPeriod = useCallback(async () => {
    if (billForm.month === undefined || billForm.month === null || billForm.year === undefined || billForm.year === null) {
      return;
    }

    const month = parseInt(billForm.month) + 1; // Convert from 0-indexed to 1-indexed
    const year = parseInt(billForm.year);

    if (!month || !year || month < 1 || month > 12) {
      return;
    }

    try {
      console.log(`Loading bills for period: month=${month}, year=${year}`);
      const billsRes = await api.get(`/maintenance/bills?month=${month}&year=${year}`);
      console.log('Bills loaded:', billsRes.data?.length || 0, 'bills');
      setExistingBills(billsRes.data || []);
    } catch (err) {
      console.error('Error loading bills for period:', err);
      // Non-critical, continue with empty list
      setExistingBills([]);
    }
  }, [billForm.month, billForm.year]);

  const loadExpenseAccountsForPeriod = useCallback(async () => {
    if (billForm.month === undefined || billForm.month === null || billForm.year === undefined || billForm.year === null) {
      return;
    }

    const month = parseInt(billForm.month) + 1; // Convert from 0-indexed to 1-indexed
    const year = parseInt(billForm.year);

    if (!month || !year || month < 1 || month > 12) {
      return;
    }

    try {
      // Load expense accounts that have transactions for the selected period
      // Only shows accounts with expenses > 0 for that month/year
      console.log(`Loading expense accounts for period: month=${month}, year=${year}`);
      const accountsRes = await api.get(`/maintenance/expense-accounts-for-period?month=${month}&year=${year}`);
      console.log('Expense accounts loaded:', accountsRes.data?.length || 0, 'accounts');
      const accounts = accountsRes.data || [];
      setExpenseAccounts(accounts);
      const fixedCodes = new Set(accounts.filter(acc => !acc.is_water).map(acc => acc.account_code));
      setBillForm(prev => ({
        ...prev,
        selected_fixed_expense_codes: prev.selected_fixed_expense_codes.length > 0
          ? prev.selected_fixed_expense_codes.filter(code => fixedCodes.has(code))
          : Array.from(fixedCodes)
      }));
    } catch (err) {
      console.error('Error loading expense accounts for period:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load expense accounts';
      console.error('Error details:', {
        message: errorMsg,
        status: err.response?.status,
        url: err.config?.url,
        code: err.code
      });

      // If it's a 404, the endpoint might not exist - backend may need restart
      if (err.response?.status === 404) {
        console.warn('Endpoint /maintenance/expense-accounts-for-period not found. Backend may need restart.');
      }
      // Non-critical, continue with empty list
      setExpenseAccounts([]);
    }
  }, [billForm.month, billForm.year]);

  useEffect(() => {
    loadInitialData();
  }, []);

  // Reload expense accounts and bills when month/year changes
  useEffect(() => {
    loadExpenseAccountsForPeriod();
    loadBillsForPeriod();
  }, [loadExpenseAccountsForPeriod, loadBillsForPeriod]);

  const loadInitialData = async () => {
    try {
      // Load user
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);

      // Load flats
      try {
        const flatsRes = await api.get('/flats');
        const flatsData = flatsRes.data || [];
        console.log('Flats loaded:', flatsData.length, 'flats');
        setFlats(flatsData);
        if (flatsData.length === 0) {
          setMessage({
            type: 'error',
            text: 'No flats found. Please add flats before generating bills.\n\nTo add flats:\n1. Go to Settings  Flats & Blocks\n2. Click "Add Flat"\n3. Fill in flat details (Flat Number, Area, Type, etc.)\n4. Save and return here to generate bills.'
          });
        } else {
          // Clear error message if flats are found
          setMessage({ type: '', text: '' });
        }
      } catch (err) {
        console.error('Error loading flats:', err);
        if (err.code === 'CONNECTION_ERROR' || err.message?.includes('Cannot connect')) {
          setMessage({
            type: 'error',
            text: err.message || 'Cannot connect to server. Please check:\n1. Backend is running on http://localhost:8002\n2. Correct API URL in config'
          });
          return; // Don't continue if we can't connect
        } else {
          setMessage({
            type: 'error',
            text: `Failed to load flats: ${err.response?.data?.detail || err.message || 'Unknown error'}`
          });
        }
      }

      // Load expense accounts for selected period (will be called again when month/year changes)
      await loadExpenseAccountsForPeriod();

      // Load bills for selected period (will be called again when month/year changes)
      await loadBillsForPeriod();
    } catch (error) {
      console.error('Error loading initial data:', error);
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to load data.';
      if (error.code === 'CONNECTION_ERROR' || errorMessage.includes('Cannot connect')) {
        setMessage({
          type: 'error',
          text: errorMessage || 'Cannot connect to server. Please check:\n1. Backend is running on http://localhost:8002\n2. Correct API URL in config'
        });
      } else {
        setMessage({ type: 'error', text: errorMessage });
      }
    }
  };

  const _pollBillingJob = async (jobId, month, year) => {
    const MAX_POLLS = 80; // 80 × 3s = 4 minutes
    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, 3000));
      try {
        const res = await api.get(`/maintenance/billing-jobs/${jobId}`);
        const job = res.data;
        if (job.status === 'completed') {
          const billsRes = await api.get(`/maintenance/bills?month=${month}&year=${year}`);
          setExistingBills(billsRes.data || []);
          setMessage({
            type: 'success',
            text: `Generated ${job.total_bills} bills for ${month}/${year}. Total: ₹${(job.total_amount || 0).toLocaleString('en-IN')}`
          });
          return;
        }
        if (job.status === 'failed') {
          setMessage({ type: 'error', text: `Bill generation failed: ${job.error || 'Unknown error'}` });
          return;
        }
        setMessage({ type: 'info', text: `Generating bills for ${month}/${year}… (${job.total_flats} flats)` });
      } catch {
        // transient poll error — keep trying
      }
    }
    setMessage({ type: 'error', text: 'Bill generation is taking longer than expected. Please refresh the page to check status.' });
  };

  const handleGenerateBills = async () => {
    setMessage({ type: '', text: '' });
    setLoading(true);

    // Validate month/year
    const month = parseInt(billForm.month) + 1; // Convert from 0-indexed to 1-indexed
    const year = parseInt(billForm.year);

    if (!month || !year) {
      setMessage({ type: 'error', text: 'Please select month and year.' });
      setLoading(false);
      return;
    }

    // Prepare request payload
    const requestPayload = {
      month,
      year,
      override_sqft_rate: billForm.override_sqft_rate ? parseFloat(billForm.override_sqft_rate) : null,
      override_water_charges: billForm.override_water_charges ? parseFloat(billForm.override_water_charges) : null,
      adjusted_inmates: Object.keys(billForm.adjusted_inmates).length > 0 ? billForm.adjusted_inmates : null,
      selected_fixed_expense_codes: billForm.selected_fixed_expense_codes,
      fixed_calculation_method: billForm.fixed_calculation_method,
      override_fixed_expenses: billForm.override_fixed_expenses ? parseFloat(billForm.override_fixed_expenses) : null,
      sinking_calculation_method: billForm.sinking_calculation_method,
      override_sinking_fund: billForm.override_sinking_fund ? parseFloat(billForm.override_sinking_fund) : null,
      repair_fund_calculation_method: billForm.repair_fund_calculation_method,
      override_repair_fund: billForm.override_repair_fund ? parseFloat(billForm.override_repair_fund) : null,
      corpus_fund_calculation_method: billForm.corpus_fund_calculation_method,
      override_corpus_fund: billForm.override_corpus_fund ? parseFloat(billForm.override_corpus_fund) : null,
      auto_post_to_accounting: billForm.auto_post_to_accounting
    };

    try {
      const response = await api.post('/maintenance/generate-bills', requestPayload);
      const data = response.data;

      // Background job response (new path)
      if (data.job_id) {
        setMessage({ type: 'info', text: `Generating bills for ${month}/${year} (${data.total_flats} flats)…` });
        await _pollBillingJob(data.job_id, month, year);
        return;
      }

      // Sync fallback — should not occur in normal operation
      setGeneratedBills(data);
      setMessage({
        type: 'success',
        text: `Generated ${data.total_bills_generated} bills for ${month}/${year}. Total: ₹${(data.total_amount || 0).toLocaleString('en-IN')}`
      });
      const billsRes = await api.get(`/maintenance/bills?month=${month}&year=${year}`);
      setExistingBills(billsRes.data || []);
    } catch (error) {
      console.error('Error generating bills:', error);
      let errorText = error.response?.data?.detail || error.message || 'Failed to generate bills. Please check your inputs and try again.';
      if (error.code === 'CONNECTION_ERROR' || error.message?.includes('Cannot connect')) {
        errorText = error.message || 'Cannot connect to server. Please check:\n1. Backend is running\n2. Correct API URL in config';
      }
      setMessage({ type: 'error', text: errorText });
    } finally {
      setLoading(false);
    }
  };

  const handlePostBills = async () => {
    const month = generatedBills?.month || (parseInt(billForm.month) + 1);
    const year = generatedBills?.year || parseInt(billForm.year);
    const hasUnpostedBills = (generatedBills?.bills || existingBills || []).some(b => !b.is_posted && b.status !== 'reversed');

    if (!month || !year || !hasUnpostedBills) {
      setMessage({ type: 'error', text: 'No unposted bills found for the selected month.' });
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await api.post('/maintenance/post-bills', {
        month,
        year
      });

      setMessage({
        type: 'success',
        text: `Successfully posted ${response.data.total_bills_generated} bills to accounting.`
      });

      // Reload bills to show updated status
      const billsRes = await api.get(`/maintenance/bills?month=${month}&year=${year}`);
      setExistingBills(billsRes.data || []);
      if (generatedBills) {
        setGeneratedBills({
          ...generatedBills,
          bills: generatedBills.bills.map(b => ({ ...b, is_posted: true, status: 'posted' }))
        });
      }
    } catch (error) {
      console.error('Error posting bills:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || error.message || 'Failed to post bills to accounting.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleInmateAdjustment = (flatId, value) => {
    const adjusted = { ...billForm.adjusted_inmates };
    if (value === '' || value === null) {
      delete adjusted[flatId];
    } else {
      adjusted[flatId] = parseInt(value);
    }
    setBillForm({ ...billForm, adjusted_inmates: adjusted });
  };

  const formatCurrency = (amount) => {
    if (!amount) return ' 0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const billPaidAmount = (bill) => {
    const status = String(bill?.status || bill?.payment_status || '').toLowerCase();
    const total = parseFloat(bill?.amount || 0);
    if (['paid', 'collected', 'settled'].includes(status)) {
      return total;
    }
    return parseFloat(bill?.paid_amount || bill?.amount_paid || bill?.collected_amount || 0);
  };

  const billOutstandingAmount = (bill) => {
    const total = parseFloat(bill?.amount || 0);
    const explicit = bill?.outstanding_amount ?? bill?.balance_amount;
    if (explicit !== undefined && explicit !== null && explicit !== '') {
      return Math.max(0, parseFloat(explicit) || 0);
    }
    return Math.max(0, total - billPaidAmount(bill));
  };

  const openPaymentModal = (bill) => {
    const billWithId = { ...bill, id: bill.id || bill._id || String(bill.id) };
    const outstanding = billOutstandingAmount(billWithId);
    setSelectedBillForAction(billWithId);
    setPaymentForm({
      amount: outstanding ? outstanding.toFixed(2) : '',
      payment_mode: 'bank',
      reference: ''
    });
    setShowPaymentModal(true);
  };

  const handleRecordPayment = async () => {
    if (!selectedBillForAction?.id) {
      setMessage({ type: 'error', text: 'Bill ID is missing. Refresh bills and try again.' });
      return;
    }
    const amount = parseFloat(paymentForm.amount);
    if (!amount || amount <= 0) {
      setMessage({ type: 'error', text: 'Enter a valid payment amount.' });
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });
    try {
      const today = new Date().toISOString().split('T')[0];
      const response = await api.post('/housing/maintenance-collections', {
        bill_id: selectedBillForAction.id,
        amount,
        flat_number: selectedBillForAction.flat_number,
        resident_name: selectedBillForAction.member_name || selectedBillForAction.resident_name || null,
        payment_mode: paymentForm.payment_mode || 'bank',
        collected_on: today,
        reference: paymentForm.reference || null
      });
      setMessage({
        type: 'success',
        text: `Payment recorded. Bill status: ${response.data.bill_status || 'updated'}.`
      });
      setShowPaymentModal(false);
      setSelectedBillForAction(null);
      setPaymentForm({ amount: '', payment_mode: 'bank', reference: '' });
      await loadBillsForPeriod();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || error.message || 'Failed to record payment.'
      });
    } finally {
      setLoading(false);
    }
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const waterExpenseAccounts = expenseAccounts.filter(acc => acc.is_water);
  const fixedExpenseAccounts = expenseAccounts.filter(acc => !acc.is_water);
  const totalWaterFromLedger = waterExpenseAccounts.reduce((sum, acc) => sum + (parseFloat(acc.total_amount) || 0), 0);

  // Component to display bill breakdown
  const BillBreakdownView = ({ bill }) => {
    const breakdown = bill.breakdown || {};
    const components = [];

    // Maintenance Amount
    if (bill.maintenance_amount || breakdown.maintenance_sqft) {
      components.push({
        label: 'Maintenance Charges',
        amount: bill.maintenance_amount || breakdown.maintenance_sqft || 0,
        details: breakdown.sqft_calculation || breakdown.maintenance_calculation
      });
    }

    // Water Amount
    if (bill.water_amount || breakdown.water_charges) {
      const waterAmount = bill.water_amount || breakdown.water_charges || 0;

      // Use correct field names from backend: water_per_person_rate and inmates_used
      // Check multiple possible field names for backward compatibility
      const perPersonRate = breakdown.water_per_person_rate ||
        breakdown.water_per_person ||
        breakdown.per_person_water_charge ||
        0;

      // Use inmates_used (actual count used in calculation) or fallback to occupants
      const occupantsUsed = breakdown.inmates_used !== undefined && breakdown.inmates_used !== null
        ? breakdown.inmates_used
        : (breakdown.occupants !== undefined && breakdown.occupants !== null
          ? breakdown.occupants
          : (breakdown.number_of_occupants || 0));

      let displayDetails = breakdown.water_calculation;

      // If calculation string doesn't exist, create it from the values
      if (!displayDetails) {
        if (breakdown.is_vacant || breakdown.vacancy_fee_applied) {
          displayDetails = `Vacant flat - Minimum charge`;
        } else if (perPersonRate > 0 && occupantsUsed > 0) {
          // Format with 3 decimal places for per person rate (e.g., 411.585)
          displayDetails = `Per person: ${perPersonRate.toFixed(3)}, Occupants: ${occupantsUsed}`;
        } else if (waterAmount > 0 && occupantsUsed > 0) {
          // Calculate rate from amount and occupants if rate is missing
          const calculatedRate = (waterAmount / occupantsUsed).toFixed(3);
          displayDetails = `Per person: ${calculatedRate}, Occupants: ${occupantsUsed}`;
        } else if (waterAmount > 0) {
          displayDetails = `Water charges: ${waterAmount.toFixed(2)}`;
        } else {
          displayDetails = '-';
        }
      }

      components.push({
        label: 'Water Charges',
        amount: waterAmount,
        details: displayDetails
      });
    }

    // Fixed Expenses
    if (bill.fixed_amount || breakdown.fixed_expenses || breakdown.fixed_expenses_equal || breakdown.shared_fixed_expenses) {
      const fixedAmount = bill.fixed_amount || breakdown.fixed_expenses || breakdown.fixed_expenses_equal || breakdown.shared_fixed_expenses || 0;
      components.push({
        label: 'Fixed Expenses',
        amount: fixedAmount,
        details: breakdown.fixed_expenses_list ?
          breakdown.fixed_expenses_list.map(exp => `${exp.name}: ${exp.amount}`).join(', ') :
          breakdown.fixed_expenses_calculation
      });
    }

    // Sinking Fund
    if (bill.sinking_fund_amount || breakdown.sinking_fund || breakdown.sinking_fund_sqft) {
      components.push({
        label: 'Sinking Fund',
        amount: bill.sinking_fund_amount || breakdown.sinking_fund || breakdown.sinking_fund_sqft || 0,
        details: breakdown.sinking_fund_calculation
      });
    }

    // Repair Fund
    if (bill.repair_fund_amount || breakdown.repair_fund) {
      components.push({
        label: 'Repair Fund',
        amount: bill.repair_fund_amount || breakdown.repair_fund || 0,
        details: breakdown.repair_fund_calculation
      });
    }

    // Association Fund
    if (bill.association_fund_amount || breakdown.association_fund) {
      components.push({
        label: 'Association Fund',
        amount: bill.association_fund_amount || breakdown.association_fund || 0,
        details: breakdown.association_fund_calculation
      });
    }

    // Corpus Fund
    if (bill.corpus_fund_amount || breakdown.corpus_fund) {
      components.push({
        label: 'Corpus Fund',
        amount: bill.corpus_fund_amount || breakdown.corpus_fund || 0,
        details: breakdown.corpus_fund_calculation
      });
    }

    // Late Fee
    if (bill.late_fee_amount || breakdown.late_fee) {
      components.push({
        label: 'Late Fee',
        amount: bill.late_fee_amount || breakdown.late_fee || 0,
        details: breakdown.late_fee_calculation
      });
    }

    // Arrears
    if (bill.arrears_amount) {
      components.push({
        label: 'Arrears',
        amount: bill.arrears_amount || 0,
        details: 'Previous month outstanding'
      });
    }

    // Supplementary Charges
    if (breakdown.supplementary_charges && breakdown.supplementary_charges.length > 0) {
      breakdown.supplementary_charges.forEach((supp, idx) => {
        components.push({
          label: supp.name || `Supplementary Charge ${idx + 1}`,
          amount: supp.amount || 0,
          details: supp.description || supp.calculation
        });
      });
    }

    const total = components.reduce((sum, comp) => sum + (parseFloat(comp.amount) || 0), 0);

    return (
      <div style={{ padding: '15px', backgroundColor: 'white', borderRadius: '8px', border: '2px solid #007AFF' }}>
        <h3 style={{ marginTop: 0, color: '#007AFF', borderBottom: '2px solid #007AFF', paddingBottom: '10px' }}>
           Bill Breakdown for {bill.flat_number}
        </h3>
        <div style={{ marginTop: '15px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#f0f0f0' }}>
                <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Component</th>
                <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #ddd' }}>Amount ()</th>
                <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {components.map((comp, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px', fontWeight: '500' }}>{comp.label}</td>
                  <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'monospace' }}>
                    {parseFloat(comp.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '8px', fontSize: '12px', color: '#666' }}>{comp.details || '-'}</td>
                </tr>
              ))}
              <tr style={{ backgroundColor: '#f9f9f9', fontWeight: 'bold', borderTop: '2px solid #007AFF' }}>
                <td style={{ padding: '12px', fontSize: '16px' }}>TOTAL AMOUNT</td>
                <td style={{ padding: '12px', textAlign: 'right', fontSize: '16px', color: '#007AFF', fontFamily: 'monospace' }}>
                  {total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td style={{ padding: '12px' }}></td>
              </tr>
            </tbody>
          </table>
        </div>
        {bill.bill_number && (
          <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f0f8ff', borderRadius: '4px', fontSize: '12px' }}>
            <strong>Bill Number:</strong> {bill.bill_number} |
            <strong> Month/Year:</strong> {monthNames[(bill.month || 1) - 1]} {bill.year}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <img
            src="/gruhamitra/GruhaMitra_Logo.png"
            alt="GruhaMitra Logo"
            className="dashboard-logo"
            onClick={() => navigate('/dashboard')}
            style={{ cursor: 'pointer' }}
          />
          <div className="dashboard-header-text">
            <div className="dashboard-society-name">
              {user?.society_name || 'GruhaMitra Demo Society'}
            </div>
            <div className="dashboard-tagline">
              Your Society, Digitally Simplified
            </div>
          </div>
        </div>
        <div className="dashboard-header-right">
          <span className="dashboard-header-icon" title="Notifications"></span>
          <div
            className="dashboard-user-info"
            onClick={() => navigate('/profile')}
            style={{ cursor: 'pointer' }}
          >
            <div className="dashboard-user-name">{user?.name || user?.email}</div>
            <div className="dashboard-user-role">{user?.role || 'Admin'}</div>
          </div>
          <button onClick={async () => {
            await authService.logout();
            window.location.href = '/gruhamitra/login';
          }} className="dashboard-logout-button">
             Logout
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h1 className="settings-title" style={{ margin: 0 }}> Maintenance Bill Generation</h1>
          <button onClick={() => navigate('/dashboard')} className="settings-back-btn">
            Back to Dashboard
          </button>
        </div>

        <div className="settings-content">
          {message.text && (
            <div className={`message ${message.type}`} style={{
              marginBottom: '20px',
              padding: '15px',
              borderRadius: '8px',
              backgroundColor: message.type === 'error' ? '#fee' : message.type === 'success' ? '#efe' : '#eef',
              border: `1px solid ${message.type === 'error' ? '#f44' : message.type === 'success' ? '#4f4' : '#44f'}`,
              color: message.type === 'error' ? '#c00' : message.type === 'success' ? '#0c0' : '#00c',
              whiteSpace: 'pre-line', // Allow line breaks in error messages
              fontSize: '14px',
              lineHeight: '1.6'
            }}>
              {message.text}
              {message.type === 'error' && message.text.includes('No flats found') && (
                <div style={{ marginTop: '15px' }}>
                  <button
                    onClick={() => navigate('/settings?tab=flats')}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#007AFF',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: 'bold',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                    }}
                  >
                     Go to Settings  Add Flats
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Bill Generation Form */}
          <div className="settings-section">
            <h2 className="settings-section-title">Generate Monthly Bills</h2>

            <div className="settings-form">
              <div className="settings-form-row">
                <div className="settings-form-group">
                  <label>Month *</label>
                  <select
                    value={billForm.month}
                    onChange={(e) => setBillForm({ ...billForm, month: parseInt(e.target.value) })}
                    required
                  >
                    {monthNames.map((name, idx) => (
                      <option key={idx} value={idx}>{name}</option>
                    ))}
                  </select>
                </div>
                <div className="settings-form-group">
                  <label>Year *</label>
                  <input
                    type="number"
                    value={billForm.year}
                    onChange={(e) => setBillForm({ ...billForm, year: parseInt(e.target.value) })}
                    min="2020"
                    max="2100"
                    required
                  />
                </div>
              </div>

              {/* Maintenance Base (Sq.ft  Rate, 0 if not used) */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <h3>1. Maintenance Base (Sq.ft Calculation)</h3>
                <div className="settings-form-group">
                  <label>Maintenance Rate per Sq.ft () - Leave 0 if not calculating by area</label>
                  <input
                    type="number"
                    step="0.01"
                    value={billForm.override_sqft_rate}
                    onChange={(e) => setBillForm({ ...billForm, override_sqft_rate: e.target.value })}
                    placeholder="e.g., 5.00 (or 0 to skip)"
                  />
                  <small style={{ color: '#666' }}>If rate is 0, maintenance not calculated by area</small>
                </div>
              </div>

              {/* Water Charges (Per Person with Adjusted Inmates) */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <h3>2. Water Charges (Per Person Calculation)</h3>
                <div className="settings-form-group">
                  <label>Override Total Water Charges () - Leave empty to auto-calculate from water expense accounts</label>
                  <input
                    type="number"
                    step="0.01"
                    value={billForm.override_water_charges}
                    onChange={(e) => setBillForm({ ...billForm, override_water_charges: e.target.value })}
                    placeholder="Auto-calculated if empty"
                  />
                  {waterExpenseAccounts.length > 0 && !billForm.override_water_charges && (
                    <div style={{ marginTop: '10px', padding: '10px', backgroundColor: '#e7f3ff', borderRadius: '4px', color: '#333' }}>
                      <strong>Auto water total from ledger:</strong> {totalWaterFromLedger.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      <div style={{ marginTop: '4px', fontSize: '13px' }}>
                        {waterExpenseAccounts.map(acc => `${acc.account_code} - ${acc.account_name}: ${acc.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`).join(', ')}
                      </div>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: '15px' }}>
                  <label style={{ fontWeight: 'bold', marginBottom: '10px', display: 'block' }}>
                    Adjust Inmates for Water Calculation (For guests/vacations {'>'}7 days)
                  </label>
                  <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #ddd', padding: '10px', borderRadius: '4px' }}>
                    {flats.map(flat => (
                      <div key={flat.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', padding: '5px' }}>
                        <span>{flat.flat_number} (Current: {flat.occupants || 0} inmates)</span>
                        <input
                          type="number"
                          min="0"
                          style={{ width: '80px', padding: '5px' }}
                          value={billForm.adjusted_inmates[flat.id] || ''}
                          onChange={(e) => handleInmateAdjustment(flat.id, e.target.value)}
                          placeholder="Adjusted"
                        />
                      </div>
                    ))}
                  </div>
                  <small style={{ color: '#666' }}>Leave empty to use flat's current occupant count</small>
                </div>
              </div>

              {/* Fixed Expenses (Admin Selection) */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <h3>3. Fixed Expenses (Admin Selection)</h3>
                <div className="settings-form-group">
                  <label style={{ fontWeight: 'bold', marginBottom: '10px', display: 'block' }}>
                    Select Expense Accounts to Include (Admin selects which expenses to include)
                  </label>
                  {fixedExpenseAccounts.length === 0 ? (
                    <div style={{ padding: '15px', backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '4px', color: '#856404' }}>
                      <p><strong>No expense accounts with transactions found for {monthNames[billForm.month]} {billForm.year}.</strong></p>
                      <p style={{ marginTop: '8px' }}>
                        Only expense accounts with transactions (expenses {'>'} 0) for the selected bill period are shown.
                        <br />
                        If you expect expenses, ensure transactions are recorded for this month/year in Accounting.
                      </p>
                    </div>
                  ) : (
                    <div style={{
                      maxHeight: '200px',
                      overflowY: 'auto',
                      border: '1px solid #ddd',
                      padding: '15px',
                      borderRadius: '4px',
                      backgroundColor: '#fff'
                    }}>
                      {fixedExpenseAccounts.map(acc => (
                        <label
                          key={acc.account_code}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            marginBottom: '10px',
                            padding: '8px',
                            cursor: 'pointer',
                            borderRadius: '4px',
                            backgroundColor: billForm.selected_fixed_expense_codes.includes(acc.account_code) ? '#e7f3ff' : 'transparent',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseEnter={(e) => {
                            if (!billForm.selected_fixed_expense_codes.includes(acc.account_code)) {
                              e.currentTarget.style.backgroundColor = '#f5f5f5';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!billForm.selected_fixed_expense_codes.includes(acc.account_code)) {
                              e.currentTarget.style.backgroundColor = 'transparent';
                            }
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={billForm.selected_fixed_expense_codes.includes(acc.account_code)}
                            onChange={(e) => {
                              const codes = e.target.checked
                                ? [...billForm.selected_fixed_expense_codes, acc.account_code]
                                : billForm.selected_fixed_expense_codes.filter(c => c !== acc.account_code);
                              setBillForm({ ...billForm, selected_fixed_expense_codes: codes });
                            }}
                            style={{
                              marginRight: '10px',
                              width: '18px',
                              height: '18px',
                              cursor: 'pointer'
                            }}
                          />
                          <div style={{ flex: 1 }}>
                            <strong style={{ color: '#333' }}>{acc.account_code}</strong> - {acc.account_name}
                            <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                              Expense for period: <strong style={{ color: '#c00' }}>{acc.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                              {acc.transaction_count > 0 && (
                                <span style={{ marginLeft: '8px', color: '#888' }}>
                                  ({acc.transaction_count} transaction{acc.transaction_count !== 1 ? 's' : ''})
                                </span>
                              )}
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                  {fixedExpenseAccounts.length > 0 && (
                    <small style={{ color: '#666', display: 'block', marginTop: '8px' }}>
                      Showing only accounts with expenses {'>'} 0 for {monthNames[billForm.month]} {billForm.year}.
                      Selected: {billForm.selected_fixed_expense_codes.length} account(s).
                      Total expenses from selected accounts will be distributed based on the method below.
                    </small>
                  )}
                </div>
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Distribution Method</label>
                    <select
                      value={billForm.fixed_calculation_method}
                      onChange={(e) => setBillForm({ ...billForm, fixed_calculation_method: e.target.value })}
                    >
                      <option value="equal">Equal per Flat</option>
                      <option value="sqft">By Sq.ft (Proportionate)</option>
                    </select>
                  </div>
                  <div className="settings-form-group">
                    <label>Override Total Fixed Expenses () - Leave empty to use selected accounts</label>
                    <input
                      type="number"
                      step="0.01"
                      value={billForm.override_fixed_expenses}
                      onChange={(e) => setBillForm({ ...billForm, override_fixed_expenses: e.target.value })}
                      placeholder="Auto-calculated if empty"
                    />
                  </div>
                </div>
              </div>

              {/* Sinking Fund */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <h3>4. Sinking Fund</h3>
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Calculation Method</label>
                    <select
                      value={billForm.sinking_calculation_method}
                      onChange={(e) => setBillForm({ ...billForm, sinking_calculation_method: e.target.value })}
                    >
                      <option value="equal">Equal per Flat</option>
                      <option value="sqft">Per Sq.ft</option>
                    </select>
                  </div>
                  <div className="settings-form-group">
                    <label>Total Sinking Fund to Collect () - Leave empty to use settings</label>
                    <input
                      type="number"
                      step="0.01"
                      value={billForm.override_sinking_fund}
                      onChange={(e) => setBillForm({ ...billForm, override_sinking_fund: e.target.value })}
                      placeholder="From settings if empty"
                    />
                  </div>
                </div>
              </div>

              {/* Repair Fund */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <h3>5. Repair Fund</h3>
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Calculation Method</label>
                    <select
                      value={billForm.repair_fund_calculation_method}
                      onChange={(e) => setBillForm({ ...billForm, repair_fund_calculation_method: e.target.value })}
                    >
                      <option value="equal">Equal per Flat</option>
                      <option value="sqft">Per Sq.ft</option>
                    </select>
                  </div>
                  <div className="settings-form-group">
                    <label>Total Repair Fund to Collect () - Leave empty to use settings</label>
                    <input
                      type="number"
                      step="0.01"
                      value={billForm.override_repair_fund}
                      onChange={(e) => setBillForm({ ...billForm, override_repair_fund: e.target.value })}
                      placeholder="From settings if empty"
                    />
                  </div>
                </div>
              </div>

              {/* Corpus Fund */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <h3>6. Corpus Fund</h3>
                <div className="settings-form-row">
                  <div className="settings-form-group">
                    <label>Calculation Method</label>
                    <select
                      value={billForm.corpus_fund_calculation_method}
                      onChange={(e) => setBillForm({ ...billForm, corpus_fund_calculation_method: e.target.value })}
                    >
                      <option value="equal">Equal per Flat</option>
                      <option value="sqft">Per Sq.ft</option>
                    </select>
                  </div>
                  <div className="settings-form-group">
                    <label>Total Corpus Fund to Collect () - Leave empty to use settings</label>
                    <input
                      type="number"
                      step="0.01"
                      value={billForm.override_corpus_fund}
                      onChange={(e) => setBillForm({ ...billForm, override_corpus_fund: e.target.value })}
                      placeholder="From settings if empty"
                    />
                  </div>
                </div>
              </div>

              {/* Accounting Posting */}
              <div className="settings-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '8px' }}>
                <h3>7. Accounting Posting</h3>
                <div className="settings-form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={billForm.auto_post_to_accounting}
                      onChange={(e) => setBillForm({ ...billForm, auto_post_to_accounting: e.target.checked })}
                    />
                    <span style={{ marginLeft: '8px' }}>Auto-post to Accounting (Debit 12001, Credit 41001/41002/etc)</span>
                  </label>
                  <small style={{ color: '#666', display: 'block', marginTop: '5px' }}>
                    Automatically creates journal entries with double-entry validation
                  </small>
                </div>
              </div>

              <div className="settings-form-actions" style={{ marginTop: '30px' }}>
                <button
                  className="settings-save-btn"
                  onClick={handleGenerateBills}
                  disabled={loading}
                >
                  {loading ? 'Generating...' : 'Generate Bills'}
                </button>
                {((generatedBills && generatedBills.bills.some(b => !b.is_posted && b.status !== 'reversed')) ||
                  (!generatedBills && existingBills.some(b => !b.is_posted && b.status !== 'reversed'))) && (
                  <button
                    className="settings-action-btn"
                    onClick={handlePostBills}
                    disabled={loading}
                    style={{ marginLeft: '10px' }}
                  >
                    {loading ? 'Posting...' : 'Post to Accounting'}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Generated Bills Summary */}
          {generatedBills && (
            <div className="settings-section" style={{ marginTop: '30px' }}>
              <h2 className="settings-section-title">Generated Bills Summary</h2>
              <div style={{ backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
                <p><strong>Total Bills:</strong> {generatedBills.total_bills_generated}</p>
                <p><strong>Total Amount:</strong> {formatCurrency(generatedBills.total_amount)}</p>
                <p><strong>Month/Year:</strong> {monthNames[generatedBills.month - 1]} {generatedBills.year}</p>
              </div>

              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Flat Number</th>
                      <th>Amount ()</th>
                      <th>Status</th>
                      <th>Posted</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {generatedBills.bills.slice(0, 20).map(bill => (
                      <React.Fragment key={bill.id}>
                        <tr>
                          <td><strong>{bill.flat_number}</strong></td>
                          <td style={{ textAlign: 'right' }}><strong>{bill.amount.toLocaleString('en-IN')}</strong></td>
                          <td>{bill.status}</td>
                          <td>{bill.is_posted ? 'Yes' : 'No'}</td>
                          <td>
                            <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                              <button
                                onClick={() => setSelectedBillDetails(selectedBillDetails === bill.id ? null : bill.id)}
                                style={{
                                  padding: '5px 10px',
                                  backgroundColor: selectedBillDetails === bill.id ? '#ff6b35' : '#007AFF',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '12px'
                                }}
                              >
                                {selectedBillDetails === bill.id ? 'Hide Details' : 'View Details'}
                              </button>
                              {/* Allow reversal for both posted and unposted bills */}
                              <button
                                onClick={() => {
                                  console.log('Bill clicked for reversal:', bill);
                                  console.log('Bill ID:', bill.id, 'Bill _id:', bill._id);
                                  // Ensure we have the bill with all fields
                                  const billWithId = {
                                    ...bill,
                                    id: bill.id || bill._id || String(bill.id) // Ensure id is present
                                  };
                                  console.log('Bill with ID:', billWithId);
                                  setSelectedBillForAction(billWithId);
                                  setShowReverseModal(true);
                                }}
                                style={{
                                  padding: '5px 10px',
                                  backgroundColor: '#ff3b30',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '12px'
                                }}
                              >
                                Reverse
                              </button>
                            </div>
                          </td>
                        </tr>
                        {selectedBillDetails === bill.id && (
                          <tr>
                            <td colSpan="5" style={{ padding: '20px', backgroundColor: '#f9f9f9' }}>
                              <BillBreakdownView bill={bill} />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
                {generatedBills.bills.length > 20 && (
                  <p style={{ marginTop: '10px', color: '#666' }}>
                    Showing first 20 of {generatedBills.bills.length} bills
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Existing Bills */}
          <div className="settings-section" style={{ marginTop: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h2 className="settings-section-title" style={{ margin: 0 }}>
                Existing Bills for {monthNames[billForm.month]} {billForm.year}
              </h2>
              <button
                onClick={loadBillsForPeriod}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#007AFF',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                 Refresh Bills
              </button>
            </div>
            {existingBills.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', backgroundColor: '#f9f9f9', borderRadius: '8px', color: '#666' }}>
                <p>No bills found for {monthNames[billForm.month]} {billForm.year}.</p>
                <p style={{ fontSize: '14px', marginTop: '10px' }}>
                  Generate bills using the form above, or select a different month/year.
                </p>
                <p style={{ fontSize: '14px', marginTop: '10px', color: '#007AFF' }}>
                  If you reversed a bill, you can regenerate it using the "Generate Bills" form above with manual overrides.
                </p>
              </div>
            ) : (
              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Flat Number</th>
                      <th>Amount ()</th>
                      <th>Paid ()</th>
                      <th>Outstanding ()</th>
                      <th>Status</th>
                      <th>Posted</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {existingBills.map(bill => (
                      <React.Fragment key={bill.id}>
                        <tr>
                          <td><strong>{bill.flat_number}</strong></td>
                          <td style={{ textAlign: 'right' }}><strong>{bill.amount.toLocaleString('en-IN')}</strong></td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(billPaidAmount(bill))}</td>
                          <td style={{ textAlign: 'right', color: billOutstandingAmount(bill) > 0 ? '#FF3B30' : '#34C759', fontWeight: '600' }}>
                            {formatCurrency(billOutstandingAmount(bill))}
                          </td>
                          <td>{bill.status}</td>
                          <td>{bill.is_posted ? 'Yes' : 'No'}</td>
                          <td>{new Date(bill.created_at).toLocaleDateString()}</td>
                          <td>
                            <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                              <button
                                onClick={() => setSelectedBillDetails(selectedBillDetails === bill.id ? null : bill.id)}
                                style={{
                                  padding: '5px 10px',
                                  backgroundColor: selectedBillDetails === bill.id ? '#ff6b35' : '#007AFF',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '12px'
                                }}
                              >
                                {selectedBillDetails === bill.id ? 'Hide Details' : 'View Details'}
                              </button>
                              {!bill.is_posted && bill.status !== 'reversed' && (
                                <button
                                  onClick={() => {
                                    setSelectedBillForAction({ ...bill, id: bill.id || bill._id || String(bill.id) });
                                    setExtraChargeForm({ amount: '', description: '' });
                                    setShowExtraChargeModal(true);
                                  }}
                                  style={{
                                    padding: '5px 10px',
                                    backgroundColor: '#8e44ad',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                  }}
                                >
                                  Extra Charge
                                </button>
                              )}
                              {bill.is_posted && bill.status !== 'reversed' && billOutstandingAmount(bill) > 0 && (
                                <button
                                  onClick={() => openPaymentModal(bill)}
                                  style={{
                                    padding: '5px 10px',
                                    backgroundColor: '#34C759',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                  }}
                                >
                                  Record Payment
                                </button>
                              )}
                              {/* Allow reversal for both posted and unposted bills */}
                              <button
                                onClick={() => {
                                  console.log('Bill clicked for reversal:', bill);
                                  console.log('Bill ID:', bill.id, 'Bill _id:', bill._id);
                                  // Ensure we have the bill with all fields
                                  const billWithId = {
                                    ...bill,
                                    id: bill.id || bill._id || String(bill.id) // Ensure id is present
                                  };
                                  console.log('Bill with ID:', billWithId);
                                  setSelectedBillForAction(billWithId);
                                  setShowReverseModal(true);
                                }}
                                style={{
                                  padding: '5px 10px',
                                  backgroundColor: '#ff3b30',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '12px'
                                }}
                              >
                                Reverse
                              </button>
                            </div>
                          </td>
                        </tr>
                        {selectedBillDetails === bill.id && (
                          <tr>
                            <td colSpan="8" style={{ padding: '20px', backgroundColor: '#f9f9f9' }}>
                              <BillBreakdownView bill={bill} />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Record Payment Modal */}
      {showPaymentModal && selectedBillForAction && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            maxWidth: '500px',
            width: '90%',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <h2 style={{ marginTop: 0 }}>Record Payment - {selectedBillForAction.flat_number}</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>
              Outstanding: <strong>{formatCurrency(billOutstandingAmount(selectedBillForAction))}</strong>
            </p>
            <div className="settings-form-group" style={{ marginBottom: '15px' }}>
              <label>Payment Amount *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max={billOutstandingAmount(selectedBillForAction)}
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
              />
            </div>
            <div className="settings-form-group" style={{ marginBottom: '15px' }}>
              <label>Payment Mode</label>
              <select
                value={paymentForm.payment_mode}
                onChange={(e) => setPaymentForm({ ...paymentForm, payment_mode: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
              >
                <option value="bank">Bank</option>
                <option value="upi">UPI</option>
                <option value="cash">Cash</option>
                <option value="cheque">Cheque</option>
              </select>
            </div>
            <div className="settings-form-group" style={{ marginBottom: '20px' }}>
              <label>Reference / Receipt No.</label>
              <input
                type="text"
                value={paymentForm.reference}
                onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })}
                placeholder="Optional bank/UPI/receipt reference"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowPaymentModal(false);
                  setSelectedBillForAction(null);
                  setPaymentForm({ amount: '', payment_mode: 'bank', reference: '' });
                }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleRecordPayment}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  backgroundColor: loading ? '#ccc' : '#34C759',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Recording...' : 'Record Payment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reverse Bill Modal */}
      {showReverseModal && selectedBillForAction && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            maxWidth: '500px',
            width: '90%',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <h2 style={{ marginTop: 0 }}>Reverse Bill - {selectedBillForAction.flat_number}</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>
              This will reverse the bill and create a reversal journal entry. You can then regenerate the bill with corrected values.
            </p>
            {/* Show message inside modal */}
            {message.text && message.type && (
              <div style={{
                padding: '10px',
                marginBottom: '15px',
                borderRadius: '4px',
                backgroundColor: message.type === 'error' ? '#fee' : message.type === 'success' ? '#efe' : '#eef',
                border: `1px solid ${message.type === 'error' ? '#f44' : message.type === 'success' ? '#4f4' : '#44f'}`,
                color: message.type === 'error' ? '#c00' : message.type === 'success' ? '#0c0' : '#00c',
                fontSize: '14px'
              }}>
                {message.text}
              </div>
            )}
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                Reversal Reason * (min 10 characters)
              </label>
              <textarea
                value={reverseForm.reversal_reason}
                onChange={(e) => setReverseForm({ ...reverseForm, reversal_reason: e.target.value })}
                placeholder="Enter reason for reversal..."
                rows={4}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>
                Committee Approval Reference (Optional)
              </label>
              <input
                type="text"
                value={reverseForm.committee_approval}
                onChange={(e) => setReverseForm({ ...reverseForm, committee_approval: e.target.value })}
                placeholder="Enter committee approval reference..."
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowReverseModal(false);
                  setSelectedBillForAction(null);
                  setReverseForm({ reversal_reason: '', committee_approval: '' });
                }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (reverseForm.reversal_reason.length < 10) {
                    setMessage({ type: 'error', text: 'Reversal reason must be at least 10 characters' });
                    return;
                  }
                  setLoading(true);
                  setMessage({ type: '', text: '' }); // Clear previous messages
                  try {
                    console.log('Reversing bill:', selectedBillForAction);
                    console.log('Bill object keys:', Object.keys(selectedBillForAction));
                    console.log('Bill ID:', selectedBillForAction.id, 'Type:', typeof selectedBillForAction.id);
                    console.log('Bill _id:', selectedBillForAction._id, 'Type:', typeof selectedBillForAction._id);
                    console.log('Bill flat_id:', selectedBillForAction.flat_id);
                    console.log('Bill flat_number:', selectedBillForAction.flat_number);

                    // Try both id and _id (backend model accepts both)
                    // Also check if it's nested or has different field names
                    const billId = selectedBillForAction.id ||
                      selectedBillForAction._id ||
                      selectedBillForAction.bill_id ||
                      (selectedBillForAction.bill && selectedBillForAction.bill.id);

                    if (!billId) {
                      const errorMsg = 'Bill ID is missing. Available fields: ' + Object.keys(selectedBillForAction).join(', ');
                      console.error(errorMsg);
                      console.error('Full bill object:', JSON.stringify(selectedBillForAction, null, 2));
                      setMessage({ type: 'error', text: errorMsg + '. Please check the console for details.' });
                      return;
                    }
                    console.log('Sending bill_id as:', billId, 'Type:', typeof billId);

                    const payload = {
                      bill_id: billId,
                      reversal_reason: reverseForm.reversal_reason,
                      committee_approval: reverseForm.committee_approval || null
                    };
                    console.log('Request payload:', payload);

                    const response = await api.post(`/maintenance/reverse-bill`, payload);
                    console.log('Bill reversal response:', response.data);
                    setMessage({ type: 'success', text: `Bill reversed successfully for ${selectedBillForAction.flat_number}. You can now regenerate it.` });

                    // Reload bills first to confirm reversal
                    await loadBillsForPeriod();

                    // Close modal and prepare for regeneration
                    const billForRegen = { ...selectedBillForAction }; // Keep a copy
                    setShowReverseModal(false);
                    setSelectedBillForAction(null);
                    setReverseForm({ reversal_reason: '', committee_approval: '' });

                    // Then show regenerate modal after a short delay
                    setTimeout(() => {
                      setSelectedBillForAction(billForRegen);
                      setShowRegenerateModal(true);
                    }, 500);
                  } catch (error) {
                    console.error('Error reversing bill:', error);
                    console.error('Error response:', error.response);
                    console.error('Error response data:', error.response?.data);
                    console.error('Error response status:', error.response?.status);
                    const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to reverse bill. Please check the console for details.';
                    setMessage({ type: 'error', text: errorMsg });
                    // Don't close modal on error so user can see the error and retry
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading || reverseForm.reversal_reason.length < 10}
                style={{
                  padding: '10px 20px',
                  backgroundColor: loading || reverseForm.reversal_reason.length < 10 ? '#ccc' : '#ff3b30',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading || reverseForm.reversal_reason.length < 10 ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Reversing...' : 'Reverse Bill'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Regenerate Bill Modal */}
      {showRegenerateModal && selectedBillForAction && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            maxWidth: '600px',
            width: '90%',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <h2 style={{ marginTop: 0 }}>Regenerate Bill - {selectedBillForAction.flat_number}</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>
              Enter corrected values for the bill components. Leave empty to use calculated values.
            </p>
            {/* Show message inside modal */}
            {message.text && message.type && (
              <div style={{
                padding: '10px',
                marginBottom: '15px',
                borderRadius: '4px',
                backgroundColor: message.type === 'error' ? '#fee' : message.type === 'success' ? '#efe' : '#eef',
                border: `1px solid ${message.type === 'error' ? '#f44' : message.type === 'success' ? '#4f4' : '#44f'}`,
                color: message.type === 'error' ? '#c00' : message.type === 'success' ? '#0c0' : '#00c',
                fontSize: '14px'
              }}>
                {message.text}
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Corrected Residents for Water</label>
                <input
                  type="number"
                  min="0"
                  value={regenerateForm.corrected_occupants}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, corrected_occupants: e.target.value })}
                  placeholder={`Current: ${selectedBillForAction.breakdown?.inmates_used || '-'}`}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Maintenance ()</label>
                <input
                  type="number"
                  step="0.01"
                  value={regenerateForm.override_maintenance}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, override_maintenance: e.target.value })}
                  placeholder="Auto-calculated"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Water Charges ()</label>
                <input
                  type="number"
                  step="0.01"
                  value={regenerateForm.override_water}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, override_water: e.target.value })}
                  placeholder="Auto-calculated"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Fixed Expenses ()</label>
                <input
                  type="number"
                  step="0.01"
                  value={regenerateForm.override_fixed}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, override_fixed: e.target.value })}
                  placeholder="Auto-calculated"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Sinking Fund ()</label>
                <input
                  type="number"
                  step="0.01"
                  value={regenerateForm.override_sinking}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, override_sinking: e.target.value })}
                  placeholder="Auto-calculated"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Repair Fund ()</label>
                <input
                  type="number"
                  step="0.01"
                  value={regenerateForm.override_repair}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, override_repair: e.target.value })}
                  placeholder="Auto-calculated"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Corpus Fund ()</label>
                <input
                  type="number"
                  step="0.01"
                  value={regenerateForm.override_corpus}
                  onChange={(e) => setRegenerateForm({ ...regenerateForm, override_corpus: e.target.value })}
                  placeholder="Auto-calculated"
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '600' }}>Notes (Optional)</label>
              <textarea
                value={regenerateForm.notes}
                onChange={(e) => setRegenerateForm({ ...regenerateForm, notes: e.target.value })}
                placeholder="Additional notes for the regenerated bill..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowRegenerateModal(false);
                  setSelectedBillForAction(null);
                  setRegenerateForm({
                    corrected_occupants: '',
                    override_maintenance: '',
                    override_water: '',
                    override_fixed: '',
                    override_sinking: '',
                    override_repair: '',
                    override_corpus: '',
                    notes: ''
                  });
                }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setLoading(true);
                  try {
                    const month = parseInt(billForm.month) + 1;
                    const year = parseInt(billForm.year);
                    await api.post(`/maintenance/regenerate-bill`, {
                      flat_id: selectedBillForAction.flat_id,
                      month: month,
                      year: year,
                      corrected_occupants: regenerateForm.corrected_occupants ? parseInt(regenerateForm.corrected_occupants, 10) : null,
                      override_maintenance: regenerateForm.override_maintenance ? parseFloat(regenerateForm.override_maintenance) : null,
                      override_water: regenerateForm.override_water ? parseFloat(regenerateForm.override_water) : null,
                      override_fixed: regenerateForm.override_fixed ? parseFloat(regenerateForm.override_fixed) : null,
                      override_sinking: regenerateForm.override_sinking ? parseFloat(regenerateForm.override_sinking) : null,
                      override_repair: regenerateForm.override_repair ? parseFloat(regenerateForm.override_repair) : null,
                      override_corpus: regenerateForm.override_corpus ? parseFloat(regenerateForm.override_corpus) : null,
                      notes: regenerateForm.notes || null
                    });
                    setMessage({ type: 'success', text: 'Bill regenerated successfully!' });
                    setShowRegenerateModal(false);
                    setSelectedBillForAction(null);
                    setRegenerateForm({
                      corrected_occupants: '',
                      override_maintenance: '',
                      override_water: '',
                      override_fixed: '',
                      override_sinking: '',
                      override_repair: '',
                      override_corpus: '',
                      notes: ''
                    });
                    loadBillsForPeriod();
                  } catch (error) {
                    setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to regenerate bill' });
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  backgroundColor: loading ? '#ccc' : '#007AFF',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer'
                }}
              >
                {loading ? 'Regenerating...' : 'Regenerate Bill'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MaintenanceScreen;


