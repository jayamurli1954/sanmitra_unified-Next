import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  TextField,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import Layout from '../../components/Layout';
import SummarizeIcon from '@mui/icons-material/Summarize';
import BalanceSheetReport from './BalanceSheetReport';
import DayBookReport from './DayBookReport';
import CashBookReport from './CashBookReport';
import BankBookReport from './BankBookReport';
import ExportButton from '../../components/ExportButton';
import PrintButton from '../../components/PrintButton';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { getAccessToken } from '../../utils/authStorage';
import { exportToCSV, exportToExcel, exportToPDF } from '../../utils/export';

const ALL_GT_ZERO_OPTION = '__ALL_GT_ZERO__';

function TabPanel({ children, value, index }) {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

function AccountingReports() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [trialBalance, setTrialBalance] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [bulkLedgers, setBulkLedgers] = useState([]);
  const [ledgerErrors, setLedgerErrors] = useState([]);
  const [profitLoss, setProfitLoss] = useState(null);
  const [categoryIncome, setCategoryIncome] = useState(null);
  const [topDonors, setTopDonors] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [reportError, setReportError] = useState('');
  const [voucherDetail, setVoucherDetail] = useState(null);
  const [voucherDialogOpen, setVoucherDialogOpen] = useState(false);
  const [voucherLoadingId, setVoucherLoadingId] = useState(null);
  const [voucherError, setVoucherError] = useState('');
  const [fromDate, setFromDate] = useState(new Date(new Date().getFullYear(), 3, 1)); // April 1st
  const [toDate, setToDate] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const getLedgerEntries = (ledgerData) => {
    if (!ledgerData) return [];
    if (Array.isArray(ledgerData.entries)) return ledgerData.entries;
    if (Array.isArray(ledgerData.transactions)) return ledgerData.transactions; // backward compatibility
    return [];
  };

  const safeArray = (value) => (Array.isArray(value) ? value : []);
  const safeNumber = (value) => Number(value || 0);
  const safeAmount = (value) => safeNumber(value).toFixed(2);
  const ledgerEntryDate = (txn) => (
    txn?.entry_date || txn?.date || txn?.posting_date || txn?.transaction_date || ''
  );
  const ledgerEntryNumber = (txn) => (
    txn?.entry_number || txn?.voucher_no || txn?.reference || (txn?.journal_id ? `JE-${txn.journal_id}` : '')
  );
  const ledgerEntryDescription = (txn) => (
    txn?.narration || txn?.description || txn?.memo || txn?.reference || ''
  );
  const ledgerJournalId = (txn) => {
    const directId = txn?.journal_id ?? txn?.journalId ?? txn?.id;
    if (directId !== null && directId !== undefined && String(directId).trim() !== '') {
      return String(directId).trim();
    }
    const entryNumber = String(ledgerEntryNumber(txn) || '').trim();
    const match = entryNumber.match(/(?:JE|REV)-(\d+)/i);
    return match ? match[1] : '';
  };
  const formatDisplayDate = (value) => {
    if (!value) return '-';
    if (value instanceof Date && !Number.isNaN(value.getTime())) {
      return value.toLocaleDateString('en-GB');
    }

    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleDateString('en-GB');
    }

    if (typeof value === 'string') {
      const isoMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (isoMatch) {
        return `${isoMatch[3]}/${isoMatch[2]}/${isoMatch[1]}`;
      }
      return value;
    }
    return '-';
  };

  const buildLedgerExportRows = () => {
    const rows = [];
    if (selectedAccount === ALL_GT_ZERO_OPTION && bulkLedgers.length > 0) {
      bulkLedgers.forEach((accountLedger) => {
        rows.push({
          'Account Code': accountLedger.account_code || '',
          'Account Name': accountLedger.account_name || '',
          'Date': '',
          'Entry #': '',
          'Description': 'Opening Balance',
          'Debit': '',
          'Credit': '',
          'Balance': safeAmount(accountLedger.opening_balance),
        });
        getLedgerEntries(accountLedger).forEach((txn) => {
          rows.push({
            'Account Code': accountLedger.account_code || '',
            'Account Name': accountLedger.account_name || '',
            'Date': formatDisplayDate(ledgerEntryDate(txn)),
            'Entry #': ledgerEntryNumber(txn),
            'Description': ledgerEntryDescription(txn),
            'Debit': safeNumber(txn.debit_amount) > 0 ? safeAmount(txn.debit_amount) : '',
            'Credit': safeNumber(txn.credit_amount) > 0 ? safeAmount(txn.credit_amount) : '',
            'Balance': safeAmount(txn.running_balance),
          });
        });
        rows.push({
          'Account Code': accountLedger.account_code || '',
          'Account Name': accountLedger.account_name || '',
          'Date': '',
          'Entry #': '',
          'Description': 'Closing Balance',
          'Debit': '',
          'Credit': '',
          'Balance': safeAmount(accountLedger.closing_balance),
        });
      });
      return rows;
    }

    if (ledger && selectedAccount !== ALL_GT_ZERO_OPTION) {
      rows.push({
        'Account Code': ledger.account_code || '',
        'Account Name': ledger.account_name || '',
        'Date': '',
        'Entry #': '',
        'Description': 'Opening Balance',
        'Debit': '',
        'Credit': '',
        'Balance': safeAmount(ledger.opening_balance),
      });
      getLedgerEntries(ledger).forEach((txn) => {
        rows.push({
          'Account Code': ledger.account_code || '',
          'Account Name': ledger.account_name || '',
          'Date': formatDisplayDate(ledgerEntryDate(txn)),
          'Entry #': ledgerEntryNumber(txn),
          'Description': ledgerEntryDescription(txn),
          'Debit': safeNumber(txn.debit_amount) > 0 ? safeAmount(txn.debit_amount) : '',
          'Credit': safeNumber(txn.credit_amount) > 0 ? safeAmount(txn.credit_amount) : '',
          'Balance': safeAmount(txn.running_balance),
        });
      });
      rows.push({
        'Account Code': ledger.account_code || '',
        'Account Name': ledger.account_name || '',
        'Date': '',
        'Entry #': '',
        'Description': 'Closing Balance',
        'Debit': '',
        'Credit': '',
        'Balance': safeAmount(ledger.closing_balance),
      });
    }
    return rows;
  };

  const handleLedgerExport = (format) => {
    const exportRows = buildLedgerExportRows();
    if (!exportRows.length) {
      alert('No ledger data to export');
      return;
    }

    const dateStamp = new Date().toISOString().slice(0, 10);
    const filenamePrefix = selectedAccount === ALL_GT_ZERO_OPTION ? 'account_ledger_all' : 'account_ledger';
    const filename = `${filenamePrefix}_${dateStamp}`;

    if (format === 'excel') {
      exportToExcel(exportRows, `${filename}.xlsx`);
      return;
    }
    if (format === 'pdf') {
      exportToPDF(exportRows, 'Account Ledger', {
        period: {
          from: formatDisplayDate(fromDate),
          to: formatDisplayDate(toDate),
        },
      });
      return;
    }
    exportToCSV(exportRows, `${filename}.csv`);
  };

  const exportRowsByFormat = (rows, format, filename, title, period = null) => {
    if (!rows.length) {
      alert('No data to export');
      return;
    }
    if (format === 'excel') {
      exportToExcel(rows, `${filename}.xlsx`);
      return;
    }
    if (format === 'pdf') {
      exportToPDF(rows, title, { period });
      return;
    }
    exportToCSV(rows, `${filename}.csv`);
  };

  const handleTrialBalanceExport = (format) => {
    const rows = safeArray(trialBalance?.lines || trialBalance?.accounts).map((account) => ({
      'Account Code': account.account_code ?? account.code ?? account.account_id ?? '',
      'Account Name': account.account_name ?? account.name ?? '',
      'Debit': safeNumber(account.debit_total ?? account.debit_balance) > 0 ? safeAmount(account.debit_total ?? account.debit_balance) : '',
      'Credit': safeNumber(account.credit_total ?? account.credit_balance) > 0 ? safeAmount(account.credit_total ?? account.credit_balance) : '',
    }));
    rows.push({
      'Account Code': '',
      'Account Name': 'TOTAL',
      'Debit': safeAmount(trialBalance?.total_debit ?? trialBalance?.total_debits),
      'Credit': safeAmount(trialBalance?.total_credit ?? trialBalance?.total_credits),
    });
    exportRowsByFormat(
      rows,
      format,
      `trial_balance_${toDate.toISOString().slice(0, 10)}`,
      'Trial Balance',
      { to: formatDisplayDate(toDate) }
    );
  };

  const handleProfitLossExport = (format) => {
    const rows = [];
    safeArray(profitLoss?.income_groups).forEach((group) => {
      rows.push({ Section: 'Income', Category: group.category_name, Account: '', Code: '', Amount: '' });
      safeArray(group.accounts).forEach((acc) => {
        rows.push({
          Section: 'Income',
          Category: group.category_name,
          Account: acc.account_name || '',
          Code: acc.account_code || '',
          Amount: safeAmount(acc.amount),
        });
      });
      rows.push({ Section: 'Income', Category: `${group.category_name} Total`, Account: '', Code: '', Amount: safeAmount(group.total) });
    });
    safeArray(profitLoss?.expense_groups).forEach((group) => {
      rows.push({ Section: 'Expense', Category: group.category_name, Account: '', Code: '', Amount: '' });
      safeArray(group.accounts).forEach((acc) => {
        rows.push({
          Section: 'Expense',
          Category: group.category_name,
          Account: acc.account_name || '',
          Code: acc.account_code || '',
          Amount: safeAmount(acc.amount),
        });
      });
      rows.push({ Section: 'Expense', Category: `${group.category_name} Total`, Account: '', Code: '', Amount: safeAmount(group.total) });
    });
    rows.push({ Section: 'Summary', Category: 'Total Income', Account: '', Code: '', Amount: safeAmount(profitLoss?.total_income) });
    rows.push({ Section: 'Summary', Category: 'Total Expenses', Account: '', Code: '', Amount: safeAmount(profitLoss?.total_expenses) });
    rows.push({ Section: 'Summary', Category: 'Net Surplus/Deficit', Account: '', Code: '', Amount: safeAmount(profitLoss?.net_surplus) });
    exportRowsByFormat(
      rows,
      format,
      `income_expenditure_${new Date().toISOString().slice(0, 10)}`,
      'Income and Expenditure',
      { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) }
    );
  };

  const handleCategoryIncomeExport = (format) => {
    const rows = [];
    safeArray(categoryIncome?.donation_income).forEach((item) => {
      rows.push({
        Type: 'Donation',
        Code: item.account_code || '',
        Name: item.account_name || '',
        Amount: safeAmount(item.amount),
        Percentage: item.percentage ?? '',
        Transactions: item.transaction_count ?? '',
      });
    });
    safeArray(categoryIncome?.seva_income).forEach((item) => {
      rows.push({
        Type: 'Seva',
        Code: item.account_code || '',
        Name: item.account_name || '',
        Amount: safeAmount(item.amount),
        Percentage: item.percentage ?? '',
        Transactions: item.transaction_count ?? '',
      });
    });
    safeArray(categoryIncome?.other_income).forEach((item) => {
      rows.push({
        Type: 'Other',
        Code: item.account_code || '',
        Name: item.account_name || '',
        Amount: safeAmount(item.amount),
        Percentage: item.percentage ?? '',
        Transactions: item.transaction_count ?? '',
      });
    });
    rows.push({
      Type: 'Summary',
      Code: '',
      Name: 'Total Income',
      Amount: safeAmount(categoryIncome?.total_income),
      Percentage: '',
      Transactions: '',
    });
    exportRowsByFormat(
      rows,
      format,
      `category_income_${new Date().toISOString().slice(0, 10)}`,
      'Category Income',
      { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) }
    );
  };

  const handleTopDonorsExport = (format) => {
    const rows = safeArray(topDonors?.donors).map((donor, index) => ({
      Rank: index + 1,
      'Devotee Name': donor.devotee_name || '',
      'Total Donated': safeAmount(donor.total_donated),
      'Donation Count': donor.donation_count ?? 0,
      'Last Donation Date': formatDisplayDate(donor.last_donation_date),
      Categories: safeArray(donor.categories).join(', '),
    }));
    exportRowsByFormat(
      rows,
      format,
      `top_donors_${new Date().toISOString().slice(0, 10)}`,
      'Top Donors',
      { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) }
    );
  };

  React.useEffect(() => {
    fetchAccounts();
  }, []);

  const normalizeAccounts = (raw) => {
    const rows = Array.isArray(raw)
      ? raw
      : (Array.isArray(raw?.accounts) ? raw.accounts : []);

    return rows
      .map((account) => ({
        id: account?.id ?? account?.account_id ?? null,
        account_code: account?.account_code ?? account?.code ?? account?.accountCode ?? '',
        account_name: account?.account_name ?? account?.name ?? account?.accountName ?? '',
        account_type: account?.account_type ?? account?.type ?? '',
        account_subtype: account?.account_subtype ?? account?.subtype ?? '',
        cash_bank_nature: account?.cash_bank_nature ?? account?.cashBankNature ?? '',
      }))
      .filter((account) => account.id !== null && account.id !== undefined && String(account.id).trim() !== '');
  };

  const isNumericAccountId = (value) => /^[0-9]+$/.test(String(value ?? '').trim());

  const fetchAccountsFromTrialBalance = async (token, asOfDateStr) => {
    const response = await fetchWithApiFallback(
      `/api/v1/journal-entries/reports/trial-balance?as_of=${asOfDateStr}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );
    const tbData = await response.json();
    const tbRows = Array.isArray(tbData?.accounts) ? tbData.accounts : [];
    return tbRows
      .map((acc) => ({
        id: acc?.account_id ?? acc?.id ?? null,
        account_code: acc?.account_code ?? acc?.code ?? '',
        account_name: acc?.account_name ?? acc?.name ?? '',
        account_type: acc?.account_type ?? acc?.type ?? '',
        account_subtype: acc?.account_subtype ?? acc?.subtype ?? '',
        cash_bank_nature: acc?.cash_bank_nature ?? acc?.cashBankNature ?? '',
      }))
      .filter((acc) => acc.id !== null && acc.id !== undefined && String(acc.id).trim() !== '');
  };

  const fetchAccounts = async () => {
    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/accounts/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const data = await response.json();
      let normalized = normalizeAccounts(data);

      // Fallback when /accounts shape is incompatible or returns non-ledger IDs.
      if (normalized.length === 0 || !normalized.some((account) => isNumericAccountId(account.id))) {
        try {
          const asOfDate = toDate.toISOString().split('T')[0];
          const trialBalanceAccounts = await fetchAccountsFromTrialBalance(token, asOfDate);
          if (trialBalanceAccounts.length > 0) {
            normalized = trialBalanceAccounts;
          }
        } catch (tbError) {
          console.warn('Trial balance fallback for account list failed:', tbError);
        }
      }

      setAccounts(normalized);
    } catch (error) {
      console.error('Error fetching accounts:', error);
      setAccounts([]);
    }
  };

  const fetchTrialBalance = async () => {
    setLoading(true);
    setReportError('');
    try {
      const token = getAccessToken();
      const asOfDate = toDate.toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/journal-entries/reports/trial-balance?as_of=${asOfDate}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      setTrialBalance(data);
    } catch (error) {
      console.error('Error fetching trial balance:', error);
      setTrialBalance(null);
      setReportError(error?.message || 'Unable to generate Trial Balance. Please retry or check backend status.');
    } finally {
      setLoading(false);
    }
  };

  const fetchLedger = async (accountOverride = null) => {
    const accountId = (
      typeof accountOverride === 'string' || typeof accountOverride === 'number'
    )
      ? accountOverride
      : selectedAccount;
    if (!accountId) {
      alert('Please select an account');
      return;
    }

    if (fromDate > toDate) {
      alert('From Date cannot be later than To Date');
      return;
    }

    setLoading(true);
    try {
      const token = getAccessToken();
      const fromDateStr = fromDate.toISOString().split('T')[0];
      const toDateStr = toDate.toISOString().split('T')[0];

      if (accountId === ALL_GT_ZERO_OPTION) {
        setLedgerErrors([]);

        // Keep account scope aligned with Trial Balance non-zero listing.
        let candidateAccounts = accounts;
        if (candidateAccounts.length === 0) {
          try {
            candidateAccounts = await fetchAccountsFromTrialBalance(token, toDateStr);
          } catch (tbError) {
            console.warn('Unable to derive accounts from trial balance for bulk ledger:', tbError);
          }
        }
        try {
          const tbResponse = await fetchWithApiFallback(
            `/api/v1/journal-entries/reports/trial-balance?as_of=${toDateStr}`,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
              },
            }
          );

          if (tbResponse.ok) {
            const tbData = await tbResponse.json();
            const nonZeroCodes = new Set(
              (Array.isArray(tbData?.accounts) ? tbData.accounts : []).map((acc) => String(acc.account_code))
            );
            const matchedAccounts = accounts.filter((acc) => nonZeroCodes.has(String(acc.account_code)));
            if (matchedAccounts.length > 0) {
              candidateAccounts = matchedAccounts;
            }
          }
        } catch (error) {
          console.warn('Trial balance account alignment failed, falling back to full account list.', error);
        }

        const ledgerResults = await Promise.all(
          candidateAccounts.map(async (account) => {
            try {
              if (!isNumericAccountId(account.id)) {
                return null;
              }
              const response = await fetchWithApiFallback(
                `/api/v1/journal-entries/reports/ledger/${account.id}?from_date=${fromDateStr}&to_date=${toDateStr}`,
                {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                  },
                }
              );

              if (!response.ok) {
                const errText = await response.text();
                return {
                  __error: true,
                  accountCode: String(account.account_code),
                  message: errText || `HTTP ${response.status}`,
                };
              }

              const data = await response.json();
              const entries = getLedgerEntries(data);
              const opening = Number(data.opening_balance || 0);
              const closing = Number(data.closing_balance || 0);
              const hasNonZero =
                Math.abs(opening) > 0.01 ||
                Math.abs(closing) > 0.01 ||
                entries.length > 0;

              return hasNonZero ? { __error: false, data } : null;
            } catch (error) {
              return {
                __error: true,
                accountCode: String(account.account_code),
                message: error?.message || 'Network/parse error',
              };
            }
          })
        );

        const errors = ledgerResults
          .filter((item) => item && item.__error)
          .map((item) => item.accountCode)
          .sort((a, b) => a.localeCompare(b));

        const filteredLedgers = ledgerResults
          .filter((item) => item && !item.__error)
          .map((item) => item.data)
          .sort((a, b) => String(a.account_code).localeCompare(String(b.account_code)));

        setLedgerErrors(errors);
        setBulkLedgers(filteredLedgers);
        setLedger(null);
      } else {
        setLedgerErrors([]);
        if (!isNumericAccountId(accountId)) {
          alert('Selected account cannot be resolved for ledger. Please refresh accounts and try again.');
          setLoading(false);
          return;
        }
        const response = await fetchWithApiFallback(
          `/api/v1/journal-entries/reports/ledger/${accountId}?from_date=${fromDateStr}&to_date=${toDateStr}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
        const data = await response.json();
        setLedger(data);
        setBulkLedgers([]);
      }
    } catch (error) {
      console.error('Error fetching ledger:', error);
      setLedger(null);
      setBulkLedgers([]);
    } finally {
      setLoading(false);
    }
  };

  const openLedgerFromTrialBalance = async (account) => {
    const accountId = account?.account_id ?? account?.id;
    if (!isNumericAccountId(accountId)) {
      alert('This Trial Balance row cannot be resolved to a ledger account.');
      return;
    }
    setSelectedAccount(String(accountId));
    setActiveTab(1);
    setLedger(null);
    setBulkLedgers([]);
    await fetchLedger(String(accountId));
  };

  const openVoucherDetail = async (txn) => {
    const journalId = ledgerJournalId(txn);
    if (!journalId) {
      setVoucherError('This ledger row does not include a posted journal id.');
      setVoucherDetail(null);
      setVoucherDialogOpen(true);
      return;
    }

    setVoucherError('');
    setVoucherDetail(null);
    setVoucherDialogOpen(true);
    setVoucherLoadingId(journalId);
    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback(
        `/api/v1/accounting/reports/vouchers/${journalId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Unable to load voucher detail (${response.status})`);
      }
      const data = await response.json();
      setVoucherDetail(data);
    } catch (error) {
      setVoucherError(error?.message || 'Unable to load voucher detail.');
    } finally {
      setVoucherLoadingId(null);
    }
  };

  const fetchProfitLoss = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const fromDateStr = fromDate.toISOString().split('T')[0];
      const toDateStr = toDate.toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/journal-entries/reports/profit-loss?from_date=${fromDateStr}&to_date=${toDateStr}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      setProfitLoss(data);
    } catch (error) {
      console.error('Error fetching profit & loss:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategoryIncome = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const fromDateStr = fromDate.toISOString().split('T')[0];
      const toDateStr = toDate.toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/journal-entries/reports/category-income?from_date=${fromDateStr}&to_date=${toDateStr}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      setCategoryIncome(data);
    } catch (error) {
      console.error('Error fetching category income:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTopDonors = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const fromDateStr = fromDate.toISOString().split('T')[0];
      const toDateStr = toDate.toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/journal-entries/reports/top-donors?from_date=${fromDateStr}&to_date=${toDateStr}&limit=10`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      setTopDonors(data);
    } catch (error) {
      console.error('Error fetching top donors:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <SummarizeIcon sx={{ fontSize: 40, mr: 2, color: '#FF9933' }} />
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            Accounting Reports
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button variant="outlined" onClick={() => navigate('/reports')}>Back to Reports</Button>
            <Button variant="outlined" onClick={() => navigate('/dashboard')}>Back to Dashboard</Button>
          </Box>
        </Box>

        <Paper>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Trial Balance" />
            <Tab label="Account Ledger" />
            <Tab label="Income & Expenditure" />
            <Tab label="Category Income" />
            <Tab label="Top Donors" />
            <Tab label="Balance Sheet" />
            <Tab label="Day Book" />
            <Tab label="Cash Book" />
            <Tab label="Bank Book" />
          </Tabs>

          {/* Trial Balance Tab */}
          <TabPanel value={activeTab} index={0}>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={4}>
                <TextField
                  label="As of Date"
                  type="date"
                  value={toDate.toISOString().split('T')[0]}
                  onChange={(e) => setToDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <Button
                  variant="contained"
                  onClick={fetchTrialBalance}
                  disabled={loading}
                  sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                  {loading ? 'Loading...' : 'Generate Report'}
                </Button>
              </Grid>
            </Grid>

            {reportError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {reportError}
              </Alert>
            )}

            {trialBalance && (
              <>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Trial Balance as of {formatDisplayDate(trialBalance.as_of || trialBalance.as_of_date)}
                </Alert>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <ExportButton onExport={handleTrialBalanceExport} filename="trial_balance" variant="outlined" />
                  <PrintButton
                    elementId="trial-balance-print"
                    title="Trial Balance"
                    variant="outlined"
                    reportContext={{ period: { to: formatDisplayDate(toDate) } }}
                  />
                </Box>

                <Box id="trial-balance-print">
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                          <TableCell><strong>Account Code</strong></TableCell>
                          <TableCell><strong>Account Name</strong></TableCell>
                          <TableCell align="right"><strong>Debit (₹)</strong></TableCell>
                          <TableCell align="right"><strong>Credit (₹)</strong></TableCell>
                          <TableCell align="center"><strong>Trace</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {safeArray(trialBalance?.lines || trialBalance?.accounts).map((account) => (
                          <TableRow key={account.account_id}>
                            <TableCell>{account.account_code ?? account.code ?? account.account_id}</TableCell>
                            <TableCell>{account.account_name ?? account.name}</TableCell>
                            <TableCell align="right">
                              {safeNumber(account.debit_total ?? account.debit_balance) > 0 ? safeAmount(account.debit_total ?? account.debit_balance) : '-'}
                            </TableCell>
                            <TableCell align="right">
                              {safeNumber(account.credit_total ?? account.credit_balance) > 0 ? safeAmount(account.credit_total ?? account.credit_balance) : '-'}
                            </TableCell>
                            <TableCell align="center">
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={() => openLedgerFromTrialBalance(account)}
                                disabled={loading}
                              >
                                Ledger
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow sx={{ bgcolor: '#FFF3E0', fontWeight: 'bold' }}>
                          <TableCell colSpan={2}><strong>TOTAL</strong></TableCell>
                          <TableCell align="right">
                            <strong>₹{safeAmount(trialBalance.total_debit ?? trialBalance.total_debits)}</strong>
                          </TableCell>
                          <TableCell align="right">
                            <strong>₹{safeAmount(trialBalance.total_credit ?? trialBalance.total_credits)}</strong>
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>

                {safeNumber(trialBalance.total_debit ?? trialBalance.total_debits) !== safeNumber(trialBalance.total_credit ?? trialBalance.total_credits) && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    Warning: Trial Balance is not balanced! Debits and Credits do not match.
                  </Alert>
                )}
              </>
            )}
          </TabPanel>

          {/* Account Ledger Tab */}
          <TabPanel value={activeTab} index={1}>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Select Account</InputLabel>
                  <Select
                    value={selectedAccount}
                    onChange={(e) => {
                      setSelectedAccount(e.target.value);
                      setLedger(null);
                      setBulkLedgers([]);
                    }}
                    label="Select Account"
                  >
                    <MenuItem value={ALL_GT_ZERO_OPTION}>
                      All Accounts (&gt;0)
                    </MenuItem>
                    {accounts.map((account) => (
                      <MenuItem key={account.id} value={account.id}>
                        {account.account_code ?? account.code ?? account.account_id} - {account.account_name ?? account.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  label="From Date"
                  type="date"
                  value={fromDate.toISOString().split('T')[0]}
                  onChange={(e) => setFromDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  label="To Date"
                  type="date"
                  value={toDate.toISOString().split('T')[0]}
                  onChange={(e) => setToDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <Button
                  variant="contained"
                  onClick={() => fetchLedger()}
                  disabled={loading || !selectedAccount}
                  fullWidth
                  sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                  {loading ? 'Loading...' : 'View Ledger'}
                </Button>
              </Grid>
            </Grid>

            {ledger && selectedAccount !== ALL_GT_ZERO_OPTION && (
              <>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Ledger for {ledger.account_code} - {ledger.account_name}
                  <br />
                  Period: {formatDisplayDate(ledger.from_date)} to {formatDisplayDate(ledger.to_date)}
                </Alert>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <ExportButton
                    onExport={handleLedgerExport}
                    filename="account_ledger"
                    variant="outlined"
                  />
                  <PrintButton
                    elementId="account-ledger-print"
                    title="Account Ledger"
                    variant="outlined"
                    reportContext={{ period: { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) } }}
                  />
                </Box>

                <Box id="account-ledger-print">
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                          <TableCell><strong>Date</strong></TableCell>
                          <TableCell><strong>Entry #</strong></TableCell>
                          <TableCell><strong>Description</strong></TableCell>
                          <TableCell align="right"><strong>Debit (₹)</strong></TableCell>
                          <TableCell align="right"><strong>Credit (₹)</strong></TableCell>
                          <TableCell align="right"><strong>Balance (₹)</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {/* Opening Balance */}
                        <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                          <TableCell colSpan={5}><strong>Opening Balance</strong></TableCell>
                          <TableCell align="right">
                            <strong>₹{safeAmount(ledger.opening_balance)}</strong>
                          </TableCell>
                        </TableRow>

                        {/* Transactions */}
                        {getLedgerEntries(ledger).map((txn, index) => (
                          <TableRow key={index}>
                            <TableCell>{formatDisplayDate(ledgerEntryDate(txn))}</TableCell>
                            <TableCell>
                              <Button
                                size="small"
                                variant="text"
                                onClick={() => openVoucherDetail(txn)}
                                disabled={voucherLoadingId === ledgerJournalId(txn)}
                                sx={{ minWidth: 0, p: 0, textTransform: 'none' }}
                              >
                                {ledgerEntryNumber(txn)}
                              </Button>
                            </TableCell>
                            <TableCell>{ledgerEntryDescription(txn)}</TableCell>
                            <TableCell align="right">
                              {safeNumber(txn.debit_amount) > 0 ? safeAmount(txn.debit_amount) : '-'}
                            </TableCell>
                            <TableCell align="right">
                              {safeNumber(txn.credit_amount) > 0 ? safeAmount(txn.credit_amount) : '-'}
                            </TableCell>
                            <TableCell align="right">{safeAmount(txn.running_balance)}</TableCell>
                          </TableRow>
                        ))}

                        {/* Closing Balance */}
                        <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                          <TableCell colSpan={5}><strong>Closing Balance</strong></TableCell>
                          <TableCell align="right">
                            <strong>₹{safeAmount(ledger.closing_balance)}</strong>
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              </>
            )}

            {selectedAccount === ALL_GT_ZERO_OPTION && ledgerErrors.length > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Could not load ledger for account code(s): {ledgerErrors.slice(0, 10).join(', ')}
              </Alert>
            )}

            {selectedAccount === ALL_GT_ZERO_OPTION && bulkLedgers.length > 0 && (
              <>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Ledger for all accounts with non-zero balance/transactions
                  <br />
                  Period: {formatDisplayDate(fromDate)} to {formatDisplayDate(toDate)}
                  <br />
                  Accounts: {bulkLedgers.length}
                </Alert>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <ExportButton
                    onExport={handleLedgerExport}
                    filename="account_ledger_all"
                    variant="outlined"
                  />
                  <PrintButton
                    elementId="bulk-ledger-print"
                    title="Account Ledger - All Accounts"
                    variant="outlined"
                    reportContext={{ period: { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) } }}
                  />
                </Box>

                <Box id="bulk-ledger-print">
                  {bulkLedgers.map((accountLedger) => (
                    <Box key={accountLedger.account_id} sx={{ mb: 4 }}>
                      <Typography variant="h6" sx={{ mb: 1 }}>
                        {accountLedger.account_code} - {accountLedger.account_name}
                      </Typography>
                      <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                          <TableHead>
                            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                              <TableCell><strong>Date</strong></TableCell>
                              <TableCell><strong>Entry #</strong></TableCell>
                              <TableCell><strong>Description</strong></TableCell>
                              <TableCell align="right"><strong>Debit (₹)</strong></TableCell>
                              <TableCell align="right"><strong>Credit (₹)</strong></TableCell>
                              <TableCell align="right"><strong>Balance (₹)</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                              <TableCell colSpan={5}><strong>Opening Balance</strong></TableCell>
                              <TableCell align="right">
                                <strong>₹{safeAmount(accountLedger.opening_balance)}</strong>
                              </TableCell>
                            </TableRow>

                            {getLedgerEntries(accountLedger).map((txn, index) => (
                              <TableRow key={`${accountLedger.account_id}-${index}`}>
                                <TableCell>{formatDisplayDate(ledgerEntryDate(txn))}</TableCell>
                                <TableCell>
                                  <Button
                                    size="small"
                                    variant="text"
                                    onClick={() => openVoucherDetail(txn)}
                                    disabled={voucherLoadingId === ledgerJournalId(txn)}
                                    sx={{ minWidth: 0, p: 0, textTransform: 'none' }}
                                  >
                                    {ledgerEntryNumber(txn)}
                                  </Button>
                                </TableCell>
                                <TableCell>{ledgerEntryDescription(txn)}</TableCell>
                                <TableCell align="right">
                                  {safeNumber(txn.debit_amount) > 0 ? safeAmount(txn.debit_amount) : '-'}
                                </TableCell>
                                <TableCell align="right">
                                  {safeNumber(txn.credit_amount) > 0 ? safeAmount(txn.credit_amount) : '-'}
                                </TableCell>
                                <TableCell align="right">{safeAmount(txn.running_balance)}</TableCell>
                              </TableRow>
                            ))}

                            <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                              <TableCell colSpan={5}><strong>Closing Balance</strong></TableCell>
                              <TableCell align="right">
                                <strong>₹{safeAmount(accountLedger.closing_balance)}</strong>
                              </TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  ))}
                </Box>
              </>
            )}
          </TabPanel>

          {/* Profit & Loss Tab */}
          <TabPanel value={activeTab} index={2}>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={3}>
                <TextField
                  label="From Date"
                  type="date"
                  value={fromDate.toISOString().split('T')[0]}
                  onChange={(e) => setFromDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  label="To Date"
                  type="date"
                  value={toDate.toISOString().split('T')[0]}
                  onChange={(e) => setToDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <Button
                  variant="contained"
                  onClick={fetchProfitLoss}
                  disabled={loading}
                  sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                  {loading ? 'Loading...' : 'Generate Report'}
                </Button>
              </Grid>
            </Grid>

            {profitLoss && (
              <>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Income & Expenditure Statement
                  <br />
                  Period: {formatDisplayDate(profitLoss.from_date)} to {formatDisplayDate(profitLoss.to_date)}
                </Alert>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <ExportButton onExport={handleProfitLossExport} filename="income_expenditure" variant="outlined" />
                  <PrintButton
                    elementId="profit-loss-print"
                    title="Income and Expenditure"
                    variant="outlined"
                    reportContext={{ period: { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) } }}
                  />
                </Box>

                <Box id="profit-loss-print">
                  {/* Income Section */}
                  <Typography variant="h6" sx={{ mt: 2, mb: 1, bgcolor: '#FFF3E0', p: 1 }}>
                    <strong>INCOME</strong>
                  </Typography>
                  {safeArray(profitLoss.income_groups).map((group, idx) => (
                    <Box key={idx} sx={{ mb: 2 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                        {group.category_name}
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableBody>
                            {safeArray(group.accounts).map((acc, accIdx) => (
                              <TableRow key={`${group.category_name}-${acc.account_code}-${accIdx}`}>
                                <TableCell sx={{ pl: 4 }}>{acc.account_code}</TableCell>
                                <TableCell>{acc.account_name}</TableCell>
                                <TableCell align="right">₹{safeAmount(acc.amount)}</TableCell>
                              </TableRow>
                            ))}
                            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                              <TableCell colSpan={2} sx={{ pl: 4 }}>
                                <strong>Total {group.category_name}</strong>
                              </TableCell>
                              <TableCell align="right">
                                <strong>₹{safeAmount(group.total)}</strong>
                              </TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  ))}
                  <Box sx={{ bgcolor: '#FFF3E0', p: 2, mb: 3 }}>
                    <Grid container>
                      <Grid item xs={8}>
                        <Typography variant="h6"><strong>TOTAL INCOME</strong></Typography>
                      </Grid>
                      <Grid item xs={4} sx={{ textAlign: 'right' }}>
                        <Typography variant="h6"><strong>₹{safeAmount(profitLoss.total_income)}</strong></Typography>
                      </Grid>
                    </Grid>
                  </Box>

                  {/* Expenses Section */}
                  <Typography variant="h6" sx={{ mt: 2, mb: 1, bgcolor: '#FFF3E0', p: 1 }}>
                    <strong>EXPENSES</strong>
                  </Typography>
                  {safeArray(profitLoss.expense_groups).map((group, idx) => (
                    <Box key={idx} sx={{ mb: 2 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                        {group.category_name}
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableBody>
                            {safeArray(group.accounts).map((acc, accIdx) => (
                              <TableRow key={`${group.category_name}-${acc.account_code}-${accIdx}`}>
                                <TableCell sx={{ pl: 4 }}>{acc.account_code}</TableCell>
                                <TableCell>{acc.account_name}</TableCell>
                                <TableCell align="right">₹{safeAmount(acc.amount)}</TableCell>
                              </TableRow>
                            ))}
                            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                              <TableCell colSpan={2} sx={{ pl: 4 }}>
                                <strong>Total {group.category_name}</strong>
                              </TableCell>
                              <TableCell align="right">
                                <strong>₹{safeAmount(group.total)}</strong>
                              </TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  ))}
                  <Box sx={{ bgcolor: '#FFF3E0', p: 2, mb: 3 }}>
                    <Grid container>
                      <Grid item xs={8}>
                        <Typography variant="h6"><strong>TOTAL EXPENSES</strong></Typography>
                      </Grid>
                      <Grid item xs={4} sx={{ textAlign: 'right' }}>
                        <Typography variant="h6"><strong>₹{safeAmount(profitLoss.total_expenses)}</strong></Typography>
                      </Grid>
                    </Grid>
                  </Box>

                  {/* Net Surplus/Deficit */}
                  <Box sx={{ bgcolor: safeNumber(profitLoss.net_surplus) >= 0 ? '#C8E6C9' : '#FFCDD2', p: 2 }}>
                    <Grid container>
                      <Grid item xs={8}>
                        <Typography variant="h5">
                          <strong>{safeNumber(profitLoss.net_surplus) >= 0 ? 'NET SURPLUS' : 'NET DEFICIT'}</strong>
                        </Typography>
                      </Grid>
                      <Grid item xs={4} sx={{ textAlign: 'right' }}>
                        <Typography variant="h5">
                          <strong>₹{safeAmount(Math.abs(safeNumber(profitLoss.net_surplus)))}</strong>
                        </Typography>
                      </Grid>
                    </Grid>
                  </Box>
                </Box>
              </>
            )}
          </TabPanel>

          {/* Category Income Tab */}
          <TabPanel value={activeTab} index={3}>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={3}>
                <TextField
                  label="From Date"
                  type="date"
                  value={fromDate.toISOString().split('T')[0]}
                  onChange={(e) => setFromDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  label="To Date"
                  type="date"
                  value={toDate.toISOString().split('T')[0]}
                  onChange={(e) => setToDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <Button
                  variant="contained"
                  onClick={fetchCategoryIncome}
                  disabled={loading}
                  sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                  {loading ? 'Loading...' : 'Generate Report'}
                </Button>
              </Grid>
            </Grid>

            {categoryIncome && (
              <>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Category-wise Income Report
                  <br />
                  Period: {formatDisplayDate(categoryIncome.from_date)} to {formatDisplayDate(categoryIncome.to_date)}
                  <br />
                  Total Income: ₹{safeAmount(categoryIncome.total_income)}
                </Alert>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <ExportButton onExport={handleCategoryIncomeExport} filename="category_income" variant="outlined" />
                  <PrintButton
                    elementId="category-income-print"
                    title="Category Income"
                    variant="outlined"
                    reportContext={{ period: { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) } }}
                  />
                </Box>

                <Box id="category-income-print">
                  {/* Donation Income */}
                  <Typography variant="h6" sx={{ mt: 2, mb: 1, bgcolor: '#FFF3E0', p: 1 }}>
                    <strong>DONATION INCOME</strong>
                  </Typography>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                          <TableCell><strong>Code</strong></TableCell>
                          <TableCell><strong>Category</strong></TableCell>
                          <TableCell align="right"><strong>Amount (₹)</strong></TableCell>
                          <TableCell align="right"><strong>%</strong></TableCell>
                          <TableCell align="right"><strong>Transactions</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {safeArray(categoryIncome.donation_income).map((item, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{item.account_code}</TableCell>
                            <TableCell>{item.account_name}</TableCell>
                            <TableCell align="right">₹{safeAmount(item.amount)}</TableCell>
                            <TableCell align="right">{item.percentage}%</TableCell>
                            <TableCell align="right">{item.transaction_count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {/* Seva Income */}
                  <Typography variant="h6" sx={{ mt: 3, mb: 1, bgcolor: '#FFF3E0', p: 1 }}>
                    <strong>SEVA INCOME</strong>
                  </Typography>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                          <TableCell><strong>Code</strong></TableCell>
                          <TableCell><strong>Seva Type</strong></TableCell>
                          <TableCell align="right"><strong>Amount (₹)</strong></TableCell>
                          <TableCell align="right"><strong>%</strong></TableCell>
                          <TableCell align="right"><strong>Bookings</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {safeArray(categoryIncome.seva_income).map((item, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{item.account_code}</TableCell>
                            <TableCell>{item.account_name}</TableCell>
                            <TableCell align="right">₹{safeAmount(item.amount)}</TableCell>
                            <TableCell align="right">{item.percentage}%</TableCell>
                            <TableCell align="right">{item.transaction_count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {/* Other Income */}
                  {safeArray(categoryIncome.other_income).length > 0 && (
                    <>
                      <Typography variant="h6" sx={{ mt: 3, mb: 1, bgcolor: '#FFF3E0', p: 1 }}>
                        <strong>OTHER INCOME</strong>
                      </Typography>
                      <TableContainer>
                        <Table>
                          <TableHead>
                            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                              <TableCell><strong>Code</strong></TableCell>
                              <TableCell><strong>Category</strong></TableCell>
                              <TableCell align="right"><strong>Amount (₹)</strong></TableCell>
                              <TableCell align="right"><strong>%</strong></TableCell>
                              <TableCell align="right"><strong>Transactions</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {safeArray(categoryIncome.other_income).map((item, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{item.account_code}</TableCell>
                                <TableCell>{item.account_name}</TableCell>
                                <TableCell align="right">₹{safeAmount(item.amount)}</TableCell>
                                <TableCell align="right">{item.percentage}%</TableCell>
                                <TableCell align="right">{item.transaction_count}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </>
                  )}
                </Box>
              </>
            )}
          </TabPanel>

          {/* Top Donors Tab */}
          <TabPanel value={activeTab} index={4}>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={3}>
                <TextField
                  label="From Date"
                  type="date"
                  value={fromDate.toISOString().split('T')[0]}
                  onChange={(e) => setFromDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  label="To Date"
                  type="date"
                  value={toDate.toISOString().split('T')[0]}
                  onChange={(e) => setToDate(new Date(e.target.value))}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <Button
                  variant="contained"
                  onClick={fetchTopDonors}
                  disabled={loading}
                  sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                  {loading ? 'Loading...' : 'Generate Report'}
                </Button>
              </Grid>
            </Grid>

            {topDonors && (
              <>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Top {safeArray(topDonors.donors).length} Donors
                  <br />
                  Period: {formatDisplayDate(topDonors.from_date)} to {formatDisplayDate(topDonors.to_date)}
                  <br />
                  Total Donations: ₹{safeAmount(topDonors.total_amount)} from {topDonors.total_donors} donors
                </Alert>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <ExportButton onExport={handleTopDonorsExport} filename="top_donors" variant="outlined" />
                  <PrintButton
                    elementId="top-donors-print"
                    title="Top Donors"
                    variant="outlined"
                    reportContext={{ period: { from: formatDisplayDate(fromDate), to: formatDisplayDate(toDate) } }}
                  />
                </Box>

                <Box id="top-donors-print">
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                          <TableCell><strong>Rank</strong></TableCell>
                          <TableCell><strong>Devotee Name</strong></TableCell>
                          <TableCell align="right"><strong>Total Donated (₹)</strong></TableCell>
                          <TableCell align="right"><strong>Donations</strong></TableCell>
                          <TableCell><strong>Last Donation</strong></TableCell>
                          <TableCell><strong>Categories</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {safeArray(topDonors.donors).map((donor, idx) => (
                          <TableRow key={donor.devotee_id}>
                            <TableCell>
                              <Box
                                sx={{
                                  width: 30,
                                  height: 30,
                                  borderRadius: '50%',
                                  bgcolor: idx === 0 ? '#FFD700' : idx === 1 ? '#C0C0C0' : idx === 2 ? '#CD7F32' : '#FF9933',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'white',
                                  fontWeight: 'bold',
                                }}
                              >
                                {idx + 1}
                              </Box>
                            </TableCell>
                            <TableCell><strong>{donor.devotee_name}</strong></TableCell>
                            <TableCell align="right">
                              <Typography variant="h6" sx={{ color: '#FF9933' }}>
                                ₹{safeAmount(donor.total_donated)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">{donor.donation_count}</TableCell>
                            <TableCell>{formatDisplayDate(donor.last_donation_date)}</TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {safeArray(donor.categories).map((cat, catIdx) => (
                                  <Box
                                    key={catIdx}
                                    sx={{
                                      bgcolor: '#FFF3E0',
                                      px: 1,
                                      py: 0.5,
                                      borderRadius: 1,
                                      fontSize: '0.75rem',
                                    }}
                                  >
                                    {cat}
                                  </Box>
                                ))}
                              </Box>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              </>
            )}
          </TabPanel>

          {/* Balance Sheet Tab */}
          <TabPanel value={activeTab} index={5}>
            <BalanceSheetReport token={getAccessToken() || ''} />
          </TabPanel>

          {/* Day Book Tab */}
          <TabPanel value={activeTab} index={6}>
            <DayBookReport token={getAccessToken() || ''} />
          </TabPanel>

          {/* Cash Book Tab */}
          <TabPanel value={activeTab} index={7}>
            <CashBookReport token={getAccessToken() || ''} />
          </TabPanel>

          {/* Bank Book Tab */}
          <TabPanel value={activeTab} index={8}>
            <BankBookReport token={getAccessToken() || ''} accounts={accounts} />
          </TabPanel>

        </Paper>
        <Dialog
          open={voucherDialogOpen}
          onClose={() => setVoucherDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            Voucher Detail
            {voucherDetail?.reference ? ` - ${voucherDetail.reference}` : ''}
          </DialogTitle>
          <DialogContent dividers>
            {voucherLoadingId && (
              <Typography color="text.secondary">Loading voucher {voucherLoadingId}...</Typography>
            )}
            {voucherError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {voucherError}
              </Alert>
            )}
            {voucherDetail && (
              <>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={12} md={4}>
                    <Typography variant="body2" color="text.secondary">Date</Typography>
                    <Typography>{formatDisplayDate(voucherDetail.entry_date)}</Typography>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Typography variant="body2" color="text.secondary">Reference</Typography>
                    <Typography>{voucherDetail.reference || '-'}</Typography>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Typography variant="body2" color="text.secondary">Status</Typography>
                    <Typography>{voucherDetail.status || '-'}</Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">Description</Typography>
                    <Typography>{voucherDetail.description || '-'}</Typography>
                  </Grid>
                </Grid>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                        <TableCell><strong>Account</strong></TableCell>
                        <TableCell><strong>Name</strong></TableCell>
                        <TableCell align="right"><strong>Debit (₹)</strong></TableCell>
                        <TableCell align="right"><strong>Credit (₹)</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {safeArray(voucherDetail.lines).map((line) => (
                        <TableRow key={line.line_id || `${line.account_code}-${line.account_name}`}>
                          <TableCell>{line.account_code}</TableCell>
                          <TableCell>{line.account_name}</TableCell>
                          <TableCell align="right">
                            {safeNumber(line.debit) > 0 ? safeAmount(line.debit) : '-'}
                          </TableCell>
                          <TableCell align="right">
                            {safeNumber(line.credit) > 0 ? safeAmount(line.credit) : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setVoucherDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Layout>
  );
}

export default AccountingReports;





