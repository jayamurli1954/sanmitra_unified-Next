import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Collapse,
  Button,
  TextField,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Snackbar,
  Tooltip,
  Autocomplete,
} from '@mui/material';
import Layout from '../../components/Layout';
import ReceiptIcon from '@mui/icons-material/Receipt';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import MinimizeIcon from '@mui/icons-material/Minimize';
import { useCurrentUser } from '../../contexts/CurrentUserContext';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { getAccessToken } from '../../utils/authStorage';
import { ACTIVE_TEMPLE_EVENT } from '../../utils/activeTemple';

function JournalEntryRow({
  entry,
  onEdit,
  onPost,
  onReverse,
  postingEntryId,
  reversingEntryId,
  canReverseEntries,
}) {
  const [open, setOpen] = useState(false);

  const getStatusColor = (status) => {
    switch (String(status).toLowerCase()) {
      case 'posted':
        return 'success';
      case 'draft':
        return 'warning';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>{entry.entry_number}</TableCell>
        <TableCell>{new Date(entry.entry_date).toLocaleDateString()}</TableCell>
        <TableCell>{entry.narration}</TableCell>
        <TableCell align="right">Rs {entry.total_amount.toFixed(2)}</TableCell>
        <TableCell>
          <Chip label={entry.status} color={getStatusColor(entry.status)} size="small" />
        </TableCell>
        <TableCell>{entry.reference_type || '-'}</TableCell>
        <TableCell align="center">
          {String(entry.status).toLowerCase() === 'draft' ? (
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
              <Button size="small" variant="outlined" onClick={() => onEdit(entry)}>
                Edit
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="warning"
                onClick={() => onPost(entry)}
                disabled={postingEntryId === entry.id}
              >
                {postingEntryId === entry.id ? 'Posting...' : 'Post'}
              </Button>
            </Box>
          ) : String(entry.status).toLowerCase() === 'posted' && canReverseEntries ? (
            <Button
              size="small"
              variant="outlined"
              color="error"
              onClick={() => onReverse(entry)}
              disabled={reversingEntryId === entry.id}
            >
              {reversingEntryId === entry.id ? 'Reversing...' : 'Reverse'}
            </Button>
          ) : (
            <Typography variant="body2" color="text.secondary">-</Typography>
          )}
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={8}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2 }}>
              <Typography variant="h6" gutterBottom>
                Journal Lines
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Account</strong></TableCell>
                    <TableCell><strong>Description</strong></TableCell>
                    <TableCell align="right"><strong>Debit (Rs)</strong></TableCell>
                    <TableCell align="right"><strong>Credit (Rs)</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {entry.journal_lines.map((line, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        {line.account_code} - {line.account_name}
                      </TableCell>
                      <TableCell>{line.description}</TableCell>
                      <TableCell align="right">
                        {line.debit_amount > 0 ? line.debit_amount.toFixed(2) : '-'}
                      </TableCell>
                      <TableCell align="right">
                        {line.credit_amount > 0 ? line.credit_amount.toFixed(2) : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                    <TableCell colSpan={2}><strong>TOTAL</strong></TableCell>
                    <TableCell align="right">
                      <strong>
                        Rs {entry.journal_lines.reduce((sum, line) => sum + line.debit_amount, 0).toFixed(2)}
                      </strong>
                    </TableCell>
                    <TableCell align="right">
                      <strong>
                        Rs {entry.journal_lines.reduce((sum, line) => sum + line.credit_amount, 0).toFixed(2)}
                      </strong>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

function JournalEntries() {
  const { user, loading: currentUserLoading } = useCurrentUser();
  const canReverseEntries = !currentUserLoading && (
    Boolean(user?.action_permissions?.reverse_accounting_entries)
    || ['admin', 'super_admin'].includes(user?.role)
    || Boolean(user?.is_superuser)
  );
  const [entries, setEntries] = useState([]);
  const [fromDate, setFromDate] = useState(new Date(new Date().getFullYear(), 3, 1)); // April 1st
  const [toDate, setToDate] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogMinimized, setDialogMinimized] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [postingEntryId, setPostingEntryId] = useState(null);
  const [reversingEntryId, setReversingEntryId] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Form state
  const [entryDate, setEntryDate] = useState(new Date().toISOString().split('T')[0]);
  const [narration, setNarration] = useState('');
  const [referenceType, setReferenceType] = useState('EXPENSE');
  const [referenceNumber, setReferenceNumber] = useState('');
  const [journalLines, setJournalLines] = useState([
    { account_id: '', debit_amount: '', credit_amount: '', description: '' },
    { account_id: '', debit_amount: '', credit_amount: '', description: '' },
  ]);

  const getAccountId = (account) => String(account?.account_id ?? account?.id ?? '');

  const getAccountLabel = (account) => {
    if (!account) return '';

    const code = String(account.account_code ?? account.code ?? account.accountCode ?? getAccountId(account)).trim();
    const name = String(account.account_name ?? account.name ?? '').trim();
    const type = String(account.account_type ?? account.type ?? '').trim();

    return `${code}${name ? ` - ${name}` : ''}${type ? ` (${type})` : ''}`;
  };

  const findAccountById = (accountId) => (
    accounts.find((account) => getAccountId(account) === String(accountId || '')) || null
  );

  const normalizeAccounts = (raw) => {
    const accountRows = Array.isArray(raw)
      ? raw
      : (Array.isArray(raw?.accounts) ? raw.accounts : (Array.isArray(raw?.data) ? raw.data : []));

    const flattenAccounts = (items, result = []) => {
      items.forEach((account) => {
        const id = account?.account_id ?? account?.id ?? null;
        result.push({
          ...account,
          id,
          account_id: id,
          account_code: account?.account_code ?? account?.code ?? account?.accountCode ?? '',
          account_name: account?.account_name ?? account?.name ?? account?.accountName ?? '',
          account_type: account?.account_type ?? account?.type ?? '',
          account_subtype: account?.account_subtype ?? account?.subtype ?? '',
        });

        if (Array.isArray(account?.sub_accounts) && account.sub_accounts.length > 0) {
          flattenAccounts(account.sub_accounts, result);
        }
      });
      return result;
    };

    return flattenAccounts(accountRows)
      .filter((account) => account.id !== null && account.id !== undefined && String(account.id).trim() !== '');
  };

  const isNumericAccountId = (value) => /^[0-9]+$/.test(String(value ?? '').trim());

  const fetchAccountsFromTrialBalance = async (token) => {
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
    return normalizeAccounts(Array.isArray(data?.accounts) ? data.accounts : []);
  };

  // Initial data load happens once on mount; later refreshes are explicit from filters/actions.
  useEffect(() => {
    fetchEntries();
    fetchAccounts();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handleActiveTempleChange = () => {
      fetchAccounts();
    };

    window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
    return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchEntries = async () => {
    setLoading(true);
    try {
      const token = getAccessToken();
      const fromDateStr = fromDate.toISOString().split('T')[0];
      const toDateStr = toDate.toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/journal-entries/?from_date=${fromDateStr}&to_date=${toDateStr}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      setEntries(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching journal entries:', error);
      setEntries([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAccounts = async () => {
    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/accounts/`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      let normalized = normalizeAccounts(data);

      // Journal entries must post against numeric SQL ledger IDs.
      if (normalized.length === 0 || !normalized.some((account) => isNumericAccountId(account.id))) {
        try {
          const trialBalanceAccounts = await fetchAccountsFromTrialBalance(token);
          if (trialBalanceAccounts.length > 0) {
            normalized = trialBalanceAccounts;
          }
        } catch (trialBalanceError) {
          console.warn('Trial balance fallback for journal account list failed:', trialBalanceError);
        }
      }

      setAccounts(normalized);
    } catch (error) {
      console.error('Error fetching accounts:', error);
      setAccounts([]);
    }
  };

  const handleAddLine = () => {
    setJournalLines([...journalLines, { account_id: '', debit_amount: '', credit_amount: '', description: '' }]);
  };

  const handleRemoveLine = (index) => {
    if (journalLines.length > 2) {
      const newLines = journalLines.filter((_, i) => i !== index);
      setJournalLines(newLines);
    }
  };

  const handleLineChange = (index, field, value) => {
    const newLines = [...journalLines];
    newLines[index][field] = value;
    setJournalLines(newLines);
  };

  const calculateTotals = () => {
    const totalDebit = journalLines.reduce((sum, line) => sum + (parseFloat(line.debit_amount) || 0), 0);
    const totalCredit = journalLines.reduce((sum, line) => sum + (parseFloat(line.credit_amount) || 0), 0);
    return { totalDebit, totalCredit };
  };

  const handleSaveEntry = async () => {
    try {
      const { totalDebit, totalCredit } = calculateTotals();
      if (totalDebit !== totalCredit) {
        setSnackbar({ open: true, message: 'Total debits must equal total credits!', severity: 'error' });
        return;
      }

      if (totalDebit === 0) {
        setSnackbar({ open: true, message: 'Entry cannot have zero amount!', severity: 'error' });
        return;
      }

      const token = getAccessToken();
      const payload = {
        entry_date: entryDate,
        narration,
        reference_type: referenceType,
        reference_id: referenceNumber ? Number(referenceNumber) : undefined,
        journal_lines: journalLines.map(line => ({
          account_id: parseInt(line.account_id),
          debit_amount: parseFloat(line.debit_amount) || 0,
          credit_amount: parseFloat(line.credit_amount) || 0,
          description: line.description,
        })),
      };

      const response = await fetchWithApiFallback(
        editingEntryId
          ? `/api/v1/journal-entries/${editingEntryId}`
          : `/api/v1/journal-entries/`,
        {
          method: editingEntryId ? 'PUT' : 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      );

      if (response.ok) {
        setSnackbar({
          open: true,
          message: editingEntryId
            ? 'Journal entry updated successfully!'
            : 'Journal entry created successfully!',
          severity: 'success',
        });
        handleCloseCreateDialog();
        resetForm();
        fetchEntries();
      } else {
        const error = await response.json();
        setSnackbar({ open: true, message: error.detail || 'Failed to save entry', severity: 'error' });
      }
    } catch (error) {
      console.error('Error saving journal entry:', error);
      setSnackbar({ open: true, message: 'Error saving journal entry', severity: 'error' });
    }
  };

  const handlePostEntry = async (entry) => {
    try {
      setPostingEntryId(entry.id);
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/journal-entries/${entry.id}/post`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setSnackbar({ open: true, message: `Entry #${entry.entry_number} posted successfully.`, severity: 'success' });
        fetchEntries();
      } else {
        const error = await response.json();
        setSnackbar({ open: true, message: error.detail || 'Failed to post entry', severity: 'error' });
      }
    } catch (error) {
      console.error('Error posting journal entry:', error);
      setSnackbar({ open: true, message: 'Error posting journal entry', severity: 'error' });
    } finally {
      setPostingEntryId(null);
    }
  };

  const handleReverseEntry = async (entry) => {
    const reason = window.prompt(`Enter reversal reason for ${entry.entry_number}:`, 'Correction entry');
    if (!reason || !reason.trim()) {
      return;
    }

    try {
      setReversingEntryId(entry.id);
      const token = getAccessToken();
      const response = await fetchWithApiFallback(`/api/v1/journal-entries/${entry.id}/cancel`, {
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
          message: `Entry #${entry.entry_number} reversed. Reversal entry created automatically.`,
          severity: 'success',
        });
        fetchEntries();
      } else {
        const error = await response.json();
        setSnackbar({ open: true, message: error.detail || 'Failed to reverse entry', severity: 'error' });
      }
    } catch (error) {
      console.error('Error reversing journal entry:', error);
      setSnackbar({ open: true, message: 'Error reversing journal entry', severity: 'error' });
    } finally {
      setReversingEntryId(null);
    }
  };

  const handleOpenNewEntry = () => {
    setEditingEntryId(null);
    resetForm();
    handleRestoreCreateDialog();
  };

  const handleEditEntry = (entry) => {
    if (String(entry.status).toLowerCase() !== 'draft') {
      setSnackbar({ open: true, message: 'Only draft entries can be edited.', severity: 'warning' });
      return;
    }

    setEditingEntryId(entry.id);
    setEntryDate(String(entry.entry_date || '').split('T')[0] || new Date().toISOString().split('T')[0]);
    setNarration(entry.narration || '');
    setReferenceType((entry.reference_type || 'EXPENSE').toUpperCase());
    setReferenceNumber(entry.reference_id ? String(entry.reference_id) : '');
    setJournalLines(
      (entry.journal_lines || []).length > 0
        ? entry.journal_lines.map((line) => ({
            account_id: line.account_id ? String(line.account_id) : '',
            debit_amount: line.debit_amount || '',
            credit_amount: line.credit_amount || '',
            description: line.description || '',
          }))
        : [
            { account_id: '', debit_amount: '', credit_amount: '', description: '' },
            { account_id: '', debit_amount: '', credit_amount: '', description: '' },
          ]
    );
    handleRestoreCreateDialog();
  };

  const resetForm = () => {
    setEditingEntryId(null);
    setEntryDate(new Date().toISOString().split('T')[0]);
    setNarration('');
    setReferenceType('EXPENSE');
    setReferenceNumber('');
    setJournalLines([
      { account_id: '', debit_amount: '', credit_amount: '', description: '' },
      { account_id: '', debit_amount: '', credit_amount: '', description: '' },
    ]);
  };

  const handleCloseCreateDialog = () => {
    setOpenDialog(false);
    setDialogMinimized(false);
    resetForm();
  };

  const handleMinimizeCreateDialog = () => {
    setOpenDialog(false);
    setDialogMinimized(true);
  };

  const handleRestoreCreateDialog = () => {
    setOpenDialog(true);
    setDialogMinimized(false);
  };

  const handleCreateDialogRequestClose = (_event, reason) => {
    if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
      handleMinimizeCreateDialog();
      return;
    }
    handleCloseCreateDialog();
  };

  const { totalDebit, totalCredit } = calculateTotals();

  return (
    <Layout>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <ReceiptIcon sx={{ fontSize: 40, mr: 2, color: '#FF9933' }} />
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
              Journal Entries
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenNewEntry}
            sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
          >
            Create Entry
          </Button>
        </Box>

        {/* Filters */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
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
                onClick={fetchEntries}
                disabled={loading}
                fullWidth
                sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
              >
                {loading ? 'Loading...' : 'Filter'}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {/* Entries Table */}
        <Paper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#FF9933' }}>
                  <TableCell sx={{ color: 'white', width: 50 }}></TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Entry #</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Date</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Narration</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="right">Amount</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Status</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Type</TableCell>
                  <TableCell sx={{ color: 'white', fontWeight: 'bold' }} align="center">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      <Typography>Loading journal entries...</Typography>
                    </TableCell>
                  </TableRow>
                ) : entries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      <Typography color="text.secondary">No journal entries found for this period</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  entries.map((entry) => (
                    <JournalEntryRow
                      key={entry.id}
                      entry={entry}
                      onEdit={handleEditEntry}
                      onPost={handlePostEntry}
                      onReverse={handleReverseEntry}
                      postingEntryId={postingEntryId}
                      reversingEntryId={reversingEntryId}
                      canReverseEntries={canReverseEntries}
                    />
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>

        {/* Create Entry Dialog */}
        <Dialog open={openDialog} onClose={handleCreateDialogRequestClose} maxWidth="md" fullWidth>
          <DialogTitle sx={{ pr: 7, position: 'relative' }}>
            <Tooltip title="Minimize">
              <IconButton
                aria-label="minimize journal entry dialog"
                onClick={handleMinimizeCreateDialog}
                size="small"
                sx={{ position: 'absolute', right: 12, top: 12 }}
              >
                <MinimizeIcon />
              </IconButton>
            </Tooltip>
            {editingEntryId ? 'Edit Journal Entry' : 'Create Journal Entry'}
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Entry Date"
                  type="date"
                  value={entryDate}
                  onChange={(e) => setEntryDate(e.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Reference Type</InputLabel>
                  <Select
                    value={referenceType}
                    onChange={(e) => setReferenceType(e.target.value)}
                    label="Reference Type"
                  >
                    <MenuItem value="EXPENSE">Expense</MenuItem>
                    <MenuItem value="INCOME">Income</MenuItem>
                    <MenuItem value="TRANSFER">Transfer</MenuItem>
                    <MenuItem value="ADJUSTMENT">Adjustment</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Narration"
                  value={narration}
                  onChange={(e) => setNarration(e.target.value)}
                  fullWidth
                  required
                  multiline
                  rows={2}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Reference Number (Optional)"
                  value={referenceNumber}
                  onChange={(e) => setReferenceNumber(e.target.value)}
                  fullWidth
                />
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>Journal Lines</Typography>
                {journalLines.map((line, index) => (
                  <Paper key={index} sx={{ p: 2, mb: 2, bgcolor: '#f5f5f5' }}>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <Autocomplete
                          fullWidth
                          size="small"
                          options={accounts}
                          openOnFocus
                          value={findAccountById(line.account_id)}
                          onChange={(_event, account) => (
                            handleLineChange(index, 'account_id', account ? getAccountId(account) : '')
                          )}
                          getOptionLabel={getAccountLabel}
                          isOptionEqualToValue={(option, value) => getAccountId(option) === getAccountId(value)}
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              label="Account"
                              placeholder="Search account code or name"
                              required
                            />
                          )}
                          noOptionsText={accounts.length ? 'No matching account' : 'No accounts loaded'}
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          label="Debit Amount"
                          type="number"
                          value={line.debit_amount}
                          onChange={(e) => handleLineChange(index, 'debit_amount', e.target.value)}
                          fullWidth
                          size="small"
                          inputProps={{ step: '0.01', min: '0' }}
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          label="Credit Amount"
                          type="number"
                          value={line.credit_amount}
                          onChange={(e) => handleLineChange(index, 'credit_amount', e.target.value)}
                          fullWidth
                          size="small"
                          inputProps={{ step: '0.01', min: '0' }}
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <IconButton
                          color="error"
                          onClick={() => handleRemoveLine(index)}
                          disabled={journalLines.length <= 2}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Grid>
                      <Grid item xs={12}>
                        <TextField
                          label="Description"
                          value={line.description}
                          onChange={(e) => handleLineChange(index, 'description', e.target.value)}
                          fullWidth
                          size="small"
                        />
                      </Grid>
                    </Grid>
                  </Paper>
                ))}

                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={handleAddLine}
                  sx={{ mb: 2 }}
                >
                  Add Line
                </Button>

                <Box sx={{ bgcolor: '#fff3e0', p: 2, borderRadius: 1 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2">Total Debit: Rs {totalDebit.toFixed(2)}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">Total Credit: Rs {totalCredit.toFixed(2)}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography
                        variant="body2"
                        color={totalDebit === totalCredit && totalDebit > 0 ? 'success.main' : 'error.main'}
                      >
                        {totalDebit === totalCredit && totalDebit > 0
                          ? 'Entry is balanced'
                          : 'Entry must be balanced (debits = credits)'}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseCreateDialog}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleSaveEntry}
              disabled={totalDebit !== totalCredit || totalDebit === 0}
              sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
            >
              {editingEntryId ? 'Update Entry' : 'Create Entry'}
            </Button>
          </DialogActions>
        </Dialog>

        {dialogMinimized && (
          <Box
            sx={{
              position: 'fixed',
              right: 24,
              bottom: 24,
              zIndex: (theme) => theme.zIndex.modal + 1,
            }}
          >
            <Button variant="contained" color="warning" onClick={handleRestoreCreateDialog}>
              Resume Journal Entry
            </Button>
          </Box>
        )}

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

export default JournalEntries;
