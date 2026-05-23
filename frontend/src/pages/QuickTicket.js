import React, { useState, useEffect, useRef } from 'react';
import {
  Box, Container, Paper, Typography, Button, Grid, Card, CardContent,
  CardActions, TextField, Alert, CircularProgress, Chip, Divider,
  Dialog, DialogTitle, DialogContent, DialogActions,
} from '@mui/material';
import PrintIcon from '@mui/icons-material/Print';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Layout from '../components/Layout';
import api from '../services/api';

export default function QuickTicket() {
  const [sevas, setSevas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSeva, setSelectedSeva] = useState(null);
  const [phone, setPhone] = useState('');
  const [devoteeName, setDevoteeName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [booking, setBooking] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const printRef = useRef(null);

  useEffect(() => {
    fetchQuickSevas();
  }, []);

  const fetchQuickSevas = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/sevas/', { params: { include_inactive: false } });
      const all = Array.isArray(response.data) ? response.data : [];
      setSevas(all.filter((s) => s.quick_ticket_enabled));
    } catch (err) {
      setError('Failed to load sevas. Please refresh.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSeva = (seva) => {
    setSelectedSeva(seva);
    setPhone('');
    setDevoteeName('');
    setSubmitError('');
    setDialogOpen(true);
  };

  const handleBook = async () => {
    if (!selectedSeva) return;
    try {
      setSubmitting(true);
      setSubmitError('');
      const payload = {
        seva_id: selectedSeva.id,
        seva_name: selectedSeva.name_english,
        amount: selectedSeva.amount,
        booking_date: new Date().toISOString().split('T')[0],
        payment_mode: 'counter_cash',
        payment_status: 'completed',
        ...(phone.trim() && { devotee_phone: phone.trim() }),
        ...(devoteeName.trim() && { devotee_name: devoteeName.trim() }),
      };
      const response = await api.post('/api/v1/sevas/bookings/quick-ticket', payload);
      setBooking(response.data);
      setDialogOpen(false);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Booking failed';
      setSubmitError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  const handlePrint = () => {
    const printContent = printRef.current?.innerHTML;
    if (!printContent) return;
    const w = window.open('', '_blank');
    w.document.write(`
      <html><head><title>Quick Token</title>
      <style>body{font-family:Arial,sans-serif;padding:16px;} h3{margin:4px 0;} p{margin:2px 0;}</style>
      </head><body>${printContent}</body></html>
    `);
    w.document.close();
    w.print();
  };

  const handleNewBooking = () => {
    setBooking(null);
    setSelectedSeva(null);
    setPhone('');
    setDevoteeName('');
  };

  const getCategoryColor = (category) => {
    const colors = {
      abhisheka: '#2E7D32', alankara: '#1565C0', pooja: '#7B1FA2',
      archana: '#F57C00', vahana_seva: '#00796B', special: '#C62828', festival: '#FF6B35',
    };
    return colors[category] || '#666';
  };

  if (loading) {
    return (
      <Layout>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
          <CircularProgress />
        </Box>
      </Layout>
    );
  }

  if (booking) {
    return (
      <Layout>
        <Container maxWidth="sm" sx={{ mt: 4 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <CheckCircleIcon sx={{ fontSize: 64, color: 'success.main', mb: 1 }} />
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
              Booking Confirmed!
            </Typography>
            <div ref={printRef}>
              <Typography variant="h6" sx={{ mb: 0.5 }}>{booking.seva_name || selectedSeva?.name_english}</Typography>
              <Typography variant="body1">Amount: <strong>₹{booking.amount || selectedSeva?.amount}</strong></Typography>
              <Typography variant="body2" color="text.secondary">Date: {booking.booking_date || new Date().toISOString().split('T')[0]}</Typography>
              {booking.booking_id && (
                <Typography variant="body2" color="text.secondary">Booking ID: {booking.booking_id}</Typography>
              )}
              {(booking.devotee_name || devoteeName) && (
                <Typography variant="body2">Name: {booking.devotee_name || devoteeName}</Typography>
              )}
              {(booking.devotee_phone || phone) && (
                <Typography variant="body2">Phone: {booking.devotee_phone || phone}</Typography>
              )}
            </div>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button variant="contained" startIcon={<PrintIcon />} onClick={handlePrint}>
                Print Ticket
              </Button>
              <Button variant="outlined" onClick={handleNewBooking}>
                New Booking
              </Button>
            </Box>
          </Paper>
        </Container>
      </Layout>
    );
  }

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Paper sx={{ p: 2, mb: 3, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
          <Box display="flex" alignItems="center" gap={1}>
            <TempleHinduIcon sx={{ color: '#fff', fontSize: 32 }} />
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#fff' }}>
                Quick Token Counter
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                One-click booking for counter sevas
              </Typography>
            </Box>
          </Box>
        </Paper>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {sevas.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">
              No quick-token sevas configured. Enable "Quick Token Mode" on sevas in Seva Management.
            </Typography>
          </Paper>
        ) : (
          <Grid container spacing={2}>
            {sevas.map((seva) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={seva.id}>
                <Card
                  sx={{
                    height: '100%',
                    cursor: 'pointer',
                    border: '2px solid transparent',
                    transition: 'all 0.15s',
                    '&:hover': { borderColor: '#FF9933', boxShadow: 4 },
                  }}
                  onClick={() => handleSelectSeva(seva)}
                >
                  <CardContent sx={{ pb: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, lineHeight: 1.2 }}>
                      {seva.name_english}
                    </Typography>
                    {seva.name_kannada && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {seva.name_kannada}
                      </Typography>
                    )}
                    <Chip
                      label={seva.category.replace('_', ' ').toUpperCase()}
                      size="small"
                      sx={{ bgcolor: getCategoryColor(seva.category), color: '#fff', mb: 1 }}
                    />
                    {seva.time_slot && (
                      <Typography variant="caption" display="block" color="text.secondary">
                        {seva.time_slot}
                      </Typography>
                    )}
                  </CardContent>
                  <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
                    <Button
                      variant="contained"
                      fullWidth
                      sx={{ fontWeight: 700, fontSize: '1rem' }}
                      onClick={(e) => { e.stopPropagation(); handleSelectSeva(seva); }}
                    >
                      ₹{seva.amount}
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>

      {/* Booking Dialog */}
      <Dialog open={dialogOpen} onClose={() => !submitting && setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>
          {selectedSeva?.name_english}
          <Typography variant="body2" color="text.secondary">₹{selectedSeva?.amount}</Typography>
        </DialogTitle>
        <DialogContent>
          {submitError && <Alert severity="error" sx={{ mb: 2 }}>{submitError}</Alert>}
          {selectedSeva?.requires_devotee_details ? (
            <>
              <TextField
                label="Devotee Name (optional)"
                value={devoteeName}
                onChange={(e) => setDevoteeName(e.target.value)}
                fullWidth
                size="small"
                sx={{ mb: 2, mt: 1 }}
              />
              <TextField
                label="Phone (optional)"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                fullWidth
                size="small"
                inputProps={{ maxLength: 10 }}
              />
            </>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Click Confirm to book immediately.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={submitting}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleBook}
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={16} /> : null}
          >
            {submitting ? 'Booking...' : 'Confirm & Book'}
          </Button>
        </DialogActions>
      </Dialog>
    </Layout>
  );
}
