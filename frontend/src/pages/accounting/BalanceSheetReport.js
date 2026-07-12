import React, { useMemo, useState } from 'react';
import {
    Box, Typography, TextField, Button, Grid, Alert,
    Table, TableBody, TableCell, TableContainer, TableRow, Paper
} from '@mui/material';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';

const BalanceSheetReport = ({ token }) => {
    const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0]);
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const safeNumber = (value) => Number(value || 0);
    const formatAmount = (value) => safeNumber(value).toFixed(2);
    const formatDisplayDate = (value) => {
        if (!value) return asOfDate;
        const parsed = new Date(value);
        return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString('en-IN');
    };

    const fetchBalanceSheet = async () => {
        setLoading(true);
        setError('');
        try {
            const response = await fetchWithApiFallback(`/api/v1/journal-entries/reports/balance-sheet?as_of=${asOfDate}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data?.detail || `Balance Sheet request failed with HTTP ${response.status}`);
            }
            setReport(data);
        } catch (err) {
            console.error(err);
            setReport(null);
            setError(err?.message || 'Unable to generate Balance Sheet. Please retry or check backend status.');
        } finally {
            setLoading(false);
        }
    };

    const normalizedReport = useMemo(() => {
        if (!report) return null;

        const groupedRows = (rows = [], fallbackGroupName) => {
            if (!Array.isArray(rows) || rows.length === 0) return [];
            if (rows.some((row) => Array.isArray(row?.accounts))) {
                return rows.map((group) => ({
                    group_name: group.group_name || group.name || fallbackGroupName,
                    group_total: safeNumber(group.group_total ?? group.total),
                    accounts: Array.isArray(group.accounts) ? group.accounts : [],
                }));
            }
            return [{
                group_name: fallbackGroupName,
                group_total: rows.reduce((sum, account) => sum + safeNumber(account.balance ?? account.current_year), 0),
                accounts: rows,
            }];
        };

        const liabilities = [
            ...groupedRows(report.designated_funds, 'Designated Funds'),
            ...groupedRows(report.current_liabilities, 'Current Liabilities'),
            ...groupedRows(report.liabilities, 'Liabilities'),
        ];
        const equity = groupedRows(report.equity, 'Funds / Equity');
        const assets = [
            ...groupedRows(report.fixed_assets, 'Fixed Assets'),
            ...groupedRows(report.current_assets, 'Current Assets'),
            ...groupedRows(report.assets, 'Assets'),
        ];
        const totalAssets = safeNumber(report.total_assets);
        const totalLiabilities = safeNumber(report.total_liabilities);
        const totalEquity = safeNumber(report.total_equity ?? report.corpus_fund);
        const totalLiabilitiesAndFunds = safeNumber(report.total_liabilities_and_funds || (totalLiabilities + totalEquity));
        const difference = safeNumber(report.difference ?? (totalAssets - totalLiabilitiesAndFunds));
        const balanced = typeof report.balanced === 'boolean'
            ? report.balanced
            : (typeof report.is_balanced === 'boolean' ? report.is_balanced : Math.abs(difference) < 0.01);

        return {
            asOf: report.as_of || report.as_of_date || asOfDate,
            balanced,
            difference,
            equity,
            liabilities,
            assets,
            totalAssets,
            totalLiabilitiesAndFunds,
        };
    }, [asOfDate, report]);

    const renderGroup = (group) => (
        <Box key={group.group_name} sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, pl: 1 }}>{group.group_name}</Typography>
            <TableContainer>
                <Table size="small">
                    <TableBody>
                        {group.accounts.map((acc, i) => (
                            <TableRow key={`${group.group_name}-${acc.account_code || acc.account_id || i}`}>
                                <TableCell sx={{ borderBottom: 'none' }}>
                                    {acc.account_code ? `${acc.account_code} - ` : ''}{acc.account_name || acc.name || 'Account'}
                                </TableCell>
                                <TableCell align="right" sx={{ borderBottom: 'none' }}>₹{formatAmount(acc.current_year ?? acc.balance)}</TableCell>
                            </TableRow>
                        ))}
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                            <TableCell><strong>{group.group_name} Total</strong></TableCell>
                            <TableCell align="right"><strong>₹{formatAmount(group.group_total)}</strong></TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );

    return (
        <Box>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} md={4}>
                    <TextField
                        label="As Of Date"
                        type="date"
                        value={asOfDate}
                        onChange={(e) => setAsOfDate(e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />
                </Grid>
                <Grid item xs={12} md={4}>
                    <Button
                        variant="contained"
                        onClick={fetchBalanceSheet}
                        disabled={loading}
                        sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                    >
                        {loading ? 'Loading...' : 'Generate Balance Sheet'}
                    </Button>
                </Grid>
            </Grid>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            {normalizedReport && (
                <Box>
                    <Alert severity={normalizedReport.balanced ? "success" : "error"} sx={{ mb: 2 }}>
                        Balance Sheet as of {formatDisplayDate(normalizedReport.asOf)}
                        {!normalizedReport.balanced && ` - WARNING: Not Balanced! Difference: ₹${formatAmount(normalizedReport.difference)}`}
                    </Alert>

                    <Grid container spacing={4}>
                        <Grid item xs={12} md={6}>
                            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                <Typography variant="h6" sx={{ bgcolor: '#FFF3E0', p: 1, textAlign: 'center', mb: 2 }}>
                                    FUNDS & LIABILITIES
                                </Typography>

                                <Box sx={{ flexGrow: 1 }}>
                                    {normalizedReport.equity.map(group => renderGroup(group))}
                                    {normalizedReport.liabilities.map(group => renderGroup(group))}
                                </Box>

                                <Box sx={{ mt: 'auto', bgcolor: '#FF9933', color: 'white', p: 1.5, display: 'flex', justifyContent: 'space-between' }}>
                                    <Typography variant="h6"><strong>Total</strong></Typography>
                                    <Typography variant="h6"><strong>₹{formatAmount(normalizedReport.totalLiabilitiesAndFunds)}</strong></Typography>
                                </Box>
                            </Paper>
                        </Grid>

                        <Grid item xs={12} md={6}>
                            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                <Typography variant="h6" sx={{ bgcolor: '#FFF3E0', p: 1, textAlign: 'center', mb: 2 }}>
                                    ASSETS
                                </Typography>

                                <Box sx={{ flexGrow: 1 }}>
                                    {normalizedReport.assets.map(group => renderGroup(group))}
                                </Box>

                                <Box sx={{ mt: 'auto', bgcolor: '#FF9933', color: 'white', p: 1.5, display: 'flex', justifyContent: 'space-between' }}>
                                    <Typography variant="h6"><strong>Total</strong></Typography>
                                    <Typography variant="h6"><strong>₹{formatAmount(normalizedReport.totalAssets)}</strong></Typography>
                                </Box>
                            </Paper>
                        </Grid>
                    </Grid>
                </Box>
            )}
        </Box>
    );
};

export default BalanceSheetReport;
