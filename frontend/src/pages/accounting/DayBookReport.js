import React, { useState } from 'react';
import {
    Box, Typography, TextField, Button, Grid, Alert,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow
} from '@mui/material';
import ExportButton from '../../components/ExportButton';
import PrintButton from '../../components/PrintButton';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { exportToCSV, exportToExcel, exportToPDF } from '../../utils/export';

const DayBookReport = ({ token }) => {
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);

    const safeNumber = (value) => Number(value || 0);
    const safeAmount = (value) => safeNumber(value).toFixed(2);

    const fetchDayBook = async () => {
        setLoading(true);
        try {
            const response = await fetchWithApiFallback(`/api/v1/journal-entries/reports/day-book?date=${date}`, {
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
                Section: 'Summary',
                'Entry #': '',
                Account: '',
                Narration: 'Opening Balance',
                Amount: safeAmount(report.opening_balance)
            }
        ];

        (report.receipts || []).forEach((item) => {
            rows.push({
                Section: 'Receipt',
                'Entry #': item.entry_number || '',
                Account: item.account_name || '',
                Narration: item.narration || '',
                Amount: safeAmount(item.debit_amount)
            });
        });

        rows.push({
            Section: 'Summary',
            'Entry #': '',
            Account: '',
            Narration: 'Total Receipts',
            Amount: safeAmount(report.total_receipts)
        });

        (report.payments || []).forEach((item) => {
            rows.push({
                Section: 'Payment',
                'Entry #': item.entry_number || '',
                Account: item.account_name || '',
                Narration: item.narration || '',
                Amount: safeAmount(item.credit_amount)
            });
        });

        rows.push({
            Section: 'Summary',
            'Entry #': '',
            Account: '',
            Narration: 'Total Payments',
            Amount: safeAmount(report.total_payments)
        });

        rows.push({
            Section: 'Summary',
            'Entry #': '',
            Account: '',
            Narration: 'Closing Balance',
            Amount: safeAmount(report.closing_balance)
        });

        return rows;
    };

    const handleExport = (format) => {
        const rows = buildExportRows();
        if (!rows.length) {
            alert('No day book data to export');
            return;
        }

        const filename = `day_book_${date}`;
        if (format === 'excel') {
            exportToExcel(rows, `${filename}.xlsx`);
            return;
        }
        if (format === 'pdf') {
            exportToPDF(rows, 'Day Book', { period: date });
            return;
        }
        exportToCSV(rows, `${filename}.csv`);
    };

    return (
        <Box>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} md={4}>
                    <TextField
                        label="Date"
                        type="date"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />
                </Grid>
                <Grid item xs={12} md={4}>
                    <Button
                        variant="contained"
                        onClick={fetchDayBook}
                        disabled={loading}
                        sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                    >
                        {loading ? 'Loading...' : 'Generate Day Book'}
                    </Button>
                </Grid>
            </Grid>

            {report && (
                <Box id="day-book-report-content">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
                        <ExportButton onExport={handleExport} filename="day_book" />
                        <PrintButton
                            elementId="day-book-report-content"
                            title="Day Book"
                            reportContext={{ period: date }}
                        />
                    </Box>

                    <Alert severity="info" sx={{ mb: 2 }}>
                        Day Book for {new Date(report.date).toLocaleDateString()}
                        <Typography variant="body2" sx={{ mt: 1 }}>Opening Balance: Rs {safeAmount(report.opening_balance)}</Typography>
                        <Typography variant="body2">Closing Balance: Rs {safeAmount(report.closing_balance)}</Typography>
                    </Alert>

                    <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Receipts (Cash IN)</Typography>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                    <TableCell>Entry #</TableCell>
                                    <TableCell>Account</TableCell>
                                    <TableCell>Narration</TableCell>
                                    <TableCell align="right">Amount (Rs)</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {report.receipts && report.receipts.length > 0 ? (
                                    report.receipts.map((r, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{r.entry_number}</TableCell>
                                            <TableCell>{r.account_name}</TableCell>
                                            <TableCell>{r.narration}</TableCell>
                                            <TableCell align="right">{safeAmount(r.debit_amount)}</TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow><TableCell colSpan={4} align="center">No receipts</TableCell></TableRow>
                                )}
                                <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                                    <TableCell colSpan={3}><strong>Total Receipts</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.total_receipts)}</strong></TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </TableContainer>

                    <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>Payments (Cash OUT)</Typography>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                    <TableCell>Entry #</TableCell>
                                    <TableCell>Account</TableCell>
                                    <TableCell>Narration</TableCell>
                                    <TableCell align="right">Amount (Rs)</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {report.payments && report.payments.length > 0 ? (
                                    report.payments.map((p, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{p.entry_number}</TableCell>
                                            <TableCell>{p.account_name}</TableCell>
                                            <TableCell>{p.narration}</TableCell>
                                            <TableCell align="right">{safeAmount(p.credit_amount)}</TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow><TableCell colSpan={4} align="center">No payments</TableCell></TableRow>
                                )}
                                <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                                    <TableCell colSpan={3}><strong>Total Payments</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.total_payments)}</strong></TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            )}
        </Box>
    );
};

export default DayBookReport;
