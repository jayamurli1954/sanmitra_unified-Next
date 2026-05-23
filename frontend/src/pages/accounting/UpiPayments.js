import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Snackbar,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import Layout from '../../components/Layout';
import PaymentIcon from '@mui/icons-material/Payment';
import QrCodeIcon from '@mui/icons-material/QrCode';
import ReceiptIcon from '@mui/icons-material/Receipt';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { getAccessToken } from '../../utils/authStorage';

function UpiPayments() {
  const [_devotees, setDevotees] = useState([]);
  const [payments, setPayments] = useState([]);
  const [formData, setFormData] = useState({
    devotee_phone: '',
    amount: '',
    sender_upi_id: '',
    upi_reference_number: '',
    payment_purpose: 'DONATION',
    notes: '',
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [receiptDialog, setReceiptDialog] = useState({ open: false, data: null });
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [loading, setLoading] = useState(false);

  // Payments reload intentionally follows the selected date; devotee prefetch is not needed here.
  useEffect(() => {
    fetchDevotees();
    fetchPayments();
  }, [selectedDate]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchDevotees = async () => {
    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback('/api/v1/devotees/', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const data = await response.json();
      setDevotees(data);
    } catch (error) {
      console.error('Error fetching devotees:', error);
    }
  };

  const fetchPayments = async () => {
    try {
      const token = getAccessToken();
      const dateStr = selectedDate.toISOString().split('T')[0];
      const response = await fetchWithApiFallback(
        `/api/v1/upi-payments/?from_date=${dateStr}&to_date=${dateStr}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      const normalizedPayments = Array.isArray(data)
        ? data
        : Array.isArray(data?.items)
          ? data.items
          : Array.isArray(data?.payments)
            ? data.payments
            : [];
      setPayments(normalizedPayments);
    } catch (error) {
      console.error('Error fetching payments:', error);
      setPayments([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = getAccessToken();
      const response = await fetchWithApiFallback('/api/v1/upi-payments/quick-log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...formData,
          amount: parseFloat(formData.amount),
          payment_datetime: new Date().toISOString(),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSnackbar({ open: true, message: 'UPI Payment logged successfully!', severity: 'success' });
        setReceiptDialog({ open: true, data });
        setFormData({
          devotee_phone: '',
          amount: '',
          sender_upi_id: '',
          upi_reference_number: '',
          payment_purpose: 'DONATION',
          notes: '',
        });
        fetchPayments();
      } else {
        const errorData = await response.json();
        setSnackbar({ open: true, message: errorData.detail || 'Failed to log payment', severity: 'error' });
      }
    } catch (error) {
      setSnackbar({ open: true, message: 'Error logging payment', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <Layout>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <PaymentIcon sx={{ fontSize: 40, mr: 2, color: '#FF9933' }} />
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            UPI Payment Logging
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {/* Quick Log Form */}
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <QrCodeIcon sx={{ mr: 1, color: '#FF9933' }} />
                <Typography variant="h6">Quick Log UPI Payment</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Log UPI payments received via static QR code
              </Typography>

              <form onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  label="Devotee Phone Number *"
                  name="devotee_phone"
                  value={formData.devotee_phone}
                  onChange={handleChange}
                  required
                  sx={{ mb: 2 }}
                  helperText="Enter phone number of devotee"
                />

                <TextField
                  fullWidth
                  label={'Amount (\u20B9) *'}
                  name="amount"
                  type="number"
                  value={formData.amount}
                  onChange={handleChange}
                  required
                  sx={{ mb: 2 }}
                  inputProps={{ step: '0.01', min: '0' }}
                />

                <TextField
                  fullWidth
                  label="Sender UPI ID"
                  name="sender_upi_id"
                  value={formData.sender_upi_id}
                  onChange={handleChange}
                  sx={{ mb: 2 }}
                  placeholder="9876543210@paytm"
                  helperText="From SMS notification"
                />

                <TextField
                  fullWidth
                  label="UPI Reference Number"
                  name="upi_reference_number"
                  value={formData.upi_reference_number}
                  onChange={handleChange}
                  sx={{ mb: 2 }}
                  helperText="Transaction reference from SMS"
                />

                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Payment Purpose *</InputLabel>
                  <Select
                    name="payment_purpose"
                    value={formData.payment_purpose}
                    onChange={handleChange}
                    label="Payment Purpose *"
                    required
                  >
                    <MenuItem value="DONATION">Donation</MenuItem>
                    <MenuItem value="SEVA">Seva Booking</MenuItem>
                    <MenuItem value="SPONSORSHIP">Sponsorship</MenuItem>
                    <MenuItem value="ANNADANA">Annadana</MenuItem>
                    <MenuItem value="OTHER">Other</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  label="Notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  multiline
                  rows={2}
                  sx={{ mb: 3 }}
                />

                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  size="large"
                  disabled={loading}
                  sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                  {loading ? 'Logging...' : 'Log Payment'}
                </Button>
              </form>
            </Paper>
          </Grid>

          {/* Today's Payments */}
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Today's UPI Payments</Typography>
                <TextField
                  label="Select Date"
                  type="date"
                  value={selectedDate.toISOString().split('T')[0]}
                  onChange={(e) => setSelectedDate(new Date(e.target.value))}
                  size="small"
                  InputLabelProps={{ shrink: true }}
                  sx={{ minWidth: 200 }}
                />
              </Box>

              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Time</strong></TableCell>
                      <TableCell><strong>Devotee</strong></TableCell>
                      <TableCell><strong>Amount</strong></TableCell>
                      <TableCell><strong>Purpose</strong></TableCell>
                      <TableCell><strong>Receipt</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {payments.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography color="text.secondary">No payments for this date</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      payments.map((payment) => (
                        <TableRow key={payment.id}>
                          <TableCell>
                            {new Date(payment.payment_datetime).toLocaleTimeString('en-IN', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </TableCell>
                          <TableCell>{payment.sender_phone || 'N/A'}</TableCell>
                          <TableCell>{'\u20B9'}{payment.amount.toFixed(2)}</TableCell>
                          <TableCell>
                            <Chip
                              label={payment.payment_purpose}
                              size="small"
                              color={
                                payment.payment_purpose === 'DONATION'
                                  ? 'success'
                                  : payment.payment_purpose === 'SEVA'
                                  ? 'primary'
                                  : 'default'
                              }
                            />
                          </TableCell>
                          <TableCell>{payment.receipt_number || 'N/A'}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

              {payments.length > 0 && (
                <Box sx={{ mt: 2, p: 2, bgcolor: '#FFF3E0', borderRadius: 1 }}>
                  <Typography variant="h6">
                    Total: {'\u20B9'}{payments.reduce((sum, p) => sum + p.amount, 0).toFixed(2)}
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>
        </Grid>

        {/* Receipt Dialog */}
        <Dialog open={receiptDialog.open} onClose={() => setReceiptDialog({ open: false, data: null })}>
          <DialogTitle>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <ReceiptIcon sx={{ mr: 1, color: '#FF9933' }} />
              Payment Receipt
            </Box>
          </DialogTitle>
          <DialogContent>
            {receiptDialog.data && (
              <Box sx={{ minWidth: 300 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Receipt Number
                </Typography>
                <Typography variant="h6" gutterBottom>
                  {receiptDialog.data.receipt_number}
                </Typography>

                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                  Amount
                </Typography>
                <Typography variant="h5" color="success.main" gutterBottom>
                  {'\u20B9'}{receiptDialog.data.amount.toFixed(2)}
                </Typography>

                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                  Purpose
                </Typography>
                <Chip label={receiptDialog.data.payment_purpose} color="primary" />

                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  Payment logged successfully and posted to accounting.
                </Typography>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setReceiptDialog({ open: false, data: null })}>Close</Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </Layout>
  );
}

export default UpiPayments;
