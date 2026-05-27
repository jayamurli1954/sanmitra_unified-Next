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

const pricingPlans = [
  {
    name: 'Starter',
    price: '₹1,500',
    note: 'per month, fixed',
    bestFor: 'Smaller temples and trusts starting with core digital operations.',
    limits: ['Up to 500 receipts/month', 'Up to 100 seva bookings/month', '3 users'],
    features: ['Donations and seva booking', 'Bilingual receipts', 'Basic roles and access'],
  },
  {
    name: 'Growth',
    price: '₹2,500',
    note: 'per month, fixed',
    bestFor: 'Growing institutions needing stronger workflows, reports, and accounting.',
    limits: ['Up to 2,000 receipts/month', 'Up to 500 seva bookings/month', '10 users'],
    features: ['Accounting integration', 'Advanced reports and audit drilldown', 'Priority support'],
    highlighted: true,
  },
  {
    name: 'Professional',
    price: '₹5,000',
    note: 'per month, fixed',
    bestFor: 'High-volume temples and trusts needing governance and advanced controls.',
    limits: ['Up to 10,000 receipts/month', 'Up to 2,500 seva bookings/month', '25 users'],
    features: ['Multi-entity controls', 'API/webhook integrations', 'Advanced governance support'],
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
              <Button href="#pricing" sx={{ color: '#8A4B05' }}>
                Pricing
              </Button>
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
              <Box sx={{ borderRadius: 2, overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.35)', bgcolor: '#fff' }}>
                <Box sx={{ bgcolor: '#FF9933', color: '#fff', px: 3, py: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Box component="img" src="/branding/mandirmitra_logo1.jpg" alt="" sx={{ width: 42, height: 42, borderRadius: 1 }} />
                    <Box>
                      <Typography sx={{ fontWeight: 900 }}>MandirMitra Temple - Demo</Typography>
                      <Typography variant="caption">Temple / Trust Management & Accounting System</Typography>
                    </Box>
                  </Box>
                  <Typography sx={{ fontWeight: 800 }}>Dashboard</Typography>
                </Box>
                <Box sx={{ p: 3, bgcolor: '#F7F7F7' }}>
                  <Typography variant="h5" sx={{ fontWeight: 900, mb: 2 }}>Temple Operations Dashboard</Typography>
                  <Grid container spacing={2}>
                    {[
                      ['Donations Today', '₹40,000', '2 donations'],
                      ['Month Collection', '₹1,50,000', 'donations + sevas'],
                      ['Recent Donors', '6', 'unique devotees'],
                      ['Sevas Today', '₹1,525', '2 bookings'],
                    ].map(([label, value, note]) => (
                      <Grid item xs={6} md={3} key={label}>
                        <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1.5 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 800 }}>{label}</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 900 }}>{value}</Typography>
                          <Typography variant="caption" color="text.secondary">{note}</Typography>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                  <Grid container spacing={2} sx={{ mt: 0.5 }}>
                    <Grid item xs={12} md={7}>
                      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5, height: '100%' }}>
                        <Typography sx={{ fontWeight: 900, mb: 1 }}>Collection Performance</Typography>
                        {[
                          ['Donations', '92%', '#0F766E'],
                          ['Sevas', '38%', '#C2410C'],
                          ['Public Payments', '64%', '#2563EB'],
                        ].map(([label, width, color]) => (
                          <Box key={label} sx={{ mb: 1.5 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Typography variant="body2" sx={{ fontWeight: 800 }}>{label}</Typography>
                              <Typography variant="body2">{width}</Typography>
                            </Box>
                            <Box sx={{ height: 10, borderRadius: 99, bgcolor: '#E5E7EB', overflow: 'hidden' }}>
                              <Box sx={{ width, height: '100%', bgcolor: color }} />
                            </Box>
                          </Box>
                        ))}
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={5}>
                      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1.5 }}>
                        <Typography sx={{ fontWeight: 900, mb: 1 }}>Recent Activity</Typography>
                        {['Donation receipt generated', 'Seva booking posted', 'Expense reversed', 'Trial balance balanced'].map((item) => (
                          <Typography key={item} variant="body2" sx={{ py: 0.75, borderBottom: '1px solid #EEE' }}>{item}</Typography>
                        ))}
                      </Paper>
                    </Grid>
                  </Grid>
                </Box>
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
              <Paper sx={{ p: 2, borderRadius: 2, bgcolor: '#fff', color: '#111827', boxShadow: '0 22px 60px rgba(0,0,0,0.28)' }}>
                <Typography variant="h5" sx={{ fontWeight: 900, mb: 2 }}>Trial Balance</Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr 1fr 1fr', gap: 1, fontWeight: 900, bgcolor: '#F3F4F6', p: 1 }}>
                  <span>Code</span><span>Account</span><span>Debit</span><span>Credit</span>
                </Box>
                {[
                  ['11001', 'Cash in Hand - Counter', '₹7,839', '-'],
                  ['12001', 'Bank - Current Account', '₹1,45,000', '-'],
                  ['42002', 'Seva Income - General', '-', '₹7,575'],
                  ['44001', 'General Donations', '-', '₹1,50,000'],
                  ['53002', 'Electricity', '₹3,486', '-'],
                ].map((row) => (
                  <Box key={row[0]} sx={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr 1fr 1fr', gap: 1, p: 1, borderBottom: '1px solid #E5E7EB' }}>
                    {row.map((cell) => <Typography key={cell} variant="body2">{cell}</Typography>)}
                  </Box>
                ))}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2, p: 1.5, bgcolor: '#FFF7ED', borderRadius: 1 }}>
                  <Typography sx={{ fontWeight: 900 }}>Balanced</Typography>
                  <Typography sx={{ fontWeight: 900 }}>Debit ₹1,56,325 = Credit ₹1,56,325</Typography>
                </Box>
              </Paper>
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

      <Container id="pricing" maxWidth="xl" sx={{ py: { xs: 6, md: 8 } }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="overline" sx={{ color: '#B45309', fontWeight: 900 }}>
            Pricing
          </Typography>
          <Typography variant="h3" sx={{ fontWeight: 900, mt: 1 }}>
            Simple monthly plans for temples and trusts
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1.5, maxWidth: 760 }}>
            Choose a fixed monthly plan based on receipt volume, seva bookings, user count, and the level of accounting and governance support required.
          </Typography>
        </Box>
        <Grid container spacing={2.5}>
          {pricingPlans.map((plan) => (
            <Grid item xs={12} md={4} key={plan.name}>
              <Paper
                variant="outlined"
                sx={{
                  p: 3,
                  height: '100%',
                  borderRadius: 2,
                  borderColor: plan.highlighted ? '#C27612' : '#E8D8B8',
                  bgcolor: plan.highlighted ? '#FFF7ED' : '#fff',
                  boxShadow: plan.highlighted ? '0 18px 45px rgba(194, 118, 18, 0.18)' : 'none',
                }}
              >
                <Typography variant="h5" sx={{ fontWeight: 900 }}>{plan.name}</Typography>
                <Typography sx={{ color: '#6B7280', mt: 1, minHeight: 48 }}>{plan.bestFor}</Typography>
                <Box sx={{ mt: 3 }}>
                  <Typography component="span" sx={{ fontSize: 36, fontWeight: 900 }}>{plan.price}</Typography>
                  <Typography component="span" color="text.secondary" sx={{ ml: 1 }}>{plan.note}</Typography>
                </Box>
                <Box sx={{ mt: 3 }}>
                  {plan.limits.map((item) => (
                    <Typography key={item} variant="body2" sx={{ py: 0.6, borderBottom: '1px solid #F3E8D0' }}>
                      {item}
                    </Typography>
                  ))}
                </Box>
                <Box sx={{ mt: 2 }}>
                  {plan.features.map((item) => (
                    <Typography key={item} variant="body2" sx={{ py: 0.5, fontWeight: 700 }}>
                      {item}
                    </Typography>
                  ))}
                </Box>
                <Button
                  href="/register-temple"
                  fullWidth
                  variant={plan.highlighted ? 'contained' : 'outlined'}
                  sx={{
                    mt: 3,
                    bgcolor: plan.highlighted ? '#C27612' : 'transparent',
                    borderColor: '#C27612',
                    color: plan.highlighted ? '#fff' : '#8A4B05',
                    '&:hover': { bgcolor: plan.highlighted ? '#9A5A0A' : '#FFF7ED' },
                  }}
                >
                  Request Onboarding
                </Button>
              </Paper>
            </Grid>
          ))}
        </Grid>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Annual prepay discounts, data migration, onboarding, training, payment gateway, SMS, and WhatsApp charges are quoted separately where applicable.
        </Typography>
      </Container>

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
