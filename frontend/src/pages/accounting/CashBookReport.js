import React, { useState } from 'react';
import {
    Box, TextField, Button, Grid, Alert,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow
} from '@mui/material';
import ExportButton from '../../components/ExportButton';
import PrintButton from '../../components/PrintButton';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { exportToCSV, exportToExcel, exportToPDF } from '../../utils/export';

const CashBookReport = ({ token }) => {
    const [fromDate, setFromDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]);
    const [toDate, setToDate] = useState(new Date().toISOString().split('T')[0]);
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);

    const safeNumber = (value) => Number(value || 0);
    const safeAmount = (value) => safeNumber(value).toFixed(2);

    const fetchCashBook = async () => {
        setLoading(true);
        try {
            const response = await fetchWithApiFallback(`/api/v1/journal-entries/reports/cash-book?from_date=${fromDate}&to_date=${toDate}`, {
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
                'Receipt (Rs)': '',
                'Payment (Rs)': '',
                'Balance (Rs)': safeAmount(report.opening_balance)
            }
        ];

        (report.entries || []).forEach((entry) => {
            rows.push({
                Date: entry.date ? new Date(entry.date).toLocaleDateString('en-GB') : '',
                'Entry #': entry.entry_number || '',
                Narration: entry.narration || '',
                'Receipt (Rs)': safeNumber(entry.receipt_amount) > 0 ? safeAmount(entry.receipt_amount) : '',
                'Payment (Rs)': safeNumber(entry.payment_amount) > 0 ? safeAmount(entry.payment_amount) : '',
                'Balance (Rs)': safeAmount(entry.running_balance)
            });
        });

        rows.push({
            Date: '',
            'Entry #': '',
            Narration: 'Totals',
            'Receipt (Rs)': safeAmount(report.total_receipts),
            'Payment (Rs)': safeAmount(report.total_payments),
            'Balance (Rs)': `Closing: ${safeAmount(report.closing_balance)}`
        });

        return rows;
    };

    const handleExport = (format) => {
        const rows = buildExportRows();
        if (!rows.length) {
            alert('No cash book data to export');
            return;
        }

        const filename = `cash_book_${fromDate}_to_${toDate}`;
        if (format === 'excel') {
            exportToExcel(rows, `${filename}.xlsx`);
            return;
        }
        if (format === 'pdf') {
            exportToPDF(rows, 'Cash Book', { period: { from: fromDate, to: toDate } });
            return;
        }
        exportToCSV(rows, `${filename}.csv`);
    };

    return (
        <Box>
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} md={4}>
                    <TextField
                        label="From Date"
                        type="date"
                        value={fromDate}
                        onChange={(e) => setFromDate(e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />
                </Grid>
                <Grid item xs={12} md={4}>
                    <TextField
                        label="To Date"
                        type="date"
                        value={toDate}
                        onChange={(e) => setToDate(e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />
                </Grid>
                <Grid item xs={12} md={4}>
                    <Button
                        variant="contained"
                        onClick={fetchCashBook}
                        disabled={loading}
                        fullWidth
                        sx={{ height: 56, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                    >
                        {loading ? 'Loading...' : 'Generate Cash Book'}
                    </Button>
                </Grid>
            </Grid>

            {report && (
                <Box id="cash-book-report-content">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
                        <ExportButton onExport={handleExport} filename="cash_book" />
                        <PrintButton
                            elementId="cash-book-report-content"
                            title="Cash Book"
                            reportContext={{ period: { from: fromDate, to: toDate } }}
                        />
                    </Box>

                    <Alert severity="info" sx={{ mb: 2 }}>
                        Cash Book from {new Date(report.from_date).toLocaleDateString()} to {new Date(report.to_date).toLocaleDateString()}
                    </Alert>

                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                    <TableCell>Date</TableCell>
                                    <TableCell>Entry #</TableCell>
                                    <TableCell>Narration</TableCell>
                                    <TableCell align="right">Receipt (Rs)</TableCell>
                                    <TableCell align="right">Payment (Rs)</TableCell>
                                    <TableCell align="right">Balance (Rs)</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                                    <TableCell colSpan={5}><strong>Opening Balance</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.opening_balance)}</strong></TableCell>
                                </TableRow>
                                {report.entries && report.entries.length > 0 ? (
                                    report.entries.map((entry, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{new Date(entry.date).toLocaleDateString()}</TableCell>
                                            <TableCell>{entry.entry_number}</TableCell>
                                            <TableCell>{entry.narration}</TableCell>
                                            <TableCell align="right">{entry.receipt_amount > 0 ? entry.receipt_amount.toFixed(2) : '-'}</TableCell>
                                            <TableCell align="right">{entry.payment_amount > 0 ? entry.payment_amount.toFixed(2) : '-'}</TableCell>
                                            <TableCell align="right">{safeAmount(entry.running_balance)}</TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow><TableCell colSpan={6} align="center">No cash transactions in this period</TableCell></TableRow>
                                )}
                                <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                                    <TableCell colSpan={3}><strong>Total</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.total_receipts)}</strong></TableCell>
                                    <TableCell align="right"><strong>{safeAmount(report.total_payments)}</strong></TableCell>
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

export default CashBookReport;
