import React, { useState, useEffect } from 'react';
import {
  Box, Container, Paper, Typography, Tab, Tabs, Chip, Alert,
  CircularProgress, Divider, Card, CardContent, Grid,
} from '@mui/material';
import VerifiedIcon from '@mui/icons-material/Verified';
import InfoIcon from '@mui/icons-material/Info';
import SecurityIcon from '@mui/icons-material/Security';
import NewReleasesIcon from '@mui/icons-material/NewReleases';
import Layout from '../components/Layout';
import { buildApiUrl } from '../utils/apiBaseUrl';

export default function ReleaseNotes() {
  const [version, setVersion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    fetchVersion();
  }, []);

  const fetchVersion = async () => {
    try {
      setLoading(true);
      const url = buildApiUrl('/api/v1/mandir/version');
      const response = await fetch(url);
      const data = await response.json();
      setVersion(data);
    } catch (err) {
      setError('Failed to fetch version info. Offline or backend unavailable.');
    } finally {
      setLoading(false);
    }
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

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Paper sx={{ p: 3, mb: 3, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
          <Box display="flex" alignItems="center" gap={2}>
            <NewReleasesIcon sx={{ fontSize: 40, color: '#fff' }} />
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#fff', mb: 0.5 }}>
                Release Notes & Version History
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                Deployed version and changelog for MandirMitra
              </Typography>
            </Box>
          </Box>
        </Paper>

        {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}

        {version && (
          <>
            {/* Current Version Card */}
            <Paper sx={{ p: 3, mb: 3, border: '2px solid #FF9933' }}>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <VerifiedIcon sx={{ fontSize: 32, color: 'success.main' }} />
                <Box flex={1}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Current Deployed Version
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    This is the version running on your instance
                  </Typography>
                </Box>
                <Chip
                  label={`v${version.version}`}
                  color="primary"
                  sx={{ fontWeight: 700, fontSize: '1.1rem', py: 2.5, px: 1 }}
                />
              </Box>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body2" color="text.secondary">
                Released: {new Date(version.released_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </Typography>
            </Paper>

            {/* Tabs */}
            <Paper sx={{ mb: 3 }}>
              <Tabs value={tabValue} onChange={(e, val) => setTabValue(val)} sx={{ borderBottom: '1px solid #eee' }}>
                <Tab label="What's New" icon={<InfoIcon />} iconPosition="start" />
                <Tab label="Features in This Release" icon={<NewReleasesIcon />} iconPosition="start" />
                <Tab label="Security & Stability" icon={<SecurityIcon />} iconPosition="start" />
              </Tabs>

              {/* Tab 1: What's New */}
              {tabValue === 0 && (
                <Box sx={{ p: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                    v1.2.0 — Stable Production Release (April 14, 2026)
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <Card>
                        <CardContent>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                            🎯 Quick Token Counter Mode
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Fast one-click seva booking without login. Perfect for temple counters to process instant bookings.
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12}>
                      <Card>
                        <CardContent>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                            📧 Seva Renewal Reminders
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Automated email and SMS reminders sent 1 month before seva subscriptions expire. Keeps devotees engaged with the temple.
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12}>
                      <Card>
                        <CardContent>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                            🌍 Multilingual Public Portal
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Public seva and donation portal now supports English, Kannada, and Hindi. Devotees can interact in their preferred language.
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {/* Tab 2: Features */}
              {tabValue === 1 && (
                <Box sx={{ p: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                    Features Included in v1.2.0
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {(version.features || []).map((feature, idx) => (
                      <Box key={idx} sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                        <NewReleasesIcon sx={{ color: 'primary.main', mt: 0.5, flexShrink: 0 }} />
                        <Typography variant="body2">{feature}</Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

              {/* Tab 3: Security */}
              {tabValue === 2 && (
                <Box sx={{ p: 3 }}>
                  <Alert severity="success" sx={{ mb: 2 }}>
                    ✅ This version is marked as <strong>STABLE</strong> for production use.
                  </Alert>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                    Security & Reliability Improvements
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                          🔒 Idempotency Protection
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          All public payments now validate idempotency keys. Prevents duplicate charges from network retries or accidental double-clicks.
                        </Typography>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                          📊 Formal Audit Logging
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          All public payments logged with timestamp, IP address, and devotee details. Compliance-ready for audits and regulatory requirements.
                        </Typography>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                          ⚡ Rate Limiting
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Public endpoints protected with rate limiting (10/min payments, 30/min sevas). Prevents abuse and DDoS attempts.
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                </Box>
              )}
            </Paper>

            {/* Rollback Info */}
            <Alert icon={<InfoIcon />} severity="info">
              <Typography variant="body2">
                <strong>Rollback Available:</strong> If you need to revert to a previous stable version, contact platform support with the version tag. This is a multi-tenant system — rollback will affect all temples on this instance.
              </Typography>
            </Alert>
          </>
        )}
      </Box>
    </Layout>
  );
}
