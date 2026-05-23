/* eslint-disable no-irregular-whitespace */
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
    Card,
    CardContent,
    CardActions,
} from '@mui/material';
import Layout from '../../components/Layout';
import LockIcon from '@mui/icons-material/Lock';
import HistoryIcon from '@mui/icons-material/History';
import EventIcon from '@mui/icons-material/Event';
import api from '../../services/api';
import { useNotification } from '../../contexts/NotificationContext';

const FinancialClosing = () => {
    const { showSuccess, showError } = useNotification();
    const [_financialYears, setFinancialYears] = useState([]);
    const [activeYear, setActiveYear] = useState(null);
    const [closings, setClosings] = useState([]);
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState(null);
    const [closingDate, setClosingDate] = useState(new Date().toISOString().split('T')[0]);

    // Initial load happens once on mount; later refreshes are explicit after closing actions.
    useEffect(() => {
        fetchData();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchData = async () => {
        setLoading(true);
        try {
            const [yearsRes, closingsRes] = await Promise.all([
                api.get('/api/v1/financial-closing/financial-years'),
                api.get('/api/v1/financial-closing/period-closings')
            ]);
            setFinancialYears(yearsRes.data);
            setClosings(closingsRes.data);

            const active = yearsRes.data.find(y => y.is_active);
            setActiveYear(active);
            if (active) {
                fetchSummary(active.id);
            }
        } catch (err) {
            showError('Failed to fetch financial data');
        } finally {
            setLoading(false);
        }
    };

    const fetchSummary = async (_yearId) => {
        try {
            // For summary, we need a period. Let's assume current month for now or let user select
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
            const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];

            const response = await api.get(`/api/v1/financial-closing/closing-summary?period_start=${firstDay}&period_end=${lastDay}`);
            setSummary(response.data);
        } catch (err) {
            console.error('Failed to fetch summary');
        }
    };

    const handleCloseMonth = async () => {
        if (!activeYear) return;
        setLoading(true);
        try {
            await api.post('/api/v1/financial-closing/close-month', {
                financial_year_id: activeYear.id,
                closing_date: closingDate,
                notes: 'Month-end closing'
            });
            showSuccess('Month-end closing completed successfully');
            fetchData();
        } catch (err) {
            showError(err.response?.data?.detail || 'Closing failed');
        } finally {
            setLoading(false);
        }
    };

    const handleCloseYear = async () => {
        if (!activeYear) return;
        if (!window.confirm('Are you sure you want to close the entire financial year? This action is irreversible.')) return;

        setLoading(true);
        try {
            await api.post('/api/v1/financial-closing/close-year', {
                financial_year_id: activeYear.id,
                closing_date: activeYear.end_date,
                notes: 'Year-end closing'
            });
            showSuccess('Financial year closed successfully');
            fetchData();
        } catch (err) {
            showError(err.response?.data?.detail || 'Year-end closing failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <Box sx={{ p: 3 }}>
                <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
                    Financial Closing
                </Typography>

                <Grid container spacing={3} sx={{ mt: 2 }}>
                    {/* Active Year Status */}
                    <Grid item xs={12} md={4}>
                        <Card sx={{ height: '100%' }}>
                            <CardContent>
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                    <EventIcon color="primary" sx={{ mr: 1 }} />
                                    <Typography variant="h6">Current Financial Year</Typography>
                                </Box>
                                {activeYear ? (
                                    <Box>
                                        <Typography variant="h4" color="primary" gutterBottom>{activeYear.year_code}</Typography>
                                        <Typography variant="body2" color="textSecondary">
                                            Period: {new Date(activeYear.start_date).toLocaleDateString()} to {new Date(activeYear.end_date).toLocaleDateString()}
                                        </Typography>
                                        <Chip
                                            label="ACTIVE"
                                            color="success"
                                            size="small"
                                            sx={{ mt: 2, fontWeight: 'bold' }}
                                        />
                                    </Box>
                                ) : (
                                    <Typography color="error">No active financial year found</Typography>
                                )}
                            </CardContent>
                            <CardActions sx={{ p: 2 }}>
                                <Button
                                    variant="outlined"
                                    fullWidth
                                    startIcon={<LockIcon />}
                                    color="error"
                                    onClick={handleCloseYear}
                                    disabled={!activeYear || loading}
                                >
                                    Close Financial Year
                                </Button>
                            </CardActions>
                        </Card>
                    </Grid>

                    {/* Month End Action */}
                    <Grid item xs={12} md={8}>
                        <Paper sx={{ p: 3, height: '100%' }}>
                            <Typography variant="h6" gutterBottom>Month-End Closing Workflow</Typography>
                            <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
                                Closing a month locks all transactions for that period and transfers the net surplus/deficit to the General Fund.
                            </Typography>

                            <Grid container spacing={2} alignItems="center">
                                <Grid item xs={12} md={6}>
                                    <TextField
                                        label="Closing Date"
                                        type="date"
                                        value={closingDate}
                                        onChange={(e) => setClosingDate(e.target.value)}
                                        fullWidth
                                        InputLabelProps={{ shrink: true }}
                                        helperText="Typically the last day of the month"
                                    />
                                </Grid>
                                <Grid item xs={12} md={6}>
                                    <Button
                                        variant="contained"
                                        color="primary"
                                        size="large"
                                        fullWidth
                                        onClick={handleCloseMonth}
                                        disabled={loading || !activeYear}
                                        startIcon={<LockIcon />}
                                        sx={{ height: 56 }}
                                    >
                                        Perform Month Closing
                                    </Button>
                                </Grid>
                            </Grid>

                            {summary && (
                                <Box sx={{ mt: 4, p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
                                    <Typography variant="subtitle2" gutterBottom>Unclosed Period Estimates</Typography>
                                    <Grid container spacing={2} sx={{ mt: 1 }}>
                                        <Grid item xs={4}>
                                            <Typography variant="caption" color="textSecondary">Total Income</Typography>
                                            <Typography variant="body1" fontWeight="bold">Rs {summary.total_income.toLocaleString()}</Typography>
                                        </Grid>
                                        <Grid item xs={4}>
                                            <Typography variant="caption" color="textSecondary">Total Expenses</Typography>
                                            <Typography variant="body1" fontWeight="bold">Rs {summary.total_expenses.toLocaleString()}</Typography>
                                        </Grid>
                                        <Grid item xs={4}>
                                            <Typography variant="caption" color="textSecondary">Net Surplus</Typography>
                                            <Typography variant="body1" fontWeight="bold" color="success.main">Rs {summary.net_surplus.toLocaleString()}</Typography>
                                        </Grid>
                                    </Grid>
                                </Box>
                            )}
                        </Paper>
                    </Grid>

                    {/* Closing History */}
                    <Grid item xs={12}>
                        <Typography variant="h6" sx={{ mt: 2, mb: 2, display: 'flex', alignItems: 'center' }}>
                            <HistoryIcon sx={{ mr: 1 }} /> Closing History
                        </Typography>
                        <TableContainer component={Paper}>
                            <Table>
                                <TableHead>
                                    <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                        <TableCell>Type</TableCell>
                                        <TableCell>Period End</TableCell>
                                        <TableCell align="right">Income</TableCell>
                                        <TableCell align="right">Expenses</TableCell>
                                        <TableCell align="right">Surplus/Deficit</TableCell>
                                        <TableCell>Completed At</TableCell>
                                        <TableCell>Status</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {closings.map((closing) => (
                                        <TableRow key={closing.id}>
                                            <TableCell>
                                                <Chip
                                                    label={closing.closing_type === 'year_end' ? 'YEAR' : 'MONTH'}
                                                    size="small"
                                                    color={closing.closing_type === 'year_end' ? 'secondary' : 'default'}
                                                />
                                            </TableCell>
                                            <TableCell>{new Date(closing.closing_date).toLocaleDateString()}</TableCell>
                                            <TableCell align="right">Rs {closing.total_income.toLocaleString()}</TableCell>
                                            <TableCell align="right">Rs {closing.total_expenses.toLocaleString()}</TableCell>
                                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                                                Rs {closing.net_surplus.toLocaleString()}
                                            </TableCell>
                                            <TableCell>{new Date(closing.completed_at).toLocaleString()}</TableCell>
                                            <TableCell>
                                                <Chip label="COMPLETED" color="success" size="small" variant="outlined" />
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {closings.length === 0 && (
                                        <TableRow>
                                            <TableCell colSpan={7} align="center">No closing records found</TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Grid>
                </Grid>
            </Box>
        </Layout>
    );
};

export default FinancialClosing;
