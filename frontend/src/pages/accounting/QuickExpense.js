import React, { useMemo, useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Snackbar,
  Chip,
  Stack,
  Autocomplete,
} from '@mui/material';
import Layout from '../../components/Layout';
import MoneyOffIcon from '@mui/icons-material/MoneyOff';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import { useCurrentUser } from '../../contexts/CurrentUserContext';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { getAccessToken } from '../../utils/authStorage';

// Common expense types with their account mappings
const EXPENSE_TYPES = [
  { label: 'Priest Salary', account_code: '52003', category: 'Operational' },
  { label: 'Staff Salary', account_code: '52001', category: 'Operational' },
  { label: 'Electricity Bill', account_code: '53002', category: 'Operational' },
  { label: 'Water Bill', account_code: '53007', category: 'Operational' },
  { label: 'Maintenance & Repairs', account_code: '53004', category: 'Operational' },
  { label: 'Flower Decoration', account_code: '54006', category: 'Pooja & Ritual' },
  { label: 'Pooja Materials', account_code: '51004', category: 'Pooja & Ritual' },
  { label: 'Prasadam Expense', account_code: '54007', category: 'Pooja & Ritual' },
  { label: 'Vegetables & Groceries', account_code: '51001', category: 'Annadana' },
  { label: 'Cooking Gas', account_code: '54012', category: 'Annadana' },
  { label: 'Tent Hiring', account_code: '54005', category: 'Festival' },
  { label: 'Sound System', account_code: '54005', category: 'Festival' },
  { label: 'Lighting Expense', account_code: '54004', category: 'Festival' },
  { label: 'Audit Fees', account_code: '54010', category: 'Administrative' },
  { label: 'Bank Charges', account_code: '54001', category: 'Administrative' },
  { label: 'Printing & Stationery', account_code: '53006', category: 'Administrative' },
];

const PAYMENT_MODES = ['Cash', 'Bank'];
const LEGACY_EXPENSE_CODE_MAP = {
  '5101': '52003',
  '5102': '52001',
  '5110': '53002',
  '5111': '53007',
  '5120': '53004',
  '5201': '54006',
  '5202': '51004',
  '5203': '54007',
  '5301': '51001',
  '5302': '54012',
  '5401': '54005',
  '5402': '54005',
  '5403': '54004',
  '5501': '54010',
  '5502': '54001',
  '5503': '53006',
};

function QuickExpense() {
  const { user, loading: currentUserLoading } = useCurrentUser();
  const canReverseEntries = !currentUserLoading && (
    Boolean(user?.action_permissions?.reverse_accounting_entries)
    || ['admin', 'super_admin'].includes(user?.role)
    || Boolean(user?.is_superuser)
  );
  const [accounts, setAccounts] = useState([]);
  const [paymentAccounts, setPaymentAccounts] = useState({ cash_accounts: [], bank_accounts: [] });
  const [todayExpenses, setTodayExpenses] = useState([]);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Form state
  const [expenseType, setExpenseType] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentMode, setPaymentMode] = useState('');
  const [paymentAccountId, setPaymentAccountId] = useState('');
  const [description, setDescription] = useState('');
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().split('T')[0]);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [editingExpenseId, setEditingExpenseId] = useState(null);
  const [postingEntryId, setPostingEntryId] = useState(null);
  const [reversingEntryId, setReversingEntryId] = useState(null);

  const expenseAccountOptions = useMemo(() => {
    const accountOptions = accounts
      .filter((acc) => {
        const type = String(acc.account_type || acc.type || '').toLowerCase();
        const code = String(acc.account_code || acc.code || '').trim();
        return type === 'expense' && code;
      })
      .map((acc) => ({
        id: acc.id,
        account_code: String(acc.account_code || acc.code || '').trim(),
        account_name: String(acc.account_name || acc.name || '').trim(),
        label: String(acc.account_name || acc.name || '').trim(),
        category: String(acc.account_subtype || acc.subtype || acc.category || 'Expense').trim(),
      }));

    const presetOptions = EXPENSE_TYPES.map((exp) => ({
      ...exp,
      account_name: exp.label,
      id: null,
    }));

    const byCode = new Map();
    [...accountOptions, ...presetOptions].forEach((option) => {
      const code = String(option.account_code || '').trim();
      if (!code || byCode.has(code)) return;
      byCode.set(code, option);
    });

    return Array.from(byCode.values()).sort((a, b) => (
      String(a.account_code).localeCompare(String(b.account_code))
    ));
  }, [accounts]);

  const selectedExpenseAccount = expenseAccountOptions.find((option) => (
    String(option.account_code) === String(expenseType)
  )) || null;

  useEffect(() => {
    fetchAccounts();
    fetchPaymentAccounts();
    fetchTodayExpenses();
  }, []);

  const fetchAccounts = async () => {
    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback('/api/v1/accounts/', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      // Flatten the hierarchical accounts
      const flattenAccounts = (accs, result = []) => {
        accs.forEach(acc => {
          result.push(acc);
          if (acc.sub_accounts && acc.sub_accounts.length > 0) {
            flattenAccounts(acc.sub_accounts, result);
          }
        });
        return result;
      };
      setAccounts(flattenAccounts(data));
    } catch (error) {
      console.error('Error fetching accounts:', error);
    }
  };

  const fetchTodayExpenses = async () => {
    try {
      const token = getAccessToken();
      const today = new Date().toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/journal-entries/?from_date=${today}&to_date=${today}&reference_type=expense`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );
      const data = await response.json();
      const rows = Array.isArray(data) ? data : [];
      const expenseRows = rows.filter((row) => String(row?.reference_type || '').toLowerCase() === 'expense');
      setTodayExpenses(expenseRows);
    } catch (error) {
      console.error('Error fetching today expenses:', error);
      setTodayExpenses([]);
    }
  };

  const fetchPaymentAccounts = async () => {
    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback('/api/v1/donations/payment-accounts', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      setPaymentAccounts({
        cash_accounts: Array.isArray(data.cash_accounts) ? data.cash_accounts : [],
        bank_accounts: Array.isArray(data.bank_accounts) ? data.bank_accounts : [],
      });
    } catch (error) {
      console.error('Error fetching payment accounts:', error);
      setPaymentAccounts({ cash_accounts: [], bank_accounts: [] });
    }
  };

  const getAccountIdByCode = (code, options = {}) => {
    const { allowLegacyExpenseFormat = false } = options;
    const normalizedCode = String(code || '').trim();

    // 1) Exact code match
    const exact = accounts.find((acc) => String(acc.account_code) === normalizedCode);
    if (exact) {
      return exact.id;
    }

    if (!allowLegacyExpenseFormat) {
      return null;
    }

    // 2) Explicit legacy expense code mapping (old 4-digit -> current 5-digit COA)
    const mappedLegacyCode = LEGACY_EXPENSE_CODE_MAP[normalizedCode];
    if (mappedLegacyCode) {
      const mapped = accounts.find((acc) => String(acc.account_code) === mappedLegacyCode);
      if (mapped) {
        return mapped.id;
      }
    }

    // 3) Generic legacy 4-digit expense code -> modern 5-digit code (e.g., 5102 -> 51002)
    if (/^\d{4}$/.test(normalizedCode)) {
      const migratedCode = `${normalizedCode.slice(0, 3)}0${normalizedCode.slice(3)}`;
      const migrated = accounts.find((acc) => String(acc.account_code) === migratedCode);
      if (migrated) {
        return migrated.id;
      }
    }

    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!expenseType || !amount || !paymentMode || !paymentAccountId || !description) {
      setSnackbar({ open: true, message: 'Please fill all required fields', severity: 'error' });
      return;
    }

    const selectedExpense = selectedExpenseAccount || EXPENSE_TYPES.find((exp) => exp.account_code === expenseType);
    const selectablePaymentAccounts = paymentMode === 'Cash'
      ? paymentAccounts.cash_accounts
      : paymentAccounts.bank_accounts;
    const selectedPayment = selectablePaymentAccounts.find(
      (acc) => String(acc.account_id) === String(paymentAccountId)
    );

    const expenseAccountId = selectedExpense?.id || getAccountIdByCode(expenseType, { allowLegacyExpenseFormat: true }) || String(expenseType);
    const selectedPaymentAccountId = selectedPayment ? selectedPayment.account_id : null;

    if (!expenseAccountId || !selectedPaymentAccountId || !selectedExpense) {
      setSnackbar({ open: true, message: 'Invalid account mapping', severity: 'error' });
      return;
    }

    try {
      const token = getAccessToken();
      const entryDateTime = String(expenseDate).includes('T') ? expenseDate : `${expenseDate}T00:00:00`;
      const payload = {
        entry_date: entryDateTime,
        narration: `${selectedExpense.label || selectedExpense.account_name} - ${description}`,
        reference_type: 'expense',
        reference_id: referenceNumber ? Number(referenceNumber) : undefined,
        journal_lines: [
          {
            account_id: expenseAccountId,
            debit_amount: parseFloat(amount),
            credit_amount: 0,
            description,
          },
          {
            account_id: selectedPaymentAccountId,
            debit_amount: 0,
            credit_amount: parseFloat(amount),
            description: `Paid via ${paymentMode} - ${selectedPayment.account_code} ${selectedPayment.account_name}`,
          },
        ],
      };

      const requestMethod = editingExpenseId ? 'PUT' : 'POST';
      const requestUrl = editingExpenseId
        ? `/api/v1/journal-entries/${editingExpenseId}`
        : '/api/v1/journal-entries/';

      const response = await fetchWithApiFallback(requestUrl, {
        method: requestMethod,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        const formattedAmount = Number(amount).toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
        let finalMessage = editingExpenseId
          ? `Expense updated successfully. Entry #${data.entry_number} | Rs ${formattedAmount} via ${paymentMode}.`
          : `Expense recorded successfully. Entry #${data.entry_number} | Rs ${formattedAmount} via ${paymentMode}.`;
        let finalSeverity = 'success';

        if (!editingExpenseId && data?.id) {
          const postResponse = await fetchWithApiFallback(
            `/api/v1/journal-entries/${data.id}/post`,
            {
              method: 'POST',
              headers: { 'Authorization': `Bearer ${token}` },
            }
          );

          if (postResponse.ok) {
            finalMessage = `Expense posted to accounts. Entry #${data.entry_number} | Rs ${formattedAmount} via ${paymentMode}.`;
          } else {
            let postErrorMessage = 'Unknown posting error';
            try {
              const postError = await postResponse.json();
              postErrorMessage = Array.isArray(postError.detail)
                ? postError.detail.map((d) => `${d.field}: ${d.message}`).join(' | ')
                : (postError.detail || postErrorMessage);
            } catch {
              // keep fallback
            }
            finalMessage = `Expense saved as draft (Entry #${data.entry_number}). Posting failed: ${postErrorMessage}`;
            finalSeverity = 'warning';
          }
        }

        setSnackbar({
          open: true,
          message: finalMessage,
          severity: finalSeverity,
        });

        setExpenseType('');
        setAmount('');
        setPaymentMode('');
        setPaymentAccountId('');
        setDescription('');
        setReferenceNumber('');
        setEditingExpenseId(null);
        setExpenseDate(new Date().toISOString().split('T')[0]);
        fetchTodayExpenses();
      } else {
        const error = await response.json();
        const detailMessage = Array.isArray(error.detail)
          ? error.detail.map((d) => `${d.field}: ${d.message}`).join(' | ')
          : (error.detail || 'Failed to save expense');
        setSnackbar({ open: true, message: detailMessage, severity: 'error' });
      }
    } catch (error) {
      console.error('Error saving expense:', error);
      setSnackbar({ open: true, message: 'Error saving expense', severity: 'error' });
    }
  };

  const handlePostDraft = async (entryId, entryNumber) => {
    try {
      setPostingEntryId(entryId);
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/journal-entries/${entryId}/post`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        setSnackbar({
          open: true,
          message: `Entry #${entryNumber} posted to accounts successfully.`,
          severity: 'success',
        });
        fetchTodayExpenses();
      } else {
        const error = await response.json();
        const detailMessage = Array.isArray(error.detail)
          ? error.detail.map((d) => `${d.field}: ${d.message}`).join(' | ')
          : (error.detail || 'Failed to post entry');
        setSnackbar({
          open: true,
          message: `Entry #${entryNumber} is still draft. ${detailMessage}`,
          severity: 'warning',
        });
      }
    } catch (error) {
      console.error('Error posting draft entry:', error);
      setSnackbar({ open: true, message: 'Error posting draft entry', severity: 'error' });
    } finally {
      setPostingEntryId(null);
    }
  };

  const handleEditExpense = (expense) => {
    if (String(expense.status).toLowerCase() !== 'draft') {
      setSnackbar({
        open: true,
        message: 'Only draft entries can be edited. Use reversal for posted entries.',
        severity: 'warning',
      });
      return;
    }

    const debitLine = (expense.journal_lines || []).find((line) => Number(line.debit_amount) > 0);
    const creditLine = (expense.journal_lines || []).find((line) => Number(line.credit_amount) > 0);

    if (!debitLine || !creditLine) {
      setSnackbar({ open: true, message: 'Unable to load entry lines for editing.', severity: 'error' });
      return;
    }

    const expenseAccountCode = String(
      debitLine.account_code || accounts.find((acc) => acc.id === debitLine.account_id)?.account_code || ''
    );

    const matchedExpenseType = expenseAccountOptions.find((exp) => exp.account_code === expenseAccountCode)
      || EXPENSE_TYPES.find((exp) => exp.account_code === expenseAccountCode);
    if (!matchedExpenseType) {
      setSnackbar({
        open: true,
        message: `Entry uses account code ${expenseAccountCode}, which is not available in expense accounts.`,
        severity: 'warning',
      });
      return;
    }

    const creditAccountId = String(creditLine.account_id || '');
    const isCash = paymentAccounts.cash_accounts.some((acc) => String(acc.account_id) === creditAccountId);
    const isBank = paymentAccounts.bank_accounts.some((acc) => String(acc.account_id) === creditAccountId);
    if (!isCash && !isBank) {
      setSnackbar({
        open: true,
        message: 'Cannot determine payment account type for this entry.',
        severity: 'warning',
      });
      return;
    }

    setEditingExpenseId(expense.id);
    setExpenseType(matchedExpenseType.account_code);
    setAmount(String(expense.total_amount || ''));
    setPaymentMode(isCash ? 'Cash' : 'Bank');
    setPaymentAccountId(creditAccountId);
    setDescription(debitLine.description || expense.narration || '');
    setExpenseDate(String(expense.entry_date || '').split('T')[0] || new Date().toISOString().split('T')[0]);
    setReferenceNumber(String(expense.reference_id || ''));
    setSnackbar({
      open: true,
      message: `Editing ${expense.entry_number}. Update and save to keep audit trail intact.`,
      severity: 'info',
    });
  };

  const handleCancelEdit = () => {
    setEditingExpenseId(null);
    setExpenseType('');
    setAmount('');
    setPaymentMode('');
    setPaymentAccountId('');
    setDescription('');
    setReferenceNumber('');
    setExpenseDate(new Date().toISOString().split('T')[0]);
  };

  const handleReverseExpense = async (expense) => {
    const reason = window.prompt(
      `Enter reversal reason for ${expense.entry_number}:`,
      'Correction entry'
    );
    if (!reason || !reason.trim()) {
      return;
    }

    try {
      setReversingEntryId(expense.id);
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/journal-entries/${expense.id}/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ cancellation_reason: reason.trim() }),
      });

      if (response.ok) {
        setSnackbar({
          open: true,
          message: `Entry ${expense.entry_number} reversed. Reversal voucher created automatically.`,
          severity: 'success',
        });
        fetchTodayExpenses();
      } else {
        const error = await response.json();
        const detailMessage = Array.isArray(error.detail)
          ? error.detail.map((d) => `${d.field}: ${d.message}`).join(' | ')
          : (error.detail || 'Failed to reverse entry');
        setSnackbar({ open: true, message: detailMessage, severity: 'error' });
      }
    } catch (error) {
      console.error('Error reversing entry:', error);
      setSnackbar({ open: true, message: 'Error reversing entry', severity: 'error' });
    } finally {
      setReversingEntryId(null);
    }
  };

  const totalExpensesToday = (Array.isArray(todayExpenses) ? todayExpenses : []).reduce(
    (sum, exp) => sum + (Number(exp.total_amount) || 0),
    0
  );

  return (
    <Layout>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <MoneyOffIcon sx={{ fontSize: 40, mr: 2, color: '#d32f2f' }} />
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            Quick Expense Entry
          </Typography>
        </Box>

        {/* Summary Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <Card sx={{ bgcolor: '#ffebee' }}>
              <CardContent>
                <Typography variant="h6" color="text.secondary">Total Expenses Today</Typography>
                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#d32f2f' }}>
                  ₹{totalExpensesToday.toFixed(2)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card sx={{ bgcolor: '#e3f2fd' }}>
              <CardContent>
                <Typography variant="h6" color="text.secondary">Transactions Today</Typography>
                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                  {todayExpenses.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          {/* Quick Entry Form */}
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <ReceiptLongIcon sx={{ mr: 1, color: '#d32f2f' }} />
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {editingExpenseId ? 'Edit Expense Entry' : 'Record Expense'}
                </Typography>
              </Box>

              <form onSubmit={handleSubmit}>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Autocomplete
                      value={selectedExpenseAccount}
                      options={expenseAccountOptions}
                      onChange={(_event, option) => setExpenseType(option?.account_code || '')}
                      getOptionLabel={(option) => (
                        option
                          ? `${option.account_code} - ${option.label || option.account_name} (${option.category || 'Expense'})`
                          : ''
                      )}
                      isOptionEqualToValue={(option, value) => (
                        String(option.account_code) === String(value.account_code)
                      )}
                      filterOptions={(options, state) => {
                        const query = String(state.inputValue || '').trim().toLowerCase();
                        if (!query) return options.slice(0, 25);
                        return options.filter((option) => (
                          String(option.account_code || '').toLowerCase().includes(query)
                          || String(option.label || option.account_name || '').toLowerCase().includes(query)
                          || String(option.category || '').toLowerCase().includes(query)
                        )).slice(0, 25);
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Expense Account"
                          required
                          placeholder="Type code/name, e.g. 530 or electricity"
                          helperText="Type 3-4 characters to search expense account code or name"
                        />
                      )}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <TextField
                      label="Amount"
                      type="number"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      fullWidth
                      required
                      inputProps={{ step: '0.01', min: '0' }}
                      InputProps={{
                        startAdornment: <Typography sx={{ mr: 1 }}>₹</Typography>,
                      }}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <FormControl fullWidth required>
                      <InputLabel>Payment Method</InputLabel>
                      <Select
                        value={paymentMode}
                        onChange={(e) => {
                          setPaymentMode(e.target.value);
                          setPaymentAccountId('');
                        }}
                        label="Payment Method"
                      >
                        {PAYMENT_MODES.map((mode) => (
                          <MenuItem key={mode} value={mode}>
                            {mode}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  {paymentMode === 'Cash' && (
                    <Grid item xs={12}>
                      <FormControl fullWidth required>
                        <InputLabel>Cash Account Code</InputLabel>
                        <Select
                          value={paymentAccountId}
                          onChange={(e) => setPaymentAccountId(e.target.value)}
                          label="Cash Account Code"
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
                    </Grid>
                  )}

                  {paymentMode === 'Bank' && (
                    <Grid item xs={12}>
                      <FormControl fullWidth required>
                        <InputLabel>Bank Account Code</InputLabel>
                        <Select
                          value={paymentAccountId}
                          onChange={(e) => setPaymentAccountId(e.target.value)}
                          label="Bank Account Code"
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
                    </Grid>
                  )}

                  <Grid item xs={12}>
                    <TextField
                      label="Description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      fullWidth
                      required
                      multiline
                      rows={2}
                      placeholder="E.g., Monthly electricity bill for January"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <TextField
                      label="Expense Date"
                      type="date"
                      value={expenseDate}
                      onChange={(e) => setExpenseDate(e.target.value)}
                      fullWidth
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <TextField
                      label="Reference Number (Optional)"
                      value={referenceNumber}
                      onChange={(e) => setReferenceNumber(e.target.value)}
                      fullWidth
                      placeholder="E.g., Bill No: EB/2025/001"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      type="submit"
                      variant="contained"
                      fullWidth
                      size="large"
                      sx={{ bgcolor: '#d32f2f', '&:hover': { bgcolor: '#b71c1c' } }}
                    >
                      {editingExpenseId ? 'Update Expense' : 'Record Expense'}
                    </Button>
                  </Grid>

                  {editingExpenseId && (
                    <Grid item xs={12}>
                      <Button type="button" variant="outlined" fullWidth size="large" onClick={handleCancelEdit}>
                        Cancel Edit
                      </Button>
                    </Grid>
                  )}
                </Grid>
              </form>
            </Paper>
          </Grid>

          {/* Today's Expenses */}
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                Today's Expenses
              </Typography>

              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: '#d32f2f' }}>
                      <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Entry #</TableCell>
                      <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Narration</TableCell>
                      <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">Amount</TableCell>
                      <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Status</TableCell>
                      <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="center">Action</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {todayExpenses.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography color="text.secondary">No expenses recorded today</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      todayExpenses.map((expense) => (
                        <TableRow key={expense.id} hover>
                          <TableCell>{expense.entry_number}</TableCell>
                          <TableCell>{expense.narration}</TableCell>
                          <TableCell align="right">₹{expense.total_amount.toFixed(2)}</TableCell>
                          <TableCell>
                            <Chip
                              label={expense.status}
                              color={String(expense.status).toLowerCase() === 'posted' ? 'success' : 'warning'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell align="center">
                            {String(expense.status).toLowerCase() === 'draft' ? (
                              <Stack direction="row" spacing={1} justifyContent="center">
                                <Button
                                  size="small"
                                  variant="outlined"
                                  onClick={() => handleEditExpense(expense)}
                                >
                                  Edit
                                </Button>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="warning"
                                  disabled={postingEntryId === expense.id}
                                  onClick={() => handlePostDraft(expense.id, expense.entry_number)}
                                >
                                  {postingEntryId === expense.id ? 'Posting...' : 'Post'}
                                </Button>
                              </Stack>
                            ) : String(expense.status).toLowerCase() === 'posted' && canReverseEntries ? (
                              <Button
                                size="small"
                                variant="outlined"
                                color="error"
                                disabled={reversingEntryId === expense.id}
                                onClick={() => handleReverseExpense(expense)}
                              >
                                {reversingEntryId === expense.id ? 'Reversing...' : 'Reverse'}
                              </Button>
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </Layout>
  );
}

export default QuickExpense;

