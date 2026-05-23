import React, { useState } from 'react';
import {
    Box, Typography, TextField, Button, Grid, Alert,
    Table, TableBody, TableCell, TableContainer, TableRow, Paper
} from '@mui/material';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';

const BalanceSheetReport = ({ token }) => {
    const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0]);
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);

    const fetchBalanceSheet = async () => {
        setLoading(true);
        try {
            const response = await fetchWithApiFallback(`/api/v1/journal-entries/reports/balance-sheet?as_of_date=${asOfDate}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            setReport(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const renderGroup = (group) => (
        <Box key={group.group_name} sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, pl: 1 }}>{group.group_name}</Typography>
            <TableContainer>
                <Table size="small">
                    <TableBody>
                        {group.accounts && group.accounts.map((acc, i) => (
                            <TableRow key={i}>
                                <TableCell sx={{ borderBottom: 'none' }}>{acc.account_name}</TableCell>
                                <TableCell align="right" sx={{ borderBottom: 'none' }}>â‚¹{acc.current_year.toFixed(2)}</TableCell>
                            </TableRow>
                        ))}
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                            <TableCell><strong>{group.group_name} Total</strong></TableCell>
                            <TableCell align="right"><strong>â‚¹{group.group_total.toFixed(2)}</strong></TableCell>
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

            {report && (
                <Box>
                    <Alert severity={report.is_balanced ? "success" : "error"} sx={{ mb: 2 }}>
                        Balance Sheet as of {new Date(report.as_of_date).toLocaleDateString()}
                        {!report.is_balanced && ` - WARNING: Not Balanced! Difference: â‚¹${report.difference.toFixed(2)}`}
                    </Alert>

                    <Grid container spacing={4}>
                        {/* Liabilities Side */}
                        <Grid item xs={12} md={6}>
                            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                <Typography variant="h6" sx={{ bgcolor: '#FFF3E0', p: 1, textAlign: 'center', mb: 2 }}>
                                    FUNDS & LIABILITIES
                                </Typography>

                                <Box sx={{ flexGrow: 1 }}>
                                    <Box sx={{ mb: 2 }}>
                                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, pl: 1 }}>Corpus/Capital Fund</Typography>
                                        <TableContainer>
                                            <Table size="small">
                                                <TableBody>
                                                    <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                                        <TableCell><strong>Corpus Fund Total</strong></TableCell>
                                                        <TableCell align="right"><strong>â‚¹{(report.corpus_fund || 0).toFixed(2)}</strong></TableCell>
                                                    </TableRow>
                                                </TableBody>
                                            </Table>
                                        </TableContainer>
                                    </Box>

                                    {(report.designated_funds || []).map(group => renderGroup(group))}
                                    {(report.current_liabilities || []).map(group => renderGroup(group))}
                                </Box>

                                <Box sx={{ mt: 'auto', bgcolor: '#FF9933', color: 'white', p: 1.5, display: 'flex', justifyContent: 'space-between' }}>
                                    <Typography variant="h6"><strong>Total</strong></Typography>
                                    <Typography variant="h6"><strong>â‚¹{(report.total_liabilities_and_funds || 0).toFixed(2)}</strong></Typography>
                                </Box>
                            </Paper>
                        </Grid>

                        {/* Assets Side */}
                        <Grid item xs={12} md={6}>
                            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                <Typography variant="h6" sx={{ bgcolor: '#FFF3E0', p: 1, textAlign: 'center', mb: 2 }}>
                                    ASSETS
                                </Typography>

                                <Box sx={{ flexGrow: 1 }}>
                                    {(report.fixed_assets || []).map(group => renderGroup(group))}
                                    {(report.current_assets || []).map(group => renderGroup(group))}
                                </Box>

                                <Box sx={{ mt: 'auto', bgcolor: '#FF9933', color: 'white', p: 1.5, display: 'flex', justifyContent: 'space-between' }}>
                                    <Typography variant="h6"><strong>Total</strong></Typography>
                                    <Typography variant="h6"><strong>â‚¹{(report.total_assets || 0).toFixed(2)}</strong></Typography>
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
