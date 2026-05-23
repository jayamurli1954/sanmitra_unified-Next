import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField, Alert,
  Snackbar, CircularProgress, ToggleButton, ToggleButtonGroup,
  Tooltip,
} from '@mui/material';
import Layout from '../../components/Layout';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import VolunteerActivismIcon from '@mui/icons-material/VolunteerActivism';
import { fetchWithApiFallback } from '../../utils/apiBaseUrl';
import { getAccessToken } from '../../utils/authStorage';

function authHeaders() {
  return {
    Authorization: `Bearer ${getAccessToken()}`,
    'Content-Type': 'application/json',
  };
}

function statusChip(status) {
  if (status === 'verified') return <Chip label="Verified" color="success" size="small" icon={<CheckCircleIcon />} />;
  return <Chip label="Pending" color="warning" size="small" icon={<HourglassEmptyIcon />} />;
}

function typeChip(paymentType) {
  if (paymentType === 'donation') {
    return <Chip label="Donation" size="small" icon={<VolunteerActivismIcon />} color="secondary" variant="outlined" />;
  }
  return <Chip label="Seva" size="small" icon={<TempleHinduIcon />} color="primary" variant="outlined" />;
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
  } catch (_e) {
    return iso;
  }
}

export default function PublicPayments() {
  const [payments, setPayments] = useState([]);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [loading, setLoading] = useState(false);
  const [approveDialog, setApproveDialog] = useState({ open: false, payment: null });
  const [approveForm, setApproveForm] = useState({ utr_reference: '', payment_date: '' });
  const [approving, setApproving] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    try {
      const qs = statusFilter ? `?status=${statusFilter}` : '';
      const res = await fetchWithApiFallback(`/api/v1/public-payments${qs}`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        setPayments(await res.json());
      }
    } catch (_e) { /* ignore fetch errors */ }
    finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const openApprove = (payment) => {
    setApproveForm({
      utr_reference: '',
      payment_date: new Date().toISOString().slice(0, 10),
    });
    setApproveDialog({ open: true, payment });
  };

  const handleApprove = async () => {
    const { payment } = approveDialog;
    if (!payment) return;
    setApproving(true);
    try {
      const res = await fetchWithApiFallback(
        `/api/v1/public-payments/${payment.id}/verify`,
        {
          method: 'PATCH',
          headers: authHeaders(),
          body: JSON.stringify({
            utr_reference: approveForm.utr_reference,
            payment_date: approveForm.payment_date,
          }),
        }
      );
      const data = await res.json();
      if (!res.ok) {
        setSnackbar({ open: true, message: data.detail || 'Approval failed', severity: 'error' });
        return;
      }
      const receiptInfo = data.receipt_number ? ` | Receipt: ${data.receipt_number}` : '';
      setSnackbar({
        open: true,
        message: `Payment verified! Accounting entry posted.${receiptInfo}`,
        severity: 'success',
      });
      setApproveDialog({ open: false, payment: null });
      fetchPayments();
    } catch (_e) {
      setSnackbar({ open: true, message: 'Network error. Please try again.', severity: 'error' });
    } finally {
      setApproving(false);
    }
  };

  const { payment: dlgPayment } = approveDialog;

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Typography variant="h5" fontWeight="bold" gutterBottom>
          Public Payment Approvals
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Review and approve payments received via the public payment portal.
          Approving a payment posts the accounting entry (Debit Bank, Credit Seva/Donation account).
        </Typography>

        {/* Filter */}
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <ToggleButtonGroup
            value={statusFilter}
            exclusive
            onChange={(_, v) => { if (v !== null) setStatusFilter(v); }}
            size="small"
          >
            <ToggleButton value="pending">Pending</ToggleButton>
            <ToggleButton value="verified">Verified</ToggleButton>
            <ToggleButton value="">All</ToggleButton>
          </ToggleButtonGroup>
          <Button variant="outlined" size="small" onClick={fetchPayments} disabled={loading}>
            {loading ? <CircularProgress size={16} /> : 'Refresh'}
          </Button>
          <Typography variant="body2" color="text.secondary">
            {payments.length} record{payments.length !== 1 ? 's' : ''}
          </Typography>
        </Box>

        <TableContainer component={Paper} elevation={1}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#FFF3E0' }}>
                <TableCell><strong>Payment ID</strong></TableCell>
                <TableCell><strong>Date</strong></TableCell>
                <TableCell><strong>Type</strong></TableCell>
                <TableCell><strong>Seva / Donation</strong></TableCell>
                <TableCell><strong>Devotee</strong></TableCell>
                <TableCell><strong>Mobile</strong></TableCell>
                <TableCell align="right"><strong>Amount (₹)</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell><strong>UTR Reference</strong></TableCell>
                <TableCell><strong>Action</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {payments.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} align="center">
                    <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                      {loading ? 'Loading...' : 'No payments found'}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {payments.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>
                    <Tooltip title={p.id || ''}>
                      <Typography variant="body2" fontFamily="monospace" fontWeight="bold">
                        {String(p.id || '').slice(0, 8).toUpperCase()}
                      </Typography>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{formatDate(p.created_at)}</Typography>
                  </TableCell>
                  <TableCell>{typeChip(p.payment_type)}</TableCell>
                  <TableCell>
                    <Typography variant="body2">{p.seva_name || '—'}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{p.devotee_name || '—'}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{p.devotee_phone || '—'}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight="bold">
                      {p.amount != null ? Number(p.amount).toLocaleString('en-IN') : '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>{statusChip(p.status)}</TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {p.utr_reference || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {p.status === 'pending' ? (
                      <Button
                        size="small"
                        variant="contained"
                        color="success"
                        onClick={() => openApprove(p)}
                        startIcon={<CheckCircleIcon />}
                      >
                        Approve
                      </Button>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        {p.verified_at ? `by ${p.verified_by || 'admin'}` : '—'}
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* Approve Dialog */}
      <Dialog open={approveDialog.open} onClose={() => setApproveDialog({ open: false, payment: null })} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ bgcolor: '#FF9933', color: 'white' }}>
          Approve Payment
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          {dlgPayment && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                <strong>{dlgPayment.payment_type === 'donation' ? 'Donation' : 'Seva'}:</strong>{' '}
                {dlgPayment.seva_name}
                {dlgPayment.amount != null && ` — ₹${Number(dlgPayment.amount).toLocaleString('en-IN')}`}
                <br />
                <strong>Devotee:</strong> {dlgPayment.devotee_name} ({dlgPayment.devotee_phone})
              </Alert>
              <Alert severity="warning" sx={{ mb: 3 }}>
                Approving will post a <strong>double-entry accounting record</strong>:{' '}
                Debit Bank Account → Credit{' '}
                {dlgPayment.payment_type === 'donation' ? 'Donation Income' : 'Seva Income'} Account.
              </Alert>
              <TextField
                label="UTR / Bank Reference Number"
                value={approveForm.utr_reference}
                onChange={(e) => setApproveForm((f) => ({ ...f, utr_reference: e.target.value }))}
                fullWidth
                sx={{ mb: 2 }}
                helperText="Enter the UTR or bank transaction reference from WhatsApp confirmation"
              />
              <TextField
                label="Payment Date"
                type="date"
                value={approveForm.payment_date}
                onChange={(e) => setApproveForm((f) => ({ ...f, payment_date: e.target.value }))}
                fullWidth
                InputLabelProps={{ shrink: true }}
                helperText="Date the payment was received in the bank"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApproveDialog({ open: false, payment: null })} disabled={approving}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="success"
            onClick={handleApprove}
            disabled={approving}
            startIcon={approving ? <CircularProgress size={16} color="inherit" /> : <CheckCircleIcon />}
          >
            {approving ? 'Posting...' : 'Confirm & Post Accounting Entry'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Layout>
  );
}
