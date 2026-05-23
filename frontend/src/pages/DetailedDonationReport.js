import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import IconButton from '@mui/material/IconButton';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../services/api';
import ExportButton from '../components/ExportButton';
import PrintButton from '../components/PrintButton';
import { exportToCSV, exportToExcel, exportToPDF } from '../utils/export';

const getDonationRows = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.donations)) return data.donations;
  if (Array.isArray(data?.items)) return data.items;
  return [];
};

function DetailedDonationReport() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fromDate, setFromDate] = useState(new Date());
  const [toDate, setToDate] = useState(new Date());
  const [categoryFilter, setCategoryFilter] = useState('');
  const [paymentModeFilter, setPaymentModeFilter] = useState('');
  const [categories, setCategories] = useState([]);
  const [reportData, setReportData] = useState(null);
  const donationRows = getDonationRows(reportData);
  const totalCount = reportData?.total_count ?? donationRows.length;
  const totalAmount = reportData?.total_amount ?? donationRows.reduce((sum, donation) => sum + (Number(donation?.amount) || 0), 0);

  const fetchCategories = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/donations/categories/');
      setCategories(response.data.map(cat => cat.name));
    } catch (err) {
      console.error('Failed to load categories');
    }
  }, []);

  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      const params = {
        from_date: fromDate.toISOString().split('T')[0],
        to_date: toDate.toISOString().split('T')[0],
      };

      if (categoryFilter) params.category = categoryFilter;
      if (paymentModeFilter) params.payment_mode = paymentModeFilter;

      const response = await api.get('/api/v1/reports/donations/detailed', { params });

      setReportData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load report');
      console.error('Report error:', err);
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, categoryFilter, paymentModeFilter]);

  useEffect(() => {
    fetchCategories();
    fetchReport();
  }, [fetchCategories, fetchReport]);

  const handleDownloadReceipt = async (donationId, receiptNumber) => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/donations/${donationId}/receipt/pdf`, {
        responseType: 'blob',
        params: { lang: 'kannada' },
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `receipt_${receiptNumber || donationId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading receipt:', err);
      setError('Failed to download receipt');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (format) => {
    if (!reportData) return;

    const exportData = donationRows.map(d => ({
      'Date': new Date(d.date).toLocaleDateString(),
      'Receipt Number': d.receipt_number,
      'Devotee Name': d.devotee_name,
      'Mobile': d.phone || d.devotee_phone || d.mobile || 'N/A',
      'Category': d.category,
      'Payment Mode': d.payment_mode,
      'Amount (₹)': d.amount,
    }));

    if (format === 'csv') {
      exportToCSV(exportData, `detailed-donation-${fromDate.toISOString().split('T')[0]}`);
    } else if (format === 'excel') {
      exportToExcel(exportData, `Detailed Donation Report`);
    } else if (format === 'pdf') {
      exportToPDF(exportData, 'Detailed Donation Report', {
        period: {
          from: fromDate.toLocaleDateString('en-GB'),
          to: toDate.toLocaleDateString('en-GB'),
        },
      });
    }
  };

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
            Detailed Donation Report
          </Typography>
          <Button variant="outlined" onClick={() => navigate('/reports')}>
            Back to Reports
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Filters */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="From Date"
                  value={fromDate}
                  onChange={(newValue) => setFromDate(newValue)}
                  renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12} sm={3}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="To Date"
                  value={toDate}
                  onChange={(newValue) => setToDate(newValue)}
                  renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Category</InputLabel>
                <Select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  label="Category"
                >
                  <MenuItem value="">All Categories</MenuItem>
                  {categories.map(cat => (
                    <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Payment Mode</InputLabel>
                <Select
                  value={paymentModeFilter}
                  onChange={(e) => setPaymentModeFilter(e.target.value)}
                  label="Payment Mode"
                >
                  <MenuItem value="">All Modes</MenuItem>
                  <MenuItem value="Cash">Cash</MenuItem>
                  <MenuItem value="UPI">UPI</MenuItem>
                  <MenuItem value="Card">Card</MenuItem>
                  <MenuItem value="Online">Online</MenuItem>
                  <MenuItem value="Cheque">Cheque</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Button
                variant="contained"
                onClick={fetchReport}
                disabled={loading}
                sx={{ minWidth: 200 }}
              >
                {loading ? <CircularProgress size={20} /> : 'Generate Report'}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {/* Report Table */}
        {reportData && (
          <Paper id="detailed-donation-report-content" sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Total: {totalCount} donations |
                Amount: ₹{new Intl.NumberFormat('en-IN').format(totalAmount)}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <ExportButton onExport={handleExport} />
                <PrintButton
                  elementId="detailed-donation-report-content"
                  title="Detailed Donation Report"
                  reportContext={{
                    period: {
                      from: fromDate.toLocaleDateString('en-GB'),
                      to: toDate.toLocaleDateString('en-GB'),
                    },
                  }}
                />
              </Box>
            </Box>

            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Date</strong></TableCell>
                    <TableCell><strong>Receipt #</strong></TableCell>
                    <TableCell><strong>Devotee Name</strong></TableCell>
                    <TableCell><strong>Mobile</strong></TableCell>
                    <TableCell><strong>Category</strong></TableCell>
                    <TableCell><strong>Payment Mode</strong></TableCell>
                    <TableCell align="right"><strong>Amount (₹)</strong></TableCell>
                    <TableCell align="right"><strong>Action</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {donationRows.map((donation) => (
                    <TableRow key={donation.id}>
                      <TableCell>{new Date(donation.date).toLocaleDateString()}</TableCell>
                      <TableCell>{donation.receipt_number}</TableCell>
                      <TableCell>{donation.devotee_name}</TableCell>
                      <TableCell>{donation.phone || donation.devotee_phone || donation.mobile || 'N/A'}</TableCell>
                      <TableCell>{donation.category}</TableCell>
                      <TableCell>{donation.payment_mode}</TableCell>
                      <TableCell align="right">
                        {new Intl.NumberFormat('en-IN', {
                          style: 'currency',
                          currency: 'INR',
                          maximumFractionDigits: 0,
                        }).format(donation.amount)}
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          color="primary"
                          size="small"
                          onClick={() => handleDownloadReceipt(donation.id, donation.receipt_number)}
                          title="Download Receipt"
                        >
                          <PictureAsPdfIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}
      </Box>
    </Layout>
  );
}

export default DetailedDonationReport;
