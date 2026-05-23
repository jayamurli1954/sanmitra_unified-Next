import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  LinearProgress,
} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';

export function InactivityWarning({ open, onStayLoggedIn, onLogout, countdownSeconds = 60 }) {
  const [countdown, setCountdown] = useState(countdownSeconds);

  useEffect(() => {
    if (!open) return;

    setCountdown(countdownSeconds);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onLogout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [open, countdownSeconds, onLogout]);

  const progress = (countdown / countdownSeconds) * 100;

  return (
    <Dialog open={open} onClose={() => {}} maxWidth="sm" fullWidth disableEscapeKeyDown>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <WarningIcon sx={{ color: 'warning.main' }} />
        Session Expiring
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, mb: 3 }}>
          <Typography variant="body1" gutterBottom>
            Your session will expire in{' '}
            <Typography component="span" variant="body1" sx={{ fontWeight: 'bold', color: 'error.main' }}>
              {countdown}
            </Typography>
            {' '}
            seconds due to inactivity.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Click "Stay Logged In" to continue your session.
          </Typography>
        </Box>
        <LinearProgress variant="determinate" value={progress} sx={{ mb: 2 }} />
      </DialogContent>
      <DialogActions>
        <Button onClick={onLogout} color="inherit">
          Logout
        </Button>
        <Button onClick={onStayLoggedIn} variant="contained" color="primary">
          Stay Logged In
        </Button>
      </DialogActions>
    </Dialog>
  );
}
