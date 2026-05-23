import React, { useEffect, useMemo, useState } from 'react';
import api from '../../services/api';
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import Layout from '../../components/Layout';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AddIcon from '@mui/icons-material/Add';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import EditIcon from '@mui/icons-material/Edit';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { getAccessToken } from '../../utils/authStorage';
import { ACTIVE_TEMPLE_EVENT } from '../../utils/activeTemple';

const ACCOUNT_TYPES = [
  { value: 'asset', label: 'Asset' },
  { value: 'liability', label: 'Liability' },
  { value: 'income', label: 'Income' },
  { value: 'expense', label: 'Expense' },
  { value: 'equity', label: 'Equity' },
];

const ACCOUNT_SUBTYPES = {
  asset: ['cash_bank', 'current_asset', 'fixed_asset', 'precious_asset', 'inventory', 'receivable'],
  liability: ['current_liability', 'long_term_liability'],
  income: ['donation_income', 'seva_income', 'sponsorship_income', 'other_income'],
  expense: ['operational_expense', 'ritual_expense', 'administrative_expense', 'festival_expense'],
  equity: ['corpus_fund', 'general_fund'],
};

const toDisplay = (value) => value.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());

function AccountRow({ account, level = 0, onEdit }) {
  const [open, setOpen] = useState(level === 0);
  const normalizedType = String(account.account_type || '').toUpperCase();

  const getAccountTypeColor = (type) => {
    switch (type) {
      case 'ASSET':
        return 'success';
      case 'LIABILITY':
        return 'error';
      case 'INCOME':
        return 'primary';
      case 'EXPENSE':
        return 'warning';
      case 'EQUITY':
        return 'info';
      default:
        return 'default';
    }
  };

  const getAccountTypeIcon = (type) => {
    switch (type) {
      case 'ASSET':
        return <AccountBalanceIcon fontSize="small" />;
      case 'LIABILITY':
        return <TrendingDownIcon fontSize="small" />;
      case 'INCOME':
        return <TrendingUpIcon fontSize="small" />;
      case 'EXPENSE':
        return <TrendingDownIcon fontSize="small" />;
      case 'EQUITY':
        return <AccountBalanceWalletIcon fontSize="small" />;
      default:
        return null;
    }
  };

  const hasSubAccounts = account.sub_accounts && account.sub_accounts.length > 0;

  return (
    <>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' }, bgcolor: level === 0 ? '#f5f5f5' : 'inherit' }}>
        <TableCell>
          {hasSubAccounts ? (
            <IconButton size="small" onClick={() => setOpen(!open)}>
              {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
            </IconButton>
          ) : (
            <Box sx={{ width: 40 }} />
          )}
        </TableCell>
        <TableCell>
          <Box sx={{ pl: level * 3 }}>{account.account_code}</Box>
        </TableCell>
        <TableCell>
          <Box sx={{ pl: level * 3 }}>
            <Typography sx={{ fontWeight: level === 0 ? 'bold' : 'normal' }}>
              {account.account_name}
            </Typography>
            {account.account_name_kannada && (
              <Typography variant="caption" color="text.secondary">
                {account.account_name_kannada}
              </Typography>
            )}
          </Box>
        </TableCell>
        <TableCell>
          <Chip
            icon={getAccountTypeIcon(normalizedType)}
            label={normalizedType || account.account_type}
            size="small"
            color={getAccountTypeColor(normalizedType)}
          />
        </TableCell>
        <TableCell align="right">
          {account.is_system_account && <Chip label="System" size="small" variant="outlined" />}
        </TableCell>
        <TableCell>
          <Chip
            label={account.is_active ? 'Active' : 'Inactive'}
            size="small"
            color={account.is_active ? 'success' : 'default'}
          />
        </TableCell>
        <TableCell align="right">
          <IconButton size="small" onClick={() => onEdit(account)} title="Edit nomenclature">
            <EditIcon fontSize="small" />
          </IconButton>
        </TableCell>
      </TableRow>
      {hasSubAccounts && (
        <TableRow>
          <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
            <Collapse in={open} timeout="auto" unmountOnExit>
              <Table size="small">
                <TableBody>
                  {account.sub_accounts.map((subAccount) => (
                    <AccountRow
                      key={subAccount.id}
                      account={subAccount}
                      level={level + 1}
                      onEdit={onEdit}
                    />
                  ))}
                </TableBody>
              </Table>
            </Collapse>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function ChartOfAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [newAccount, setNewAccount] = useState({
    account_code: '',
    account_name: '',
    account_type: 'asset',
    account_subtype: '',
    description: '',
    parent_account_id: '',
  });
  const [stats, setStats] = useState({
    ASSET: 0,
    LIABILITY: 0,
    INCOME: 0,
    EXPENSE: 0,
    EQUITY: 0,
  });
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [openingBalanceFile, setOpeningBalanceFile] = useState(null);
  const [legacyAccountFile, setLegacyAccountFile] = useState(null);
  const [uploadingOpeningBalances, setUploadingOpeningBalances] = useState(false);
  const [uploadingLegacyAccounts, setUploadingLegacyAccounts] = useState(false);
  const [editForm, setEditForm] = useState({
    id: null,
    account_code: '',
    account_name: '',
    account_name_kannada: '',
    description: '',
    reason: '',
  });

  const subtypeOptions = useMemo(() => ACCOUNT_SUBTYPES[newAccount.account_type] || [], [newAccount.account_type]);
  const normalizeApiError = (error, fallbackMessage) => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const joined = detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
            const msg = typeof item.msg === 'string' ? item.msg : JSON.stringify(item);
            return loc ? `${loc}: ${msg}` : msg;
          }
          return String(item || '');
        })
        .filter(Boolean)
        .join('; ');
      if (joined) {
        return joined;
      }
    }
    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail);
      } catch (_e) {
        return fallbackMessage;
      }
    }
    return fallbackMessage;
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  useEffect(() => {
    const handleActiveTempleChange = () => {
      fetchAccounts();
    };

    window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
    return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
  }, []);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/accounts/hierarchy`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to fetch accounts');
      }

      const data = await response.json();
      const accountData = Array.isArray(data) ? data : [];
      setAccounts(accountData);

      const calculateStats = (accs) => {
        const next = { ASSET: 0, LIABILITY: 0, INCOME: 0, EXPENSE: 0, EQUITY: 0 };
        const countAccounts = (items) => {
          items.forEach((acc) => {
            const typeKey = String(acc.account_type || '').toUpperCase();
            if (Object.prototype.hasOwnProperty.call(next, typeKey)) {
              next[typeKey] += 1;
            }
            if (acc.sub_accounts && acc.sub_accounts.length > 0) {
              countAccounts(acc.sub_accounts);
            }
          });
        };
        countAccounts(accs);
        return next;
      };

      setStats(calculateStats(accountData));
    } catch (error) {
      console.error('Error fetching accounts:', error);
      setMessage({ type: 'error', text: error.message || 'Failed to fetch accounts' });
    } finally {
      setLoading(false);
    }
  };

  const handleInitializeDefaults = async () => {
    try {
      setInitializing(true);
      setMessage({ type: '', text: '' });
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/accounts/import-legacy`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to import legacy accounts');
      }

      setMessage({
        type: 'success',
        text: `${data.message || 'Legacy COA imported'} (Created: ${data.created || 0}${typeof data.reactivated === 'number' ? `, Reactivated: ${data.reactivated}` : ''})`,
      });
      await fetchAccounts();
    } catch (error) {
      console.error('Error initializing default accounts:', error);
      setMessage({ type: 'error', text: error.message || 'Failed to import legacy accounts' });
    } finally {
      setInitializing(false);
    }
  };

  const handleCreateAccount = async () => {
    if (!/^\d{5}$/.test(newAccount.account_code)) {
      setMessage({ type: 'error', text: 'Account code must be exactly 5 digits.' });
      return;
    }
    if (!newAccount.account_name.trim()) {
      setMessage({ type: 'error', text: 'Account name is required.' });
      return;
    }

    try {
      setSaving(true);
      setMessage({ type: '', text: '' });

      const token = getAccessToken();
      const payload = {
        account_code: newAccount.account_code.trim(),
        account_name: newAccount.account_name.trim(),
        account_type: newAccount.account_type,
        account_subtype: newAccount.account_subtype || null,
        description: newAccount.description?.trim() || null,
        parent_account_id: newAccount.parent_account_id ? parseInt(newAccount.parent_account_id, 10) : null,
        allow_manual_entry: true,
      };

      const response = await fetchWithApiFallback(`/api/v1/accounts/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to add account');
      }

      setOpenAddDialog(false);
      setNewAccount({
        account_code: '',
        account_name: '',
        account_type: 'asset',
        account_subtype: '',
        description: '',
        parent_account_id: '',
      });
      setMessage({ type: 'success', text: 'Account added successfully.' });
      await fetchAccounts();
    } catch (error) {
      console.error('Error adding account:', error);
      setMessage({ type: 'error', text: error.message || 'Failed to add account' });
    } finally {
      setSaving(false);
    }
  };

  const downloadOpeningBalanceTemplate = async () => {
    try {
      const response = await fetch('/api/v1/opening-balances/template', {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${getAccessToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download template');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Opening_Balance_Template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading template:', error);
      setMessage({ type: 'error', text: 'Failed to download template' });
    }
  };

  const handleImportOpeningBalances = async () => {
    if (!openingBalanceFile) {
      setMessage({ type: 'error', text: 'Select an opening balance CSV/XLSX file first.' });
      return;
    }

    try {
      setUploadingOpeningBalances(true);
      setMessage({ type: '', text: '' });
      const formData = new FormData();
      formData.append('file', openingBalanceFile);
      const response = await api.post('/api/v1/opening-balances/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage({
        type: response.data.errors?.length ? 'warning' : 'success',
        text: `Opening balance upload complete. Updated ${response.data.updated_count || 0} account(s).`,
      });
      setOpeningBalanceFile(null);
      await fetchAccounts();
    } catch (error) {
      console.error('Error importing opening balances:', error);
      setMessage({ type: 'error', text: normalizeApiError(error, 'Failed to import opening balances') });
    } finally {
      setUploadingOpeningBalances(false);
    }
  };

  const handleImportLegacyAccounts = async () => {
    if (!legacyAccountFile) {
      setMessage({ type: 'error', text: 'Select a legacy account CSV/XLSX file first.' });
      return;
    }

    try {
      setUploadingLegacyAccounts(true);
      setMessage({ type: '', text: '' });
      const formData = new FormData();
      formData.append('file', legacyAccountFile);
      const response = await api.post('/api/v1/accounts/import-legacy', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage({
        type: response.data.errors?.length ? 'warning' : 'success',
        text: `Legacy account upload complete. Created ${response.data.created_count || 0}, updated ${response.data.updated_count || 0}.`,
      });
      setLegacyAccountFile(null);
      await fetchAccounts();
    } catch (error) {
      console.error('Error importing legacy accounts:', error);
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to import legacy accounts' });
    } finally {
      setUploadingLegacyAccounts(false);
    }
  };

  const handleOpenEditDialog = (account) => {
    setEditForm({
      id: account.id,
      account_code: account.account_code || '',
      account_name: account.account_name || '',
      account_name_kannada: account.account_name_kannada || '',
      description: account.description || '',
      reason: 'Nomenclature correction',
    });
    setOpenEditDialog(true);
  };

  const handleUpdateAccount = async () => {
    if (!editForm.id) {
      setMessage({ type: 'error', text: 'Invalid account selected.' });
      return;
    }

    if (!editForm.account_name.trim()) {
      setMessage({ type: 'error', text: 'Account name is required.' });
      return;
    }

    if (!editForm.reason.trim()) {
      setMessage({ type: 'error', text: 'Reason is required for audit trail.' });
      return;
    }

    try {
      setEditSaving(true);
      setMessage({ type: '', text: '' });
      const token = getAccessToken();
      const reason = encodeURIComponent(editForm.reason.trim());
      const response = await fetchWithApiFallback(
        `/api/v1/accounts/${editForm.id}?reason=${reason}`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            account_name: editForm.account_name.trim(),
            account_name_kannada: editForm.account_name_kannada.trim() || null,
            description: editForm.description.trim() || null,
          }),
        },
      );

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update account');
      }

      setOpenEditDialog(false);
      setMessage({ type: 'success', text: `Updated account ${editForm.account_code} successfully.` });
      await fetchAccounts();
    } catch (error) {
      console.error('Error updating account:', error);
      setMessage({ type: 'error', text: error.message || 'Failed to update account' });
    } finally {
      setEditSaving(false);
    }
  };

  return (
    <Layout>
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <AccountTreeIcon sx={{ fontSize: 40, mr: 2, color: '#FF9933' }} />
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
              Chart of Accounts
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button
              variant="outlined"
              startIcon={<RestartAltIcon />}
              onClick={handleInitializeDefaults}
              disabled={initializing || loading}
            >
              {initializing ? 'Importing...' : 'Import Legacy COA'}
            </Button>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenAddDialog(true)}>
              Add Account
            </Button>
          </Box>
        </Box>

        <Box sx={{ display: 'grid', gap: 2, mb: 3 }}>
          <Paper sx={{ p: 2, borderLeft: '5px solid #1565C0' }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Opening Balance Upload</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload CSV or XLSX with columns like `account_code`, `opening_balance_debit`, `opening_balance_credit` or `opening_balance`.
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <Button variant="outlined" component="label">
                {openingBalanceFile ? openingBalanceFile.name : 'Choose Opening Balance File'}
                <input hidden type="file" accept=".csv,.xlsx" onChange={(e) => setOpeningBalanceFile(e.target.files?.[0] || null)} />
              </Button>
              <Button
                variant="outlined"
                startIcon={<FileDownloadIcon />}
                onClick={downloadOpeningBalanceTemplate}
              >
                Download Template
              </Button>
              <Button variant="contained" onClick={handleImportOpeningBalances} disabled={uploadingOpeningBalances}>
                {uploadingOpeningBalances ? 'Uploading...' : 'Upload Opening Balances'}
              </Button>
            </Box>
          </Paper>

          <Paper sx={{ p: 2, borderLeft: '5px solid #2E7D32' }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Legacy Accounts Upload</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload legacy account masters using `legacy_code` or `account_code` with the latest account naming and balances. 4-digit legacy codes are mapped into the current 5-digit COA format.
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <Button variant="outlined" component="label">
                {legacyAccountFile ? legacyAccountFile.name : 'Choose Legacy Account File'}
                <input hidden type="file" accept=".csv,.xlsx" onChange={(e) => setLegacyAccountFile(e.target.files?.[0] || null)} />
              </Button>
              <Button variant="contained" color="success" onClick={handleImportLegacyAccounts} disabled={uploadingLegacyAccounts}>
                {uploadingLegacyAccounts ? 'Uploading...' : 'Upload Legacy Accounts'}
              </Button>
            </Box>
          </Paper>
        </Box>

        {message.text && (
          <Alert severity={message.type || 'info'} sx={{ mb: 2 }} onClose={() => setMessage({ type: '', text: '' })}>
            {message.text}
          </Alert>
        )}

        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Paper sx={{ p: 2, flex: 1, minWidth: 150 }}>
            <Typography variant="body2" color="text.secondary">Asset Accounts</Typography>
            <Typography variant="h4" color="success.main">{stats.ASSET}</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 150 }}>
            <Typography variant="body2" color="text.secondary">Liability Accounts</Typography>
            <Typography variant="h4" color="error.main">{stats.LIABILITY}</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 150 }}>
            <Typography variant="body2" color="text.secondary">Income Accounts</Typography>
            <Typography variant="h4" color="primary.main">{stats.INCOME}</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 150 }}>
            <Typography variant="body2" color="text.secondary">Expense Accounts</Typography>
            <Typography variant="h4" color="warning.main">{stats.EXPENSE}</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 150 }}>
            <Typography variant="body2" color="text.secondary">Equity Accounts</Typography>
            <Typography variant="h4" color="info.main">{stats.EQUITY}</Typography>
          </Paper>
        </Box>

        <Alert severity="info" sx={{ mb: 3 }}>
          This is your complete chart of accounts hierarchy. Click the arrow icons to expand/collapse account groups.
        </Alert>

        <Paper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#FF9933' }}>
                  <TableCell sx={{ color: 'white', width: 50 }} />
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Code</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Account Name</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Type</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">System</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Status</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography>Loading accounts...</Typography>
                    </TableCell>
                  </TableRow>
                ) : accounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary">No accounts found</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  accounts.map((account) => (
                    <AccountRow
                      key={account.id}
                      account={account}
                      onEdit={handleOpenEditDialog}
                    />
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>

        <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)} fullWidth maxWidth="sm">
          <DialogTitle>Add Account</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'grid', gap: 2, mt: 1 }}>
              <TextField
                label="Account Code"
                placeholder="e.g., 51099"
                value={newAccount.account_code}
                onChange={(e) => setNewAccount((prev) => ({ ...prev, account_code: e.target.value.replace(/\D/g, '').slice(0, 5) }))}
                helperText="Exactly 5 digits"
                required
                fullWidth
              />
              <TextField
                label="Account Name"
                value={newAccount.account_name}
                onChange={(e) => setNewAccount((prev) => ({ ...prev, account_name: e.target.value }))}
                required
                fullWidth
              />
              <TextField
                select
                label="Account Type"
                value={newAccount.account_type}
                onChange={(e) =>
                  setNewAccount((prev) => ({
                    ...prev,
                    account_type: e.target.value,
                    account_subtype: '',
                  }))
                }
                fullWidth
              >
                {ACCOUNT_TYPES.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Account Subtype (Optional)"
                value={newAccount.account_subtype}
                onChange={(e) => setNewAccount((prev) => ({ ...prev, account_subtype: e.target.value }))}
                fullWidth
              >
                <MenuItem value="">None</MenuItem>
                {subtypeOptions.map((subtype) => (
                  <MenuItem key={subtype} value={subtype}>
                    {toDisplay(subtype)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Parent Account ID (Optional)"
                value={newAccount.parent_account_id}
                onChange={(e) => setNewAccount((prev) => ({ ...prev, parent_account_id: e.target.value.replace(/\D/g, '') }))}
                fullWidth
              />
              <TextField
                label="Description (Optional)"
                value={newAccount.description}
                onChange={(e) => setNewAccount((prev) => ({ ...prev, description: e.target.value }))}
                multiline
                rows={2}
                fullWidth
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenAddDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateAccount} variant="contained" disabled={saving}>
              {saving ? 'Saving...' : 'Add Account'}
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={openEditDialog} onClose={() => setOpenEditDialog(false)} fullWidth maxWidth="sm">
          <DialogTitle>Edit Account Nomenclature</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'grid', gap: 2, mt: 1 }}>
              <TextField
                label="Account Code"
                value={editForm.account_code}
                fullWidth
                disabled
              />
              <TextField
                label="Account Name"
                value={editForm.account_name}
                onChange={(e) => setEditForm((prev) => ({ ...prev, account_name: e.target.value }))}
                required
                fullWidth
              />
              <TextField
                label="Account Name (Kannada, Optional)"
                value={editForm.account_name_kannada}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, account_name_kannada: e.target.value }))
                }
                fullWidth
              />
              <TextField
                label="Description (Optional)"
                value={editForm.description}
                onChange={(e) => setEditForm((prev) => ({ ...prev, description: e.target.value }))}
                multiline
                rows={2}
                fullWidth
              />
              <TextField
                label="Reason for change"
                value={editForm.reason}
                onChange={(e) => setEditForm((prev) => ({ ...prev, reason: e.target.value }))}
                required
                fullWidth
                helperText="Required for audit trail"
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenEditDialog(false)}>Cancel</Button>
            <Button onClick={handleUpdateAccount} variant="contained" disabled={editSaving}>
              {editSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Layout>
  );
}

export default ChartOfAccounts;

