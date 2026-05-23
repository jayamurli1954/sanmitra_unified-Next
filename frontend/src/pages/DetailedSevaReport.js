import React, { useState, useEffect } from 'react';
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
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
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
import { useNotification } from '../contexts/NotificationContext';

const getSevaRows = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.sevas)) return data.sevas;
  if (Array.isArray(data?.items)) return data.items;
  return [];
};

function DetailedSevaReport() {
  const navigate = useNavigate();
  const { showSuccess, showError } = useNotification();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fromDate, setFromDate] = useState(new Date());
  const [toDate, setToDate] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState('');
  const [reportData, setReportData] = useState(null);
  const sevaRows = getSevaRows(reportData);
  const totalCount = reportData?.total_count ?? sevaRows.length;
  const completedCount = reportData?.completed_count ?? sevaRows.filter((seva) => seva.status === 'Completed').length;
  const pendingCount = reportData?.pending_count ?? sevaRows.filter((seva) => seva.status === 'Pending').length;
  const totalAmount = reportData?.total_amount ?? sevaRows.reduce((sum, seva) => sum + (Number(seva?.amount) || 0), 0);
  const [rescheduleDialog, setRescheduleDialog] = useState({ open: false, booking: null });
  const [newDate, setNewDate] = useState(null);
  const [rescheduleReason, setRescheduleReason] = useState('');

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError('');

      const params = {
        from_date: fromDate.toISOString().split('T')[0],
        to_date: toDate.toISOString().split('T')[0],
      };

      if (statusFilter) params.status = statusFilter;

      const response = await api.get('/api/v1/reports/sevas/detailed', { params });

      setReportData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load report');
      console.error('Report error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial report load should happen once on mount; later refreshes are user-driven.
  useEffect(() => {
    fetchReport();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleReschedule = (booking) => {
    setRescheduleDialog({ open: true, booking });
    setNewDate(new Date(booking.seva_date));
    setRescheduleReason('');
  };

  const submitReschedule = async () => {
    try {
      await api.put(`/api/v1/sevas/bookings/${rescheduleDialog.booking.id}/reschedule`, null, {
        params: {
          new_date: newDate.toISOString().split('T')[0],
          reason: rescheduleReason,
        }
      });

      showSuccess('Reschedule request submitted. Waiting for admin approval.');
      setRescheduleDialog({ open: false, booking: null });
      fetchReport();
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to submit reschedule request');
    }
  };

  const handleDownloadReceipt = async (bookingId, receiptNumber) => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/sevas/bookings/${bookingId}/receipt/pdf`, {
        responseType: 'blob',
        params: { lang: 'kannada' },
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `seva_receipt_${receiptNumber || bookingId}.pdf`);
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

    const exportData = sevaRows.map(s => ({
      'Receipt Date': new Date(s.receipt_date || s.seva_date).toLocaleDateString(),
      'Seva Date': new Date(s.seva_date || s.booking_date).toLocaleDateString(),
      'Receipt Number': s.receipt_number,
      'Seva Name': s.seva_name,
      'Devotee Name': s.devotee_name,
      'Mobile': s.devotee_mobile || 'N/A',
      'Amount (INR)': s.amount,
      'Status': s.status,
    }));

    if (format === 'csv') {
      exportToCSV(exportData, `detailed-seva-${fromDate.toISOString().split('T')[0]}`);
    } else if (format === 'excel') {
      exportToExcel(exportData, `Detailed Seva Report`);
    } else if (format === 'pdf') {
      exportToPDF(exportData, 'Detailed Seva Report', {
        period: {
          from: fromDate.toLocaleDateString('en-GB'),
          to: toDate.toLocaleDateString('en-GB'),
        },
      });
    }
  };

  const getStatusColor = (status) => {
    if (status === 'Completed') return 'success';
    if (status === 'Pending') return 'warning';
    return 'default';
  };

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
            Detailed Seva Report
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
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  label="Status"
                >
                  <MenuItem value="">All Status</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                variant="contained"
                fullWidth
                onClick={fetchReport}
                disabled={loading}
                sx={{ height: '40px' }}
              >
                {loading ? <CircularProgress size={20} /> : 'Generate Report'}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {/* Report Table */}
        {reportData && (
          <Paper id="detailed-seva-report-content" sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Total: {totalCount} sevas |
                Completed: {completedCount} |
                Pending: {pendingCount} |
                Amount: Rs {new Intl.NumberFormat('en-IN').format(totalAmount)}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <ExportButton onExport={handleExport} />
                <PrintButton
                  elementId="detailed-seva-report-content"
                  title="Detailed Seva Report"
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
                    <TableCell><strong>Receipt Date</strong></TableCell>
                    <TableCell><strong>Seva Date</strong></TableCell>
                    <TableCell><strong>Receipt #</strong></TableCell>
                    <TableCell><strong>Seva Name</strong></TableCell>
                    <TableCell><strong>Devotee Name</strong></TableCell>
                    <TableCell><strong>Mobile</strong></TableCell>
                    <TableCell align="right"><strong>Amount (INR)</strong></TableCell>
                    <TableCell><strong>Status</strong></TableCell>
                    <TableCell><strong>Action</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sevaRows.map((seva) => (
                    <TableRow key={seva.id}>
                      <TableCell>{new Date(seva.receipt_date || seva.seva_date).toLocaleDateString()}</TableCell>
                      <TableCell>{new Date(seva.seva_date || seva.booking_date).toLocaleDateString()}</TableCell>
                      <TableCell>{seva.receipt_number}</TableCell>
                      <TableCell>{seva.seva_name}</TableCell>
                      <TableCell>{seva.devotee_name}</TableCell>
                      <TableCell>{seva.phone || seva.devotee_phone || seva.mobile || 'N/A'}</TableCell>
                      <TableCell align="right">
                        {new Intl.NumberFormat('en-IN', {
                          style: 'currency',
                          currency: 'INR',
                          maximumFractionDigits: 0,
                        }).format(seva.amount)}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={seva.status}
                          color={getStatusColor(seva.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          {seva.status === 'Pending' && (
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleReschedule(seva)}
                            >
                              Reschedule
                            </Button>
                          )}
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => handleDownloadReceipt(seva.id, seva.receipt_number)}
                            title="Download Receipt"
                          >
                            <PictureAsPdfIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* Reschedule Dialog */}
        <Dialog open={rescheduleDialog.open} onClose={() => setRescheduleDialog({ open: false, booking: null })}>
          <DialogTitle>Reschedule Seva</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Current Date: {rescheduleDialog.booking && new Date(rescheduleDialog.booking.seva_date).toLocaleDateString()}
              </Typography>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="New Date"
                  value={newDate}
                  onChange={(newValue) => setNewDate(newValue)}
                  renderInput={(params) => <TextField {...params} fullWidth sx={{ mb: 2 }} />}
                />
              </LocalizationProvider>
              <TextField
                fullWidth
                label="Reason for Reschedule"
                multiline
                rows={3}
                value={rescheduleReason}
                onChange={(e) => setRescheduleReason(e.target.value)}
                required
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setRescheduleDialog({ open: false, booking: null })}>Cancel</Button>
            <Button
              variant="contained"
              onClick={submitReschedule}
              disabled={!newDate || !rescheduleReason}
            >
              Submit Request
            </Button>
          </DialogActions>
        </Dialog>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}
      </Box>
    </Layout>
  );
}

export default DetailedSevaReport;

