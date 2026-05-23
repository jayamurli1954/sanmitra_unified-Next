import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
} from '@mui/material';
import Layout from '../components/Layout';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';

function SevaRescheduleApproval() {
  const { showSuccess, showError } = useNotification();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pendingRequests, setPendingRequests] = useState([]);
  const [approvalDialog, setApprovalDialog] = useState({ open: false, booking: null, action: null });

  useEffect(() => {
    fetchPendingRequests();
  }, []);

  const fetchPendingRequests = async () => {
    try {
      setLoading(true);
      setError('');
      // Get all bookings with pending reschedule requests
      const response = await api.get('/api/v1/sevas/reschedule/pending');
      setPendingRequests(response.data);
    } catch (err) {
      console.error('Failed to load reschedule requests:', err);
      const msg = err.response?.data?.detail || 'Failed to load pending reschedule requests';
      setError(msg);
      setPendingRequests([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = (booking, approve) => {
    setApprovalDialog({ open: true, booking, action: approve ? 'approve' : 'reject' });
  };

  const submitApproval = async () => {
    try {
      await api.post(
        `/api/v1/sevas/bookings/${approvalDialog.booking.id}/approve-reschedule`,
        null,
        {
          params: { approve: approvalDialog.action === 'approve' }
        }
      );

      showSuccess(
        approvalDialog.action === 'approve'
          ? 'Reschedule approved successfully'
          : 'Reschedule request rejected'
      );

      setApprovalDialog({ open: false, booking: null, action: null });
      fetchPendingRequests();
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to process approval');
    }
  };

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          Seva Reschedule Approval
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {pendingRequests.length === 0 && !loading && (
          <Alert severity="info" sx={{ mt: 2 }}>
            No pending reschedule requests
          </Alert>
        )}

        {pendingRequests.length > 0 && (
          <Paper sx={{ p: 3, mt: 2 }}>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Receipt #</strong></TableCell>
                    <TableCell><strong>Seva Name</strong></TableCell>
                    <TableCell><strong>Devotee</strong></TableCell>
                    <TableCell><strong>Original Date</strong></TableCell>
                    <TableCell><strong>Requested Date</strong></TableCell>
                    <TableCell><strong>Reason</strong></TableCell>
                    <TableCell><strong>Action</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pendingRequests.map((booking) => (
                    <TableRow key={booking.id}>
                      <TableCell>{booking.receipt_number}</TableCell>
                      <TableCell>{booking.seva?.name_english || 'Unknown'}</TableCell>
                      <TableCell>{booking.devotee?.name || 'Unknown'}</TableCell>
                      <TableCell>
                        {booking.original_booking_date
                          ? new Date(booking.original_booking_date).toLocaleDateString()
                          : new Date(booking.booking_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {booking.reschedule_requested_date
                          ? new Date(booking.reschedule_requested_date).toLocaleDateString()
                          : 'N/A'}
                      </TableCell>
                      <TableCell>{booking.reschedule_reason || 'N/A'}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Button
                            size="small"
                            variant="contained"
                            color="success"
                            onClick={() => handleApprove(booking, true)}
                          >
                            Approve
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            onClick={() => handleApprove(booking, false)}
                          >
                            Reject
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* Approval Dialog */}
        <Dialog open={approvalDialog.open} onClose={() => setApprovalDialog({ open: false, booking: null, action: null })}>
          <DialogTitle>
            {approvalDialog.action === 'approve' ? 'Approve' : 'Reject'} Reschedule Request
          </DialogTitle>
          <DialogContent>
            {approvalDialog.booking && (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Original Date: {new Date(approvalDialog.booking.original_booking_date || approvalDialog.booking.booking_date).toLocaleDateString()}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Requested Date: {approvalDialog.booking.reschedule_requested_date ? new Date(approvalDialog.booking.reschedule_requested_date).toLocaleDateString() : 'N/A'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Reason: {approvalDialog.booking.reschedule_reason || 'N/A'}
                </Typography>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setApprovalDialog({ open: false, booking: null, action: null })}>
              Cancel
            </Button>
            <Button
              variant="contained"
              color={approvalDialog.action === 'approve' ? 'success' : 'error'}
              onClick={submitApproval}
            >
              {approvalDialog.action === 'approve' ? 'Approve' : 'Reject'}
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

export default SevaRescheduleApproval;



