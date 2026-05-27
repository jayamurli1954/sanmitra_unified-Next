import React from 'react';
import {
  Box,
  Button,
  Container,
  Grid,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import VolunteerActivismIcon from '@mui/icons-material/VolunteerActivism';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import EventAvailableIcon from '@mui/icons-material/EventAvailable';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EmailIcon from '@mui/icons-material/Email';
import LanguageIcon from '@mui/icons-material/Language';
import LoginIcon from '@mui/icons-material/Login';

const landingAsset = (path) => `/branding/landing/${path}`;

const featureItems = [
  {
    icon: <VolunteerActivismIcon />,
    title: 'Donations',
    text: 'Record cash, bank, online, and public-link donations with bilingual receipts.',
  },
  {
    icon: <TempleHinduIcon />,
    title: 'Sevas And Poojas',
    text: 'Book sevas, manage devotee details, issue receipts, and track bookings.',
  },
  {
    icon: <AccountBalanceIcon />,
    title: 'Accounting',
    text: 'Post donations, sevas, expenses, transfers, and reversals through MitraBooks.',
  },
  {
    icon: <ReceiptLongIcon />,
    title: 'Reports',
    text: 'Trial balance, ledger, income and expenditure, receipts and payments, and day books.',
  },
  {
    icon: <CalendarMonthIcon />,
    title: 'Panchang',
    text: 'Location-aware Panchang with tithi, nakshatra, muhurat, and temple-day context.',
  },
  {
    icon: <EventAvailableIcon />,
    title: 'Public Payments',
    text: 'Let devotees submit donation or seva payments for admin verification and receipt issue.',
  },
];

function MandirMitraLanding() {
  return (
    <Box sx={{ bgcolor: '#fffaf0', color: '#111827', minHeight: '100vh' }}>
      <Box
        component="header"
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          bgcolor: 'rgba(255, 250, 240, 0.92)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(180, 83, 9, 0.16)',
        }}
      >
        <Container maxWidth="xl">
          <Box sx={{ height: 72, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box
                component="img"
                src="/branding/mandirmitra_logo1.jpg"
                alt="MandirMitra"
                sx={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 1 }}
              />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1 }}>
                  MandirMitra
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Temple / Trust Management
                </Typography>
              </Box>
            </Box>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              <Button href="/register-temple" variant="outlined" sx={{ borderColor: '#C27612', color: '#8A4B05' }}>
                Onboard Temple
              </Button>
              <Button href="/login" variant="contained" startIcon={<LoginIcon />} sx={{ bgcolor: '#C27612', '&:hover': { bgcolor: '#9A5A0A' } }}>
                Login
              </Button>
            </Stack>
          </Box>
        </Container>
      </Box>

      <Box
        component="section"
        sx={{
          minHeight: { xs: 'auto', md: 'calc(100svh - 72px)' },
          display: 'flex',
          alignItems: 'center',
          py: { xs: 6, md: 8 },
          background:
            'linear-gradient(120deg, rgba(57, 32, 9, 0.92), rgba(116, 64, 9, 0.76) 48%, rgba(255, 250, 240, 0.28)), url("/temple-gopuram.svg") center right / min(56vw, 720px) no-repeat',
        }}
      >
        <Container maxWidth="xl">
          <Grid container spacing={5} alignItems="center">
            <Grid item xs={12} md={5}>
              <Typography variant="overline" sx={{ color: '#FED7AA', fontWeight: 900 }}>
                MANDIRMITRA BY SANMITRA TECH
              </Typography>
              <Typography
                component="h1"
                sx={{
                  color: '#fff',
                  fontWeight: 900,
                  fontSize: { xs: 42, md: 64 },
                  lineHeight: 1.02,
                  mt: 1,
                }}
              >
                MandirMitra
              </Typography>
              <Typography variant="h5" sx={{ color: '#FFE8C2', mt: 2, maxWidth: 560, lineHeight: 1.45 }}>
                A temple and trust operations system for donations, sevas, receipts, Panchang, reports, and accounting.
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 4 }}>
                <Button href="/register-temple" size="large" variant="contained" sx={{ bgcolor: '#F59E0B', color: '#111827', '&:hover': { bgcolor: '#D97706' } }}>
                  Onboard Temple / Trust
                </Button>
                <Button href="/login" size="large" variant="outlined" sx={{ color: '#fff', borderColor: '#FFE8C2' }}>
                  Existing Admin Login
                </Button>
              </Stack>
            </Grid>

            <Grid item xs={12} md={7}>
              <Box
                sx={{
                  borderRadius: 2,
                  overflow: 'hidden',
                  border: '1px solid rgba(255,255,255,0.32)',
                  boxShadow: '0 30px 80px rgba(0,0,0,0.35)',
                  bgcolor: '#111827',
                }}
              >
                <Box
                  component="img"
                  src={landingAsset('mandirmitra_dashboard.jpg')}
                  alt="MandirMitra dashboard screenshot"
                  sx={{ width: '100%', display: 'block' }}
                />
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      <Container maxWidth="xl" sx={{ py: { xs: 6, md: 8 } }}>
        <Grid container spacing={4} alignItems="center">
          <Grid item xs={12} md={5}>
            <Typography variant="overline" sx={{ color: '#B45309', fontWeight: 900 }}>
              Working Modules
            </Typography>
            <Typography variant="h3" sx={{ fontWeight: 900, mt: 1 }}>
              Built around daily temple operations
            </Typography>
          </Grid>
          <Grid item xs={12} md={7}>
            <Grid container spacing={2}>
              {featureItems.map((feature) => (
                <Grid item xs={12} sm={6} key={feature.title}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2.25,
                      borderRadius: 2,
                      height: '100%',
                      borderColor: '#E8D8B8',
                      bgcolor: '#fff',
                    }}
                  >
                    <Box sx={{ color: '#C27612', mb: 1 }}>{feature.icon}</Box>
                    <Typography variant="h6" sx={{ fontWeight: 800 }}>{feature.title}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>{feature.text}</Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Grid>
        </Grid>
      </Container>

      <Box sx={{ bgcolor: '#102A2A', color: '#fff', py: { xs: 6, md: 8 } }}>
        <Container maxWidth="xl">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Box
                component="img"
                src={landingAsset('mandirmitra_trial_balance_report.jpg')}
                alt="MandirMitra accounting report screenshot"
                sx={{
                  width: '100%',
                  borderRadius: 2,
                  border: '1px solid rgba(255,255,255,0.18)',
                  boxShadow: '0 22px 60px rgba(0,0,0,0.28)',
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="overline" sx={{ color: '#FCD34D', fontWeight: 900 }}>
                Accounting Connected
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 900, mt: 1 }}>
                Receipts, vouchers, ledger drilldown, and reports stay linked.
              </Typography>
              <Typography variant="body1" sx={{ color: '#D1FAE5', mt: 2, maxWidth: 640 }}>
                Donations, sevas, expenses, and reversals post through the shared MitraBooks accounting engine, preserving auditability and double-entry discipline.
              </Typography>
            </Grid>
          </Grid>
        </Container>
      </Box>

      <Container maxWidth="xl" sx={{ py: { xs: 6, md: 8 } }}>
        <Paper
          sx={{
            p: { xs: 3, md: 5 },
            borderRadius: 2,
            bgcolor: '#fff',
            border: '1px solid #E8D8B8',
          }}
        >
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h3" sx={{ fontWeight: 900 }}>
                Start with a temple/trust onboarding request.
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mt: 1.5 }}>
                Existing admins can continue directly to login. New temples and trusts can request onboarding.
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ justifyContent: { md: 'flex-end' } }}>
                <Button href="/register-temple" size="large" variant="contained" sx={{ bgcolor: '#C27612', '&:hover': { bgcolor: '#9A5A0A' } }}>
                  Onboard Temple / Trust
                </Button>
                <Button href="/login" size="large" variant="outlined" sx={{ borderColor: '#C27612', color: '#8A4B05' }}>
                  Login
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </Paper>
      </Container>

      <Box component="footer" sx={{ bgcolor: '#1F2937', color: '#fff', py: 4 }}>
        <Container maxWidth="xl">
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <Typography variant="h6" sx={{ fontWeight: 900 }}>Contact</Typography>
            </Grid>
            <Grid item xs={12} md={9}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ flexWrap: 'wrap' }}>
                <Button href="https://wa.me/917904942915" startIcon={<WhatsAppIcon />} sx={{ color: '#D1FAE5', justifyContent: 'flex-start' }}>7904942915</Button>
                <Button href="mailto:contact@sanmitratech.in" startIcon={<EmailIcon />} sx={{ color: '#D1FAE5', justifyContent: 'flex-start' }}>contact@sanmitratech.in</Button>
                <Button href="https://www.sanmitratech.in" startIcon={<LanguageIcon />} sx={{ color: '#D1FAE5', justifyContent: 'flex-start' }}>www.sanmitratech.in</Button>
                <Button href="https://www.mandirmitra.sanmitratech.in" startIcon={<LanguageIcon />} sx={{ color: '#D1FAE5', justifyContent: 'flex-start' }}>www.mandirmitra.sanmitratech.in</Button>
              </Stack>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  );
}

export default MandirMitraLanding;
