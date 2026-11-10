import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stack,
  Chip,
  Button,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import DownloadIcon from '@mui/icons-material/Download';
import {
  buildWhatsAppShareUrl,
  formatPanchangWhatsAppMessage,
} from '../utils/panchangWhatsAppMessage';
import {
  WHATSAPP_SHARE_MESSAGES,
  createPanchangInfographic,
  downloadPanchangInfographic,
  sharePanchangInfographicToWhatsApp,
} from '../utils/panchangInfographic';

/**
 * Compact one-page WhatsApp share card for the selected day's Panchang.
 * Keeps the full Panchang display unchanged.
 */
function PanchangWhatsAppCard({ data }) {
  const [copyStatus, setCopyStatus] = useState('');
  const whatsappMessage = useMemo(() => formatPanchangWhatsAppMessage(data), [data]);
  const [imageUrl, setImageUrl] = useState('');
  const infographicRef = useRef(null);

  // Draw the infographic whenever the day's data changes.
  useEffect(() => {
    let cancelled = false;
    infographicRef.current = null;
    setImageUrl('');
    if (!data) return undefined;
    createPanchangInfographic(data)
      .then((result) => {
        if (cancelled || !result) return;
        infographicRef.current = result;
        setImageUrl(result.canvas.toDataURL('image/png'));
      })
      .catch((err) => {
        console.error('Panchang infographic failed:', err);
      });
    return () => {
      cancelled = true;
    };
  }, [data]);

  const flash = (message) => {
    setCopyStatus(message);
    window.setTimeout(() => setCopyStatus(''), 6000);
  };

  const handleDownloadImage = () => {
    const file = infographicRef.current?.file;
    if (!file) return;
    downloadPanchangInfographic(file);
    flash('Image downloaded');
  };

  const handleShareImage = async () => {
    const outcome = await sharePanchangInfographicToWhatsApp(infographicRef.current?.file);
    const message = WHATSAPP_SHARE_MESSAGES[outcome];
    if (message) flash(message);
  };

  const handleCopyImage = async () => {
    const file = infographicRef.current?.file;
    if (!file) return;
    try {
      await navigator.clipboard.write([new window.ClipboardItem({ 'image/png': file })]);
      flash('Image copied — paste it into WhatsApp');
    } catch (err) {
      handleDownloadImage();
    }
  };

  if (!data || !whatsappMessage) {
    return null;
  }

  const handleCopyWhatsApp = async () => {
    try {
      await navigator.clipboard.writeText(whatsappMessage);
      setCopyStatus('Copied WhatsApp message');
    } catch (err) {
      setCopyStatus('Copy failed — select the card text manually');
    }
    window.setTimeout(() => setCopyStatus(''), 2500);
  };

  const handleOpenWhatsApp = () => {
    window.open(buildWhatsAppShareUrl(whatsappMessage), '_blank', 'noopener,noreferrer');
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Today's Panchang",
          text: whatsappMessage,
        });
        return;
      } catch (err) {
        if (err?.name === 'AbortError') return;
      }
    }
    await handleCopyWhatsApp();
  };

  return (
    <Paper
      className="no-print"
      sx={{
        p: 2,
        mb: 2,
        maxWidth: 420,
        mx: 'auto',
        bgcolor: '#F7FBF4',
        border: '1px solid #C8E6C9',
        borderRadius: 2,
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#1B5E20' }}>
          WhatsApp message card
        </Typography>
        <Chip label="1-page" size="small" sx={{ bgcolor: '#25D366', color: '#fff', fontWeight: 600 }} />
      </Stack>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
        English / ಕನ್ನಡ / संस्कृतम् infographic for phone share, with the text version below.
      </Typography>
      {imageUrl && (
        <Box sx={{ mb: 1.5 }}>
          <Box
            component="img"
            src={imageUrl}
            alt="Panchang infographic"
            sx={{ width: '100%', display: 'block', borderRadius: 1, border: '1px solid #E0E0E0' }}
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<WhatsAppIcon />}
              onClick={handleShareImage}
              sx={{ bgcolor: '#25D366', '&:hover': { bgcolor: '#1ebe57' } }}
            >
              Share on WhatsApp
            </Button>
            <Button fullWidth variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadImage}>
              Download
            </Button>
            <Button fullWidth variant="outlined" startIcon={<ContentCopyIcon />} onClick={handleCopyImage}>
              Copy image
            </Button>
          </Stack>
        </Box>
      )}
      <Box
        component="pre"
        sx={{
          m: 0,
          p: 1.5,
          maxHeight: 220,
          overflow: 'auto',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: '"Noto Sans","Noto Sans Kannada","Noto Sans Devanagari",system-ui,sans-serif',
          fontSize: 13,
          lineHeight: 1.45,
          bgcolor: '#fff',
          borderRadius: 1,
          border: '1px solid #E0E0E0',
        }}
      >
        {whatsappMessage}
      </Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1.5 }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<ContentCopyIcon />}
          onClick={handleCopyWhatsApp}
        >
          Copy message
        </Button>
        <Button
          fullWidth
          variant="contained"
          startIcon={<WhatsAppIcon />}
          onClick={handleOpenWhatsApp}
          sx={{ bgcolor: '#25D366', '&:hover': { bgcolor: '#1ebe57' } }}
        >
          Send as text
        </Button>
        <Button
          fullWidth
          variant="outlined"
          onClick={handleShare}
        >
          Share
        </Button>
      </Stack>
      {copyStatus && (
        <Typography variant="caption" sx={{ display: 'block', mt: 1, color: '#2E7D32' }}>
          {copyStatus}
        </Typography>
      )}
    </Paper>
  );
}

export default PanchangWhatsAppCard;
