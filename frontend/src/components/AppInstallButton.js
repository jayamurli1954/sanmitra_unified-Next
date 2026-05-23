import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Tooltip,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';

const isStandaloneDisplay = () => (
  window.matchMedia?.('(display-mode: standalone)')?.matches
  || window.navigator.standalone === true
);

const isAppleTouchDevice = () => /iphone|ipad|ipod/i.test(window.navigator.userAgent || '');

function AppInstallButton({ variant = 'icon', color = 'inherit', fullWidth = false }) {
  const [installPrompt, setInstallPrompt] = useState(null);
  const [installed, setInstalled] = useState(() => isStandaloneDisplay());
  const [helpOpen, setHelpOpen] = useState(false);
  const isAppleDevice = useMemo(() => isAppleTouchDevice(), []);

  useEffect(() => {
    const handleBeforeInstallPrompt = (event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };
    const handleInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (installPrompt) {
      installPrompt.prompt();
      const choice = await installPrompt.userChoice.catch(() => null);
      if (choice?.outcome === 'accepted') {
        setInstalled(true);
      }
      setInstallPrompt(null);
      return;
    }
    setHelpOpen(true);
  };

  if (installed) {
    return null;
  }

  const label = isAppleDevice ? 'Add to Home Screen' : 'Install App';
  const instructions = isAppleDevice
    ? [
        'Open this site in Safari.',
        'Tap the Share button.',
        'Choose Add to Home Screen.',
      ]
    : [
        'Open this site in Chrome, Edge, or another supported browser.',
        'Use the browser install icon in the address bar, or choose Install App from the browser menu.',
        'After installation, MandirMitra opens like a normal desktop or mobile app.',
      ];

  return (
    <>
      {variant === 'button' ? (
        <Button
          color={color}
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={handleInstall}
          fullWidth={fullWidth}
          sx={{ textTransform: 'none', fontWeight: 700 }}
        >
          {label}
        </Button>
      ) : (
        <Tooltip title={label}>
          <IconButton color={color} onClick={handleInstall} size="small" aria-label={label}>
            <DownloadIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}

      <Dialog open={helpOpen} onClose={() => setHelpOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{label}</DialogTitle>
        <DialogContent>
          <List dense>
            {instructions.map((instruction) => (
              <ListItem key={instruction} disableGutters>
                <ListItemText primary={instruction} />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHelpOpen(false)}>OK</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default AppInstallButton;
