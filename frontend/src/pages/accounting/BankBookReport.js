import React, { useEffect, useMemo, useState } from 'react';
import {
    Box, Typography, TextField, Button, Grid, Alert,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import ExportButton from '../../components/ExportButton';
import PrintButton from '../../components/PrintButton';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { exportToCSV, exportToExcel, exportToPDF } from '../../utils/export';

const BankBookReport = ({ token, accounts }) => {
    const [selectedAccount, setSelectedAccount] = useState('');
    const [fromDate, setFromDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]);
    const [toDate, setToDate] = useState(new Date().toISOString().split('T')[0]);
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [paymentBankAccounts, setPaymentBankAccounts] = useState([]);

    const safeNumber = (value) => Number(value || 0);
    const safeAmount = (value) => safeNumber(value).toFixed(2);

    useEffect(() => {
        const fetchPaymentBankAccounts = async () => {
            try {
                const response = await fetchWithApiFallback('/api/v1/donations/payment-accounts', {
                    headers: { Authorization: `Bearer ${token}` }
                });
                const data = await response.json();
                const banks = Array.isArray(data?.bank_accounts) ? data.bank_accounts : [];
                setPaymentBankAccounts(
                    banks.map((acc) => ({
                        id: acc?.account_id ?? acc?.id,
                        account_code: String(acc?.account_code || ''),
                        account_name: String(acc?.account_name || ''),
                        cash_bank_nature: 'bank',
                    })).filter((acc) => acc.id !== null && acc.id !== undefined && String(acc.id).trim() !== '')
                );
            } catch (err) {
                console.error('Error fetching payment bank accounts:', err);
                setPaymentBankAccounts([]);
            }
        };

        fetchPaymentBankAccounts();
    }, [token]);

    const bankAccounts = useMemo(() => {
        const list = Array.isArray(accounts) ? accounts : [];
        const fromAccounts = list.filter((acc) => {
            const nature = String(acc?.cash_bank_nature || '').toLowerCase();
            const subtype = String(acc?.account_subtype || '').toLowerCase();
            const code = String(acc?.account_code || '');
            const name = String(acc?.account_name || '').toLowerCase();
            const isBankByNature = nature === 'bank';
            const isBankBySubtype = subtype.includes('bank') && !subtype.includes('cash');
            const isBankByCode = code.startsWith('12');
            const isBankByName = name.includes('bank');
            const isCashByName = name.includes('cash in hand') || name.includes('cash');
            return (isBankByNature || isBankBySubtype || isBankByCode || isBankByName) && !isCashByName;
        });

        const merged = [...fromAccounts, ...paymentBankAccounts];
        const deduped = [];
        const seen = new Set();
        for (const acc of merged) {
            const key = String(acc?.id || '');
            if (!key || seen.has(key)) continue;
            seen.add(key);
            deduped.push(acc);
        }
        return deduped;
    }, [accounts, paymentBankAccounts]);

    useEffect(() => {
        if (!selectedAccount && bankAccounts.length > 0) {
            setSelectedAccount(String(bankAccounts[0].id));
            return;
        }
        if (selectedAccount && !bankAccounts.some((acc) => String(acc.id) === String(selectedAccount))) {
            setSelectedAccount(bankAccounts.length > 0 ? String(bankAccounts[0].id) : '');
        }
    }, [bankAccounts, selectedAccount]);

    const fetchBankBook = async () => {
        if (!selectedAccount) {
            alert('Please select a bank account');
            return;
        }
        setLoading(true);
        try {
            const response = await fetchWithApiFallback(`/api/v1/journal-entries/reports/bank-book/${selectedAccount}?from_date=${fromDate}&to_date=${toDate}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await response.json();
            setReport(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const buildExportRows = () => {
        if (!report) return [];

        const rows = [
            {
                Date: '',
                'Entry #': '',
                Narration: 'Opening Balance',
                'Cheque/Ref': '',
                'Deposit (Rs)': '',
                'Withdrawal (Rs)': '',
                'Balance (Rs)': safeAmount(report.opening_balance)
            }
        ];

        (report.entries || []).forEach((entry) => {
            rows.push({
                Date: entry.date ? new Date(entry.date).toLocaleDateString('en-GB') : '',
                'Entry #': entry.entry_number || '',
                Narration: entry.narration || '',
                'Cheque/Ref': entry.cheque_number || '',
                'Deposit (Rs)': safeNumber(entry.deposit_amount) > 0 ? safeAmount(entry.deposit_amount) : '',
                'Withdrawal (Rs)': safeNumber(entry.withdrawal_amount) > 0 ? safeAmount(entry.withdrawal_amount) : '',
                'Balance (Rs)': safeAmount(entry.running_balance)
            });
        });

        rows.push({
            Date: '',
            'Entry #': '',
            Narration: 'Totals',
            'Cheque/Ref': '',
            'Deposit (Rs)': safeAmount(report.total_deposits),
            'Withdrawal (Rs)': safeAmount(report.total_withdrawals),
            'Balance (Rs)': `Closing: ${safeAmount(report.closing_balance)}`
        });

        return rows;
    };

    const handleExport = (format) => {
        const rows = buildExportRows();
        if (!rows.length) {
            alert('No bank book data to export');
            return;
        }

        const accountCode = report?.account_code || 'bank';
        const filename = `bank_book_${accountCode}_${fromDate}_to_${toDate}`;
        if (format === 'excel') {
            exportToExcel(rows, `${filename}.xlsx`);
            return;
        }
        if (format === 'pdf') {
            exportToPDF(rows, 'Bank Book', { period: { from: fromDate, to: toDate } });
            return;
        }
        exportToCSV(rows, `${filename}.csv`);
    };

    return (
        <Box>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} md={3}>
                    <FormControl fullWidth>
                        <InputLabel>Select Bank Account</InputLabel>
                        <Select
                            value={selectedAccount}
                            onChange={(e) => setSelectedAccount(e.target.value)}
                            label="Select Bank Account"
                        >
                            {bankAccounts.map((account) => (
                                <MenuItem key={account.id} value={String(account.id)}>
                                    {account.account_code} - {account.account_name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Grid>
                <Grid item xs={12} md={3}>
                    <TextField
                        label="From Date"
                        type="date"
                        value={fromDate}
                        onChange={(e) => setFromDate(e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />
                </Grid>
                <Grid item xs={12} md={3}>
                    <TextField
                        label="To Date"
                        type="date"
                        value={toDate}
                        onChange={(e) => setToDate(e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />
                </Grid>
                <Grid item xs={12} md={3}>
                    <Button
                        variant="contained"
                        onClick={fetchBankBook}
                        disabled={loading || !selectedAccount}
                        fullWidth
                        sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                    >
                        {loading ? 'Loading...' : 'Generate Bank Book'}
                    </Button>
                </Grid>
            </Grid>

            {report && (
                <Box id="bank-book-report-content">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
                        <ExportButton onExport={handleExport} filename="bank_book" />
                        <PrintButton
                            elementId="bank-book-report-content"
                            title="Bank Book"
                            reportContext={{ period: { from: fromDate, to: toDate } }}
                        />
                    </Box>

                    <Alert severity="info" sx={{ mb: 2 }}>
                        Bank Book for {report.account_code} - {report.account_name} ({report.bank_name || 'N/A'})
                        <Typography variant="body2" sx={{ mt: 1 }}>Period: {new Date(report.from_date).toLocaleDateString()} to {new Date(report.to_date).toLocaleDateString()}</Typography>
                    </Alert>

                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                    <TableCell>Date</TableCell>
                                    <TableCell>Entry #</TableCell>
                                    <TableCell>Narration</TableCell>
                                    <TableCell>Cheque/Ref No.</TableCell>
                                    <TableCell align="right">Deposit (Rs)</TableCell>
                                    <TableCell align="right">Withdrawal (Rs)</TableCell>
                                    <TableCell align="right">Balance (Rs)</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                                    <TableCell colSpan={6}><strong>Opening Balance</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.opening_balance)}</strong></TableCell>
                                </TableRow>
                                {report.entries && report.entries.length > 0 ? (
                                    report.entries.map((entry, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                                            <TableCell>{entry.entry_number}</TableCell>
                                            <TableCell>
                                                {entry.narration}{' '}
                                                {!entry.cleared && (
                                                    <Box component="span" sx={{ ml: 1, fontSize: '0.7rem', bgcolor: 'warning.light', px: 1, borderRadius: 1 }}>
                                                        Pending
                                                    </Box>
                                                )}
                                            </TableCell>
                                            <TableCell>{entry.cheque_number || '-'}</TableCell>
                                            <TableCell align="right">{entry.deposit_amount > 0 ? entry.deposit_amount.toFixed(2) : '-'}</TableCell>
                                            <TableCell align="right">{entry.withdrawal_amount > 0 ? entry.withdrawal_amount.toFixed(2) : '-'}</TableCell>
                                            <TableCell align="right">{safeAmount(entry.running_balance)}</TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow><TableCell colSpan={7} align="center">No bank transactions in this period</TableCell></TableRow>
                                )}
                                <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                                    <TableCell colSpan={4}><strong>Total</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.total_deposits)}</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.total_withdrawals)}</strong></TableCell>
                                    <TableCell align="right"><strong>Closing: {safeAmount(report.closing_balance)}</strong></TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            )}
        </Box>
    );
};

export default BankBookReport;
