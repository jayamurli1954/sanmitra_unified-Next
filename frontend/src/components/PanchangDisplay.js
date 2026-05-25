import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Divider,
  Alert,
  Stack,
  Card,
  CardContent,
  Button,
  Accordion,
  AccordionSummary,
  List,
  ListItem,
  ListItemText,
  AccordionDetails,
  Tooltip,
  IconButton,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PrintIcon from '@mui/icons-material/Print';
import ShareIcon from '@mui/icons-material/Share';
import InfoIcon from '@mui/icons-material/InfoOutlined';

const TITHI_NAMES = [
  'Pratipada',
  'Dwitiya',
  'Tritiya',
  'Chaturthi',
  'Panchami',
  'Shashthi',
  'Saptami',
  'Ashtami',
  'Navami',
  'Dashami',
  'Ekadashi',
  'Dwadashi',
  'Trayodashi',
  'Chaturdashi',
];

const getNextTithiName = (tithi = {}) => {
  const number = Number(tithi.number);
  const paksha = tithi.paksha || '';
  if (!number || number < 1 || number > 15) return 'Next tithi';
  if (number < 14) return `${paksha} ${TITHI_NAMES[number]}`.trim();
  if (number === 14) return paksha === 'Shukla' ? 'Shukla Purnima' : 'Krishna Amavasya';
  return paksha === 'Shukla' ? 'Krishna Pratipada' : 'Shukla Pratipada';
};

const formatTransitionTime = (value, fallback) => {
  if (fallback) return fallback;
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

const formatCountdown = (diff) => {
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);
  return `${hours}h ${minutes}m ${seconds}s`;
};

/**
 * Enhanced Panchang Display Component
 * Features: Verification badges, live countdown, quality indicators, 8-period breakdown, print support
 */
function PanchangDisplay({ data, settings, compact = false, selectedDate, onDateChange }) {
  const [timeLeft, setTimeLeft] = useState({});

  // Default settings
  const defaultSettings = {
    show_tithi: true,
    show_nakshatra: true,
    show_yoga: true,
    show_karana: true,
    show_sun_timings: true,
    show_rahu_kaal: true,
    show_yamaganda: true,
    show_gulika: true,
    show_abhijit_muhurat: true,
    display_mode: 'full',
    primary_language: 'English',
    show_on_dashboard: true,
  };

  const displaySettings = settings || defaultSettings;
  const hinduDate = data?.date?.hindu || {};
  const vikramSamvat = hinduDate.samvat_vikram || hinduDate.vikram_samvat || '';
  const shakaSamvat = hinduDate.samvat_shaka || hinduDate.shaka_samvat || '';
  const monthPaksha = [hinduDate.month, hinduDate.paksha && `${hinduDate.paksha} Paksha`]
    .filter(Boolean)
    .join(' ');
  // Panchang calculation module is now active; show Amrita/Varjyam display in UI.
  const showAmrita = true;
  const showVarjyam = true;
  const amritaPreviewOnly =
    data?.calculation_metadata?.amrita_kalam_verified !== true
    && data?.calculation_metadata?.amrita_kalam_preview === true;
  const varjyamPreviewOnly =
    data?.calculation_metadata?.varjyam_verified !== true
    && data?.calculation_metadata?.varjyam_preview === true;

  // Live countdown timer for tithi/nakshatra transitions
  useEffect(() => {
    if (!data || compact) return;

    const updateCountdown = () => {
      const now = new Date();
      const calculations = {};

      // Tithi countdown
      if (data.panchang?.tithi?.end_time) {
        const tithi = data.panchang.tithi;
        const tithiEnd = new Date(tithi.end_time);
        const diff = tithiEnd - now;
        const endTime = formatTransitionTime(tithi.end_time, tithi.end_time_formatted);
        const nextTithi = getNextTithiName(tithi);

        if (diff > 0) {
          calculations.tithi = `Ends ${endTime} -> ${nextTithi} (${formatCountdown(diff)})`;
        } else {
          calculations.tithi = `Ended ${endTime}; ${nextTithi} active now`;
        }
      }

      // Nakshatra countdown
      if (data.panchang?.nakshatra?.end_time) {
        const nakshatra = data.panchang.nakshatra;
        const nakshatraEnd = new Date(nakshatra.end_time);
        const diff = nakshatraEnd - now;
        const endTime = formatTransitionTime(nakshatra.end_time, nakshatra.end_time_formatted);

        if (diff > 0) {
          calculations.nakshatra = `Ends ${endTime} (${formatCountdown(diff)})`;
        } else {
          calculations.nakshatra = `Ended ${endTime}`;
        }
      }

      setTimeLeft(calculations);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);

    return () => clearInterval(interval);
  }, [data, compact]);

  if (!data) {
    return (
      <Paper sx={{ p: 2, bgcolor: '#FFF9E6' }}>
        <Typography variant="body2" color="text.secondary">
          Panchang data will be displayed here once connected to panchang service API.
        </Typography>
      </Paper>
    );
  }

  const formatTime = (timeString) => {
    if (!timeString || timeString === 'N/A') return 'N/A';

    // If already formatted with AM/PM (e.g., from backend moonrise calculation)
    if (typeof timeString === 'string' && (timeString.includes('AM') || timeString.includes('PM'))) {
      return timeString;
    }

    if (timeString.match(/^\d{2}:\d{2}:\d{2}$/)) {
      const [hours, minutes] = timeString.split(':');
      const hour = parseInt(hours);
      const min = minutes;
      const period = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
      return `${displayHour}:${min} ${period}`;
    }

    const date = new Date(timeString);
    if (isNaN(date.getTime())) return 'N/A';
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getTimeAgo = (isoString) => {
    if (!isoString) return 'recently';
    const now = new Date();
    const generated = new Date(isoString);
    const diffSeconds = Math.floor((now - generated) / 1000);

    if (diffSeconds < 60) return 'just now';
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} minutes ago`;
    return `${Math.floor(diffSeconds / 3600)} hours ago`;
  };

  const handlePrint = () => {
    window.print();
  };

  const handleShare = async () => {
    const shareData = {
      title: 'Today\'s Panchang',
      text: `Check out today's Panchang for ${data.location?.city || 'your location'}`,
      url: window.location.href
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.log('Error sharing:', err);
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(window.location.href);
      alert('Link copied to clipboard!');
    }
  };

  // Compact info card component
  const InfoCard = ({ title, value, color = '#1976d2', icon = '' }) => (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        border: '1px solid #e0e0e0',
        borderLeft: `4px solid ${color}`,
        height: '100%'
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        {icon} {title}
      </Typography>
      <Typography variant="body1" sx={{ fontWeight: 600, color: color }}>
        {value}
      </Typography>
    </Paper>
  );

  // Quality indicator with stars
  const QualityIndicator = ({ quality }) => {
    if (!quality) return null;

    const stars = '⭐'.repeat(quality.stars) + '☆'.repeat(5 - quality.stars);

    return (
      <Box sx={{ mt: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: quality.color }}>
            {stars}
          </Typography>
          <Chip
            label={quality.label}
            size="small"
            sx={{ bgcolor: quality.color, color: '#fff', fontWeight: 600 }}
          />
        </Box>
      </Box>
    );
  };

  // Compact view for dashboard
  if (compact) {
    return (
      <Paper sx={{ p: 2, bgcolor: '#FFF9E6', boxShadow: 2 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#FF9933', mb: 2 }}>
          📅 Today's Panchang
        </Typography>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          {formatDate(data.date?.gregorian?.date)}
        </Typography>

        <Box sx={{ mt: 2 }}>
          {displaySettings.show_tithi && data.panchang?.tithi && (
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                Tithi:
              </Typography>
              <Typography variant="body2">
                {data.panchang.tithi.full_name || data.panchang.tithi.name}
              </Typography>
            </Box>
          )}

          {settings?.show_nakshatra && data.panchang?.nakshatra && (
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                Nakshatra:
              </Typography>
              <Chip
                label={data.panchang.nakshatra.name}
                size="small"
                sx={{ bgcolor: '#E3F2FD', color: '#1565C0', fontWeight: 'bold' }}
              />
            </Box>
          )}

          {settings?.show_sun_timings && data.sun_moon && (
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="body2">
                🌅 {formatTime(data.sun_moon.sunrise)}  🌇 {formatTime(data.sun_moon.sunset)}
              </Typography>
            </Box>
          )}
        </Box>
      </Paper>
    );
  }

  // Full page view - ENHANCED VERSION
  return (
    <Box className="panchang-display">
      <style>
        {`
          @media print {
            .no-print {
              display: none !important;
            }
            .panchang-display {
              padding: 20px;
            }
            body {
              print-color-adjust: exact;
              -webkit-print-color-adjust: exact;
            }
          }
        `}
      </style>

      {/* CALCULATION BADGES HEADER */}
      <Paper sx={{ p: 2, mb: 2, bgcolor: '#E8F5E9', border: '2px solid #4CAF50' }} className="print-header">
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={8}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#2E7D32', mb: 1 }}>
              📅 Today's Panchang
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 0.5 }}>
              <Chip
                icon={<span>✓</span>}
                label="Calculated with Swiss Ephemeris"
                size="small"
                sx={{ bgcolor: '#4CAF50', color: '#fff', fontWeight: 600 }}
              />
              <Chip
                label={`🎯 Lahiri Ayanamsa (${data.calculation_metadata?.ayanamsa_value ? data.calculation_metadata.ayanamsa_value.toFixed(2) : 'N/A'}°)`}
                size="small"
                sx={{ bgcolor: '#2196F3', color: '#fff', fontWeight: 600 }}
              />
              <Chip
                label={`⏱️ Calculated: ${data.calculation_metadata?.generated_at ? getTimeAgo(data.calculation_metadata.generated_at) : 'recently'}`}
                size="small"
                sx={{ bgcolor: '#FF9800', color: '#fff', fontWeight: 600 }}
              />
              {data.location && (
                <Chip
                  label={`📍 ${data.location.city || 'Location'} (${data.location.latitude ? parseFloat(data.location.latitude).toFixed(2) : '0'}°N, ${data.location.longitude ? parseFloat(data.location.longitude).toFixed(2) : '0'}°E)`}
                  size="small"
                  sx={{ bgcolor: '#9C27B0', color: '#fff', fontWeight: 600 }}
                />
              )}
            </Stack>
          </Grid>
          <Grid item xs={12} md={4} sx={{ textAlign: { xs: 'left', md: 'right' } }} className="no-print">
            <Button
              variant="outlined"
              startIcon={<PrintIcon />}
              onClick={handlePrint}
              sx={{ mr: 1 }}
            >
              Print
            </Button>
            <Button
              variant="outlined"
              startIcon={<ShareIcon />}
              onClick={handleShare}
            >
              Share
            </Button>
          </Grid>
        </Grid>

        {/* Accuracy Meter */}
        <Box sx={{ mt: 2, p: 1.5, bgcolor: '#fff', borderRadius: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: '#2E7D32' }}>
            Calculation Method:
          </Typography>
          <Box sx={{ bgcolor: '#E8F5E9', height: 8, borderRadius: 1, mt: 0.5, overflow: 'hidden' }}>
            <Box sx={{ bgcolor: '#4CAF50', height: '100%', width: '85%' }} />
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            ℹ️ Calculated with {data.calculation_metadata?.verified_against}. Compare with the temple's preferred panchang before final muhurta use.
          </Typography>
        </Box>
      </Paper>

      {/* DATE HEADER */}
      <Paper sx={{ p: 2, mb: 2, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
        <Grid container alignItems="center" spacing={2}>
          {/* Date text — left */}
          <Grid item xs={12} sm={8}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#fff', mb: 0.5 }}>
              📅 {formatDate(data.date?.gregorian?.date)}
            </Typography>
            {data.date?.hindu && (
              <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 0.5 }}>
                {vikramSamvat && (
                  <Chip
                    label={`Vikram Samvat ${vikramSamvat}`}
                    size="small"
                    sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: '#fff', fontWeight: 500 }}
                  />
                )}
                {shakaSamvat && (
                  <Chip
                    label={`Shaka Samvat ${shakaSamvat}`}
                    size="small"
                    sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: '#fff', fontWeight: 500 }}
                  />
                )}
                {monthPaksha && (
                  <Chip
                    label={monthPaksha}
                    size="small"
                    sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: '#fff', fontWeight: 500 }}
                  />
                )}
                {data.date.hindu.samvatsara && (
                  <Chip
                    label={`${data.date.hindu.samvatsara.name} (${data.date.hindu.samvatsara.cycle_year}/60)`}
                    size="small"
                    sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: '#fff', fontWeight: 500 }}
                  />
                )}
              </Stack>
            )}
          </Grid>

          {/* Date picker — right, shown only when onDateChange is provided */}
          {onDateChange && (
            <Grid item xs={12} sm={4}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: { xs: 'flex-start', sm: 'flex-end' }, gap: 0.5 }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>
                  View Panchang for:
                </Typography>
                <input
                  type="date"
                  value={selectedDate || new Date().toISOString().split('T')[0]}
                  onChange={(e) => onDateChange(e.target.value)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: 6,
                    border: '2px solid rgba(255,255,255,0.7)',
                    background: 'rgba(255,255,255,0.15)',
                    color: '#fff',
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: 'pointer',
                    outline: 'none',
                    colorScheme: 'dark',
                  }}
                />
                {selectedDate !== new Date().toISOString().split('T')[0] && (
                  <Box
                    component="button"
                    onClick={() => onDateChange(new Date().toISOString().split('T')[0])}
                    sx={{
                      background: 'rgba(255,255,255,0.25)', border: '1px solid rgba(255,255,255,0.6)',
                      borderRadius: 1, color: '#fff', fontSize: 11, fontWeight: 600,
                      px: 1, py: 0.3, cursor: 'pointer', '&:hover': { background: 'rgba(255,255,255,0.4)' },
                    }}
                  >
                    ↩ Today
                  </Box>
                )}
              </Box>
            </Grid>
          )}
        </Grid>
      </Paper>

      {/* LIVE COUNTDOWN BANNER */}
      {(timeLeft.tithi || timeLeft.nakshatra) && (
        <Paper sx={{ p: 1.5, mb: 2, bgcolor: '#FFF3E0', border: '2px solid #FF9800' }} className="no-print">
          <Grid container spacing={2}>
            {timeLeft.tithi && (
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    ⏱️ Tithi changes in:
                  </Typography>
                  <Chip
                    label={timeLeft.tithi}
                    size="small"
                    sx={{ bgcolor: '#FF9800', color: '#fff', fontWeight: 700 }}
                  />
                </Box>
              </Grid>
            )}
            {timeLeft.nakshatra && (
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    ⏱️ Nakshatra changes in:
                  </Typography>
                  <Chip
                    label={timeLeft.nakshatra}
                    size="small"
                    sx={{ bgcolor: '#1976D2', color: '#fff', fontWeight: 700 }}
                  />
                </Box>
              </Grid>
            )}
          </Grid>
        </Paper>
      )}

      {/* SOUTH INDIA FESTIVALS & SPECIAL NOTES (Multilingual) */}
      {data.south_india_special && data.south_india_special.length > 0 && (
        <Paper sx={{ p: 2, mb: 2, bgcolor: '#E8F5E9', border: '2px solid #4CAF50' }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: '#2E7D32', mb: 1.5 }}>
            🪔 South India Festivals & Observances (ಕನ್ನಡ | संस्कृत)
          </Typography>
          <Stack spacing={1.5}>
            {data.south_india_special.map((item, index) => (
              <Paper
                key={index}
                elevation={0}
                sx={{
                  p: 2,
                  bgcolor: '#fff',
                  borderLeft: `4px solid ${item.type === 'festival' ? '#4CAF50' : '#FF9800'}`
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="body1" sx={{ fontWeight: 700, color: item.type === 'festival' ? '#2E7D32' : '#F57C00' }}>
                    {item.type === 'festival' ? '🎉' : '📝'} {item.english || item.text}
                  </Typography>
                </Box>
                {item.text && item.text.includes('|') && (
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'inherit' }}>
                    {item.text}
                  </Typography>
                )}
                {item.kannada && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, fontFamily: 'inherit' }}>
                    <strong>Kannada:</strong> {item.kannada}
                  </Typography>
                )}
                {item.sanskrit && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, fontFamily: 'inherit' }}>
                    <strong>Sanskrit:</strong> {item.sanskrit}
                  </Typography>
                )}
              </Paper>
            ))}
          </Stack>
        </Paper>
      )}

      {/* FESTIVAL ALERTS */}
      {data.festivals && data.festivals.length > 0 && (
        <Paper sx={{ p: 2, mb: 2, bgcolor: '#FFF3E0', border: '2px solid #FF9800' }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: '#E65100', mb: 1.5 }}>
            🎉 Today's Special Significance
          </Typography>
          <Grid container spacing={2}>
            {data.festivals.map((festival, index) => (
              <Grid item xs={12} key={index}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: '#fff',
                    borderLeft: `4px solid ${festival.importance === 'major' ? '#D32F2F' : '#FF9800'}`
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#E65100' }}>
                      {festival.type === 'major' ? '🎉' : festival.type === 'fasting' ? '🙏' : '🕉️'} {festival.name}
                    </Typography>
                    <Chip
                      label={festival.importance?.toUpperCase()}
                      size="small"
                      sx={{
                        bgcolor: festival.importance === 'major' ? '#D32F2F' : '#FF9800',
                        color: '#fff',
                        fontWeight: 600
                      }}
                    />
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {festival.description}
                  </Typography>

                  {festival.observances && festival.observances.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                        How to Observe:
                      </Typography>
                      <ul style={{ margin: 0, paddingLeft: '20px' }}>
                        {festival.observances.map((obs, i) => (
                          <li key={i}>
                            <Typography variant="body2">{obs}</Typography>
                          </li>
                        ))}
                      </ul>
                    </Box>
                  )}

                  {festival.benefits && festival.benefits.length > 0 && (
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                        ✨ Benefits:
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 0.5 }}>
                        {festival.benefits.map((benefit, i) => (
                          <Chip
                            key={i}
                            label={benefit}
                            size="small"
                            sx={{ bgcolor: '#E8F5E9', color: '#2E7D32' }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      <Grid container spacing={2}>
        {/* PANCHANG - FIVE LIMBS WITH QUALITY INDICATORS */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, color: '#FF6B35' }}>
              पञ्चाङ्ग - Five Limbs
            </Typography>
            <Grid container spacing={2}>
              {/* Tithi with Quality */}
              {displaySettings.show_tithi && data.panchang?.tithi && (
                <Grid item xs={12} sm={6}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      border: '1px solid #e0e0e0',
                      borderLeft: `4px solid ${data.panchang.tithi.quality?.color || '#2E7D32'}`,
                      height: '100%'
                    }}
                  >
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      🌙 TITHI (तिथि)
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600, color: data.panchang.tithi.quality?.color || '#2E7D32' }}>
                      {data.panchang.tithi.full_name || data.panchang.tithi.name}
                    </Typography>

                    <QualityIndicator quality={data.panchang.tithi.quality} />

                    {data.panchang.tithi.quality && (
                      <Box sx={{ mt: 1.5 }}>
                        {data.panchang.tithi.quality.good_for && data.panchang.tithi.quality.good_for.length > 0 && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: '#4CAF50' }}>
                              ✅ Good for:
                            </Typography>
                            <Box sx={{ mt: 0.5 }}>
                              {data.panchang.tithi.quality.good_for.map((item, i) => (
                                <Chip
                                  key={i}
                                  label={item}
                                  size="small"
                                  sx={{ m: 0.25, fontSize: '0.7rem' }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}

                        {data.panchang.tithi.quality.avoid && data.panchang.tithi.quality.avoid.length > 0 && (
                          <Box>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: '#D32F2F' }}>
                              ⚠️ Avoid:
                            </Typography>
                            <Box sx={{ mt: 0.5 }}>
                              {data.panchang.tithi.quality.avoid.map((item, i) => (
                                <Chip
                                  key={i}
                                  label={item}
                                  size="small"
                                  sx={{ m: 0.25, fontSize: '0.7rem', bgcolor: '#FFEBEE' }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}
                      </Box>
                    )}
                  </Paper>
                </Grid>
              )}

              {/* Nakshatra with Quality */}
              {displaySettings.show_nakshatra && data.panchang?.nakshatra && (
                <Grid item xs={12} sm={6}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      border: '1px solid #e0e0e0',
                      borderLeft: `4px solid ${data.panchang.nakshatra.quality?.color || '#1565C0'}`,
                      height: '100%'
                    }}
                  >
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      ⭐ NAKSHATRA (नक्षत्र)
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600, color: data.panchang.nakshatra.quality?.color || '#1565C0' }}>
                      {data.panchang.nakshatra.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Pada {data.panchang.nakshatra.pada || 1}
                    </Typography>

                    <QualityIndicator quality={data.panchang.nakshatra.quality} />

                    {data.panchang.nakshatra.quality && (
                      <Box sx={{ mt: 1.5 }}>
                        <Grid container spacing={1} sx={{ fontSize: '0.75rem' }}>
                          {data.panchang.nakshatra.quality.deity && (
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                🕉️ Deity:
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600 }}>
                                {data.panchang.nakshatra.quality.deity.split('(')[0]}
                              </Typography>
                            </Grid>
                          )}
                          {data.panchang.nakshatra.quality.ruling_planet && (
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                🪐 Planet:
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600 }}>
                                {data.panchang.nakshatra.quality.ruling_planet}
                              </Typography>
                            </Grid>
                          )}
                          {data.panchang.nakshatra.quality.nature && (
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                🔮 Nature:
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600 }}>
                                {data.panchang.nakshatra.quality.nature}
                              </Typography>
                            </Grid>
                          )}
                          {data.panchang.nakshatra.quality.element && (
                            <Grid item xs={6}>
                              <Typography variant="caption" color="text.secondary">
                                ⚡ Element:
                              </Typography>
                              <Typography variant="caption" sx={{ display: 'block', fontWeight: 600 }}>
                                {data.panchang.nakshatra.quality.element}
                              </Typography>
                            </Grid>
                          )}
                        </Grid>

                        {data.panchang.nakshatra.quality.good_for && data.panchang.nakshatra.quality.good_for.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: '#4CAF50' }}>
                              ✅ Good for:
                            </Typography>
                            <Box sx={{ mt: 0.5 }}>
                              {data.panchang.nakshatra.quality.good_for.slice(0, 3).map((item, i) => (
                                <Chip
                                  key={i}
                                  label={item}
                                  size="small"
                                  sx={{ m: 0.25, fontSize: '0.7rem' }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}

                        {data.panchang.nakshatra.quality.avoid && data.panchang.nakshatra.quality.avoid.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: '#D32F2F' }}>
                              ⚠️ Avoid:
                            </Typography>
                            <Box sx={{ mt: 0.5 }}>
                              {data.panchang.nakshatra.quality.avoid.slice(0, 2).map((item, i) => (
                                <Chip
                                  key={i}
                                  label={item}
                                  size="small"
                                  sx={{ m: 0.25, fontSize: '0.7rem', bgcolor: '#FFEBEE' }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}
                      </Box>
                    )}
                  </Paper>
                </Grid>
              )}

              {/* Yoga */}
              {displaySettings.show_yoga && data.panchang?.yoga && (
                <Grid item xs={12} sm={6}>
                  <InfoCard
                    title="YOGA (योग)"
                    value={data.panchang.yoga.name}
                    color={data.panchang.yoga.is_inauspicious ? "#D32F2F" : "#7B1FA2"}
                    icon="🔗"
                  />
                </Grid>
              )}

              {/* Karana */}
              {displaySettings.show_karana && data.panchang?.karana && (
                <Grid item xs={12} sm={6}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 1.5,
                      border: '1px solid #e0e0e0',
                      borderLeft: '4px solid #F57C00',
                      height: '100%'
                    }}
                  >
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      ⚡ KARANA (करण)
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#F57C00' }}>
                      {data.panchang.karana.first_half?.name} | {data.panchang.karana.second_half?.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      1st Half | 2nd Half
                    </Typography>
                    {data.panchang.karana.is_bhadra && (
                      <Chip
                        label="Vishti/Bhadra - Inauspicious"
                        size="small"
                        sx={{ mt: 1, bgcolor: '#D32F2F', color: '#fff' }}
                      />
                    )}
                  </Paper>
                </Grid>
              )}

              {/* Vara */}
              {data.panchang?.vara && (
                <Grid item xs={12} sm={6}>
                  <InfoCard
                    title="VARA (वार)"
                    value={`${data.panchang.vara.name} (${data.panchang.vara.sanskrit})`}
                    color="#00796B"
                    icon="📆"
                  />
                </Grid>
              )}

              {/* Moon Sign */}
              {data.moon_sign && (
                <Grid item xs={12} sm={6}>
                  <InfoCard
                    title="MOON SIGN (राशि)"
                    value={data.moon_sign.name}
                    color="#9C27B0"
                    icon="🌙"
                  />
                </Grid>
              )}
            </Grid>
          </Paper>
        </Grid>

        {/* TIMINGS COLUMN */}
        <Grid item xs={12} md={4}>
          <Stack spacing={2}>
            {/* Sunrise/Sunset */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5, color: '#FF6B35' }}>
                ☀️ Sun & Moon
              </Typography>
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">🌅 Sunrise</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatTime(data.sun_moon?.sunrise)}
                  </Typography>
                </Box>
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">🌇 Sunset</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatTime(data.sun_moon?.sunset)}
                  </Typography>
                </Box>
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">🌙 Moonrise</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatTime(data.sun_moon?.moonrise)}
                  </Typography>
                </Box>
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">🌙 Moonset</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatTime(data.sun_moon?.moonset)}
                  </Typography>
                </Box>
              </Stack>
            </Paper>

            {/* Ayana & Ruthu */}
            {(data.ayana || data.ruthu) && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5, color: '#FF6B35' }}>
                  🌍 Season & Ayana
                </Typography>
                <Stack spacing={1}>
                  {data.ayana && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">Ayana</Typography>
                      <Chip label={data.ayana} size="small" sx={{ bgcolor: '#E3F2FD', color: '#1565C0' }} />
                    </Box>
                  )}
                  {data.ruthu && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">Ruthu</Typography>
                      <Chip label={data.ruthu} size="small" sx={{ bgcolor: '#E8F5E9', color: '#2E7D32' }} />
                    </Box>
                  )}
                </Stack>
              </Paper>
            )}
          </Stack>
        </Grid>

        {/* AUSPICIOUS TIMES */}
        {data.auspicious_times && (
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, bgcolor: '#E8F5E9', border: '2px solid #4CAF50' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#2E7D32', mb: 1.5 }}>
                ✅ Auspicious Timings
              </Typography>
              <Stack spacing={1}>
                {displaySettings.show_abhijit_muhurat && data.auspicious_times.abhijit_muhurat && (
                  <Box sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        🌟 Abhijit Muhurat
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#2E7D32' }}>
                        {formatTime(data.auspicious_times.abhijit_muhurat.start)} - {formatTime(data.auspicious_times.abhijit_muhurat.end)}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Most auspicious time of the day • Duration: {Math.round(data.auspicious_times.abhijit_muhurat.duration_minutes)} mins
                    </Typography>
                  </Box>
                )}
                {data.auspicious_times.brahma_muhurat && (
                  <Box sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        🕉️ Brahma Muhurta
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#2E7D32' }}>
                        {formatTime(data.auspicious_times.brahma_muhurat.start)} - {formatTime(data.auspicious_times.brahma_muhurat.end)}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Pre-dawn meditation • Duration: {data.auspicious_times.brahma_muhurat.duration_minutes} mins
                    </Typography>
                  </Box>
                )}
                {showAmrita && data.auspicious_times.amrita_kalam && (
                  <Box sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        🍯 Amrita Kalam
                        {amritaPreviewOnly ? ' (Preview)' : ''}
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#2E7D32' }}>
                        {formatTime(data.auspicious_times.amrita_kalam.start)} - {formatTime(data.auspicious_times.amrita_kalam.end)}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Nectar period • Duration: {Math.round(data.auspicious_times.amrita_kalam.duration_minutes)} mins
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Paper>
          </Grid>
        )}

        {/* INAUSPICIOUS TIMES */}
        {data.inauspicious_times && (
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, bgcolor: '#FFEBEE', border: '2px solid #F44336' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#C62828', mb: 1.5 }}>
                ⚠️ Inauspicious Timings
              </Typography>
              <Stack spacing={1}>
                {displaySettings.show_rahu_kaal && data.inauspicious_times.rahu_kaal && (
                  <Box sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        🔴 Rahu Kala
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#C62828' }}>
                        {formatTime(data.inauspicious_times.rahu_kaal.start)} - {formatTime(data.inauspicious_times.rahu_kaal.end)}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Avoid new activities • Duration: {Math.round(data.inauspicious_times.rahu_kaal.duration_minutes)} mins
                    </Typography>
                  </Box>
                )}
                {displaySettings.show_yamaganda && data.inauspicious_times.yamaganda && (
                  <Box sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        ⚫ Yamaganda Kala
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#C62828' }}>
                        {formatTime(data.inauspicious_times.yamaganda.start)} - {formatTime(data.inauspicious_times.yamaganda.end)}
                      </Typography>
                    </Box>
                  </Box>
                )}
                {displaySettings.show_gulika && data.inauspicious_times.gulika && (
                  <Box sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        🟤 Gulika Kala
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#C62828' }}>
                        {formatTime(data.inauspicious_times.gulika.start)} - {formatTime(data.inauspicious_times.gulika.end)}
                      </Typography>
                    </Box>
                  </Box>
                )}
                {data.additional_inauspicious_times?.dur_muhurta && data.additional_inauspicious_times.dur_muhurta.map((dur, idx) => (
                  <Box key={idx} sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        ⚠️ Dur Muhurta
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#C62828' }}>
                        {formatTime(dur.start)} - {formatTime(dur.end)}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Inauspicious period • Duration: {dur.duration_minutes} mins
                    </Typography>
                  </Box>
                ))}
                {showVarjyam && data.additional_inauspicious_times?.varjyam && data.additional_inauspicious_times.varjyam.map((varj, idx) => (
                  <Box key={idx} sx={{ bgcolor: '#fff', p: 1.5, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        🚫 Varjyam
                        {varjyamPreviewOnly ? ' (Preview)' : ''}
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, color: '#C62828' }}>
                        {formatTime(varj.start)} - {formatTime(varj.end)}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      Avoid starting new ventures • Duration: {varj.duration_minutes} mins
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </Paper>
          </Grid>
        )}

        {/* 8 PERIODS OF THE DAY */}
        {data.day_periods && data.day_periods.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, color: '#FF6B35' }}>
                📊 Complete Day Division (8 Periods)
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Each day is divided into 8 equal periods from sunrise to sunset. Each period is ruled by a different planet.
              </Typography>

              <Grid container spacing={1}>
                {data.day_periods.map((period, idx) => {
                  let bgcolor = '#E3F2FD';
                  let borderColor = '#2196F3';
                  let textColor = '#1565C0';

                  if (period.quality === 'rahu') {
                    bgcolor = '#FFEBEE';
                    borderColor = '#F44336';
                    textColor = '#C62828';
                  } else if (period.quality === 'yama' || period.quality === 'gulika') {
                    bgcolor = '#FFF3E0';
                    borderColor = '#FF9800';
                    textColor = '#E65100';
                  } else if (period.quality === 'good') {
                    bgcolor = '#E8F5E9';
                    borderColor = '#4CAF50';
                    textColor = '#2E7D32';
                  }

                  return (
                    <Grid item xs={12} sm={6} md={3} key={idx}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 1.5,
                          bgcolor,
                          border: `2px solid ${borderColor}`,
                          height: '100%'
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 700, color: textColor }}>
                          Period {period.period} • 🪐 {period.ruler}
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5 }}>
                          {formatTime(period.start)} - {formatTime(period.end)}
                        </Typography>
                        {period.note && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                            {period.note}
                          </Typography>
                        )}
                        {period.special_type && (
                          <Chip
                            label={period.special_type.toUpperCase()}
                            size="small"
                            sx={{
                              mt: 0.5,
                              bgcolor: borderColor,
                              color: '#fff',
                              fontSize: '0.65rem',
                              height: '20px'
                            }}
                          />
                        )}
                      </Paper>
                    </Grid>
                  );
                })}
              </Grid>
            </Paper>
          </Grid>
        )}

        {/* SPECIAL NOTES */}
        {data.special_notes && data.special_notes.summary && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2, bgcolor: '#FFF9C4', border: '2px solid #FBC02D' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#F57F17', mb: 1.5 }}>
                📝 Special Notes for Today
              </Typography>
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.8 }}>
                {data.special_notes.summary}
              </Typography>
              {data.special_notes.recommendations && data.special_notes.recommendations.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, color: '#2E7D32' }}>
                    ✅ Recommendations:
                  </Typography>
                  <List dense>
                    {data.special_notes.recommendations.map((rec, idx) => (
                      <ListItem key={idx} sx={{ py: 0.5 }}>
                        <ListItemText
                          primary={rec}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
              {data.special_notes.avoid && data.special_notes.avoid.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, color: '#C62828' }}>
                    ⚠️ Avoid:
                  </Typography>
                  <List dense>
                    {data.special_notes.avoid.map((item, idx) => (
                      <ListItem key={idx} sx={{ py: 0.5 }}>
                        <ListItemText
                          primary={item}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* FOOTER - DISCLAIMER */}
      <Paper sx={{ p: 2, mt: 2, bgcolor: '#F5F5F5' }} className="print-footer">
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
          ⚠️ Important Note:
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This panchang is calculated using Swiss Ephemeris with Lahiri Ayanamsa. For specific religious ceremonies
          and personal muhurats, compare with the temple's preferred panchang source and consult a qualified pandit or astrologer.
        </Typography>
      </Paper>
    </Box>
  );
}

export default PanchangDisplay;
