import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Paper,
    Grid,
    Button,
    TextField,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    CircularProgress,
    Stepper,
    Step,
    StepLabel,
    Autocomplete,
} from '@mui/material';
import Layout from '../../components/Layout';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import api from '../../services/api';
import { useNotification } from '../../contexts/NotificationContext';
import { ACTIVE_TEMPLE_EVENT } from '../../utils/activeTemple';

const BankReconciliation = () => {
    const { showSuccess, showError } = useNotification();
    const [activeStep, setActiveStep] = useState(0);
    const [bankAccounts, setBankAccounts] = useState([]);
    const [selectedAccount, setSelectedAccount] = useState('');
    const [file, setFile] = useState(null);
    const [statementDate, setStatementDate] = useState(new Date().toISOString().split('T')[0]);
    const [loading, setLoading] = useState(false);
    const [statement, setStatement] = useState(null);
    const [summary, setSummary] = useState(null);
    const [statementEntries, setStatementEntries] = useState([]);
    const [bookEntries, setBookEntries] = useState([]);
    const [matchingItem, setMatchingItem] = useState(null); // Current statement entry being matched

    const getAccountId = (account) => String(account?.account_id ?? account?.id ?? '');

    const getAccountLabel = (account) => {
        if (!account) return '';

        const code = String(account.code ?? account.account_code ?? account.accountCode ?? getAccountId(account)).trim();
        const name = String(account.name ?? account.account_name ?? '').trim();
        const type = String(account.type ?? account.account_type ?? '').trim();

        return `${code}${name ? ` - ${name}` : ''}${type ? ` (${type})` : ''}`;
    };

    const findBankAccountById = (accountId) => (
        bankAccounts.find((account) => getAccountId(account) === String(accountId || '')) || null
    );

    const normalizeAccounts = (raw) => {
        const rows = Array.isArray(raw)
            ? raw
            : (Array.isArray(raw?.accounts) ? raw.accounts : (Array.isArray(raw?.data) ? raw.data : []));

        return rows
            .map((account) => {
                const id = account?.account_id ?? account?.id ?? null;
                return {
                    ...account,
                    id,
                    account_id: id,
                    code: account?.code ?? account?.account_code ?? account?.accountCode ?? '',
                    name: account?.name ?? account?.account_name ?? account?.accountName ?? '',
                    type: account?.type ?? account?.account_type ?? '',
                    account_code: account?.account_code ?? account?.code ?? account?.accountCode ?? '',
                    account_name: account?.account_name ?? account?.name ?? account?.accountName ?? '',
                    account_type: account?.account_type ?? account?.type ?? '',
                    cash_bank_nature: account?.cash_bank_nature ?? account?.cashBankNature ?? '',
                    is_cash_bank: Boolean(account?.is_cash_bank ?? account?.isCashBank),
                };
            })
            .filter((account) => account.id !== null && account.id !== undefined && String(account.id).trim() !== '');
    };

    const isBankAccount = (account) => {
        const nature = String(account?.cash_bank_nature || '').toLowerCase();
        const name = String(account?.name || account?.account_name || '').toLowerCase();
        const code = String(account?.code || account?.account_code || '').trim();
        return nature === 'bank' || code === '12001' || (Boolean(account?.is_cash_bank) && name.includes('bank'));
    };

    const fetchAccountsFallback = async () => {
        const accountsResponse = await api.get('/api/v1/accounts/');
        let normalized = normalizeAccounts(accountsResponse.data).filter(isBankAccount);

        if (normalized.length === 0) {
            const trialBalanceResponse = await api.get(
                `/api/v1/journal-entries/reports/trial-balance?as_of=${statementDate}`
            );
            normalized = normalizeAccounts(trialBalanceResponse.data?.accounts || []).filter(isBankAccount);
        }

        return normalized;
    };

    // Bank accounts are loaded once on mount; other refreshes are explicit.
    useEffect(() => {
        fetchBankAccounts();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        const handleActiveTempleChange = () => {
            fetchBankAccounts();
        };

        window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
        return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChange);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchBankAccounts = async () => {
        try {
            const response = await api.get('/api/v1/bank-reconciliation/accounts');
            let normalizedAccounts = normalizeAccounts(response.data);

            if (normalizedAccounts.length === 0) {
                normalizedAccounts = await fetchAccountsFallback();
            }

            setBankAccounts(normalizedAccounts);
        } catch (err) {
            try {
                setBankAccounts(await fetchAccountsFallback());
            } catch (fallbackErr) {
                showError('Failed to fetch bank accounts');
            }
        }
    };

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleImport = async () => {
        if (!selectedAccount || !file || !statementDate) {
            showError('Please select account, date and file');
            return;
        }

        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post(
                `/api/v1/bank-reconciliation/statements/import?account_id=${selectedAccount}&statement_date=${statementDate}`,
                formData,
                {
                    headers: { 'Content-Type': 'multipart/form-data' },
                }
            );

            setStatement(response.data);
            showSuccess('Bank statement imported successfully');
            fetchReconciliationData(response.data.id);
            setActiveStep(1);
        } catch (err) {
            showError(err.response?.data?.detail || 'Failed to import statement');
        } finally {
            setLoading(false);
        }
    };

    const fetchReconciliationData = async (statementId) => {
        setLoading(true);
        try {
            const [summaryRes, entriesRes, bookRes] = await Promise.all([
                api.get(`/api/v1/bank-reconciliation/statements/${statementId}/summary`),
                api.get(`/api/v1/bank-reconciliation/statements/${statementId}/entries`),
                api.get(`/api/v1/bank-reconciliation/statements/${statementId}/unmatched-book-entries`)
            ]);

            setSummary(summaryRes.data);
            setStatementEntries(entriesRes.data);
            setBookEntries(bookRes.data);
        } catch (err) {
            showError('Failed to fetch reconciliation details');
        } finally {
            setLoading(false);
        }
    };

    const handleMatch = async (statementEntryId, journalLineId) => {
        try {
            await api.post('/api/v1/bank-reconciliation/match', {
                statement_entry_id: statementEntryId,
                journal_line_id: journalLineId
            });
            showSuccess('Entry matched successfully');
            setMatchingItem(null);
            fetchReconciliationData(statement.id);
        } catch (err) {
            showError(err.response?.data?.detail || 'Matching failed');
        }
    };

    const handleFinalReconcile = async () => {
        setLoading(true);
        try {
            await api.post('/api/v1/bank-reconciliation/reconcile', {
                account_id: selectedAccount,
                statement_id: statement.id,
                reconciliation_date: statementDate,
                notes: 'Final reconciliation'
            });
            showSuccess('Bank reconciliation completed successfully');
            setActiveStep(2);
        } catch (err) {
            showError(err.response?.data?.detail || 'Reconciliation failed');
        } finally {
            setLoading(false);
        }
    };

    const renderStep0 = () => (
        <Paper sx={{ p: 4, maxWidth: 600, mx: 'auto', mt: 4 }}>
            <Typography variant="h6" gutterBottom>Import Bank Statement</Typography>
            <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <Autocomplete
                    fullWidth
                    options={bankAccounts}
                    openOnFocus
                    value={findBankAccountById(selectedAccount)}
                    onChange={(_event, account) => setSelectedAccount(account ? getAccountId(account) : '')}
                    getOptionLabel={getAccountLabel}
                    isOptionEqualToValue={(option, value) => getAccountId(option) === getAccountId(value)}
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            label="Bank Account"
                            placeholder="Search bank account code or name"
                            required
                        />
                    )}
                    noOptionsText={bankAccounts.length ? 'No matching bank account' : 'No bank accounts loaded'}
                />

                <TextField
                    label="Statement Date"
                    type="date"
                    value={statementDate}
                    onChange={(e) => setStatementDate(e.target.value)}
                    fullWidth
                    InputLabelProps={{ shrink: true }}
                />

                <Box sx={{ border: '2px dashed #ccc', p: 3, textAlign: 'center', borderRadius: 2 }}>
                    <input
                        accept=".csv"
                        style={{ display: 'none' }}
                        id="raised-button-file"
                        type="file"
                        onChange={handleFileChange}
                    />
                    <label htmlFor="raised-button-file">
                        <Button variant="outlined" component="span" startIcon={<CloudUploadIcon />} sx={{ mb: 1 }}>
                            Select CSV File
                        </Button>
                    </label>
                    <Typography variant="body2" color="textSecondary">
                        {file ? file.name : 'Expected format: Date, Description, Debit, Credit, Balance'}
                    </Typography>
                </Box>

                <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    onClick={handleImport}
                    disabled={loading || !file || !selectedAccount}
                    sx={{ py: 1.5 }}
                >
                    {loading ? <CircularProgress size={24} color="inherit" /> : 'Import & Continue'}
                </Button>
            </Box>
        </Paper>
    );

    const renderStep1 = () => (
        <Box sx={{ mt: 3 }}>
            {summary && (
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={3}>
                        <Paper sx={{ p: 2, textAlign: 'center', bgcolor: '#e3f2fd' }}>
                            <Typography variant="caption" color="textSecondary">Statement Balance</Typography>
                            <Typography variant="h6">{'\u20B9'}{summary.statement_balance?.toLocaleString()}</Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Paper sx={{ p: 2, textAlign: 'center', bgcolor: '#fff3e0' }}>
                            <Typography variant="caption" color="textSecondary">Book Balance</Typography>
                            <Typography variant="h6">{'\u20B9'}{summary.book_balance?.toLocaleString()}</Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Paper sx={{ p: 2, textAlign: 'center', bgcolor: summary.difference === 0 ? '#e8f5e9' : '#ffebee' }}>
                            <Typography variant="caption" color="textSecondary">Difference</Typography>
                            <Typography variant="h6">{'\u20B9'}{summary.difference?.toLocaleString()}</Typography>
                        </Paper>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Box sx={{ display: 'flex', gap: 1, height: '100%', alignItems: 'center' }}>
                            <Button
                                variant="contained"
                                color="success"
                                fullWidth
                                onClick={handleFinalReconcile}
                                disabled={summary.difference !== 0 || loading}
                                startIcon={<CheckCircleIcon />}
                            >
                                Finalize
                            </Button>
                        </Box>
                    </Grid>
                </Grid>
            )}

            <Grid container spacing={2}>
                {/* Bank Statement Side */}
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 0 }}>
                        <Box sx={{ p: 2, bgcolor: '#f5f5f5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="subtitle1" fontWeight="bold">Bank Statement Entries</Typography>
                            <Chip label={`Unmatched: ${statementEntries.filter(e => !e.is_matched).length}`} size="small" color="primary" />
                        </Box>
                        <TableContainer sx={{ maxHeight: 500 }}>
                            <Table stickyHeader size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell>Date</TableCell>
                                        <TableCell>Description</TableCell>
                                        <TableCell align="right">Amount</TableCell>
                                        <TableCell align="center">Action</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {statementEntries.map((entry) => (
                                        <TableRow key={entry.id} sx={{ bgcolor: entry.is_matched ? '#e8f5e9' : 'inherit' }}>
                                            <TableCell>{new Date(entry.transaction_date).toLocaleDateString()}</TableCell>
                                            <TableCell sx={{ fontSize: '0.8rem' }}>{entry.description}</TableCell>
                                            <TableCell align="right" sx={{ color: entry.amount >= 0 ? 'success.main' : 'error.main' }}>
                                                {'\u20B9'}{Math.abs(entry.amount).toLocaleString()}
                                            </TableCell>
                                            <TableCell align="center">
                                                {entry.is_matched ? (
                                                    <CheckCircleIcon color="success" fontSize="small" />
                                                ) : (
                                                    <Button
                                                        size="small"
                                                        variant={matchingItem?.id === entry.id ? "contained" : "outlined"}
                                                        onClick={() => setMatchingItem(entry)}
                                                    >
                                                        Match
                                                    </Button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Paper>
                </Grid>

                {/* Book Entries Side */}
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 0 }}>
                        <Box sx={{ p: 2, bgcolor: '#f5f5f5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="subtitle1" fontWeight="bold">Book Entries (Journal Lines)</Typography>
                            {matchingItem && (
                                <Chip
                                    label={`Matching: \u20B9${Math.abs(matchingItem.amount).toLocaleString()}`}
                                    color="warning"
                                    onDelete={() => setMatchingItem(null)}
                                    size="small"
                                />
                            )}
                        </Box>
                        <TableContainer sx={{ maxHeight: 500 }}>
                            <Table stickyHeader size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell>Date</TableCell>
                                        <TableCell>Narration</TableCell>
                                        <TableCell align="right">Amount</TableCell>
                                        <TableCell align="center">Action</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {bookEntries.map((line) => (
                                        <TableRow key={line.id}>
                                            <TableCell>{new Date(line.entry_date).toLocaleDateString()}</TableCell>
                                            <TableCell sx={{ fontSize: '0.8rem' }}>{line.narration}</TableCell>
                                            <TableCell align="right">{'\u20B9'}{line.amount.toLocaleString()}</TableCell>
                                            <TableCell align="center">
                                                <Button
                                                    size="small"
                                                    variant="contained"
                                                    color="secondary"
                                                    disabled={!matchingItem || Math.abs(Math.abs(matchingItem.amount) - line.amount) > 0.01}
                                                    onClick={() => handleMatch(matchingItem.id, line.id)}
                                                >
                                                    Select
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );

    const renderStep2 = () => (
        <Paper sx={{ p: 6, textAlign: 'center', mt: 4 }}>
            <CheckCircleIcon sx={{ fontSize: 100, color: 'success.main', mb: 2 }} />
            <Typography variant="h4" gutterBottom>Success!</Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
                The bank account has been reconciled with the statement.
                A reconciliation record has been created for your audits.
            </Typography>
            <Button variant="contained" onClick={() => setActiveStep(0)}>Next Statement</Button>
        </Paper>
    );

    return (
        <Layout>
            <Box sx={{ p: 3 }}>
                <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
                    Bank Reconciliation
                </Typography>

                <Stepper activeStep={activeStep} sx={{ mb: 4, mt: 3 }}>
                    <Step><StepLabel>Import Statement</StepLabel></Step>
                    <Step><StepLabel>Match Transactions</StepLabel></Step>
                    <Step><StepLabel>Complete</StepLabel></Step>
                </Stepper>

                {activeStep === 0 && renderStep0()}
                {activeStep === 1 && renderStep1()}
                {activeStep === 2 && renderStep2()}
            </Box>
        </Layout>
    );
};

export default BankReconciliation;
