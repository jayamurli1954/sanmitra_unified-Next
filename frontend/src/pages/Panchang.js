import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Button,
  TextField,
  MenuItem,
  Autocomplete,
  List,
  ListItem,
  ListItemText,
  Chip,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import Layout from '../components/Layout';
import PanchangDisplay from '../components/PanchangDisplay';
import api from '../services/api';

function Panchang() {
  const navigate = useNavigate();
  const nakshatraOptions = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta',
    'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati',
  ];
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [settings, setSettings] = useState(null);
  const [panchangData, setPanchangData] = useState(null);
  const [selectedNakshatra, setSelectedNakshatra] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [nakshatraMatches, setNakshatraMatches] = useState([]);
  const [dateLookup, setDateLookup] = useState(null);
  const [wizardError, setWizardError] = useState('');
  const [nakshatraLoading, setNakshatraLoading] = useState(false);
  const [dateLookupLoading, setDateLookupLoading] = useState(false);
  const [cityOptions, setCityOptions] = useState([]);
  const [selectedCity, setSelectedCity] = useState(null);

  useEffect(() => {
    fetchPanchangCities();
    fetchPanchangData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedNakshatra && panchangData?.panchang?.nakshatra?.name) {
      setSelectedNakshatra(panchangData.panchang.nakshatra.name);
    }
  }, [panchangData, selectedNakshatra]);

  // Fetch panchang whenever selectedDate changes
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    if (selectedDate && selectedDate !== today) {
      fetchPanchangForDate(selectedDate);
    } else if (selectedDate === today) {
      fetchPanchangData();
    }
  }, [selectedDate]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedLocationParams = (city = selectedCity) => {
    if (!city) return {};
    return {
      city_name: city.name,
      latitude: city.lat,
      longitude: city.lon,
    };
  };

  const fetchPanchangCities = async () => {
    try {
      const response = await api.get('/api/v1/panchang/display-settings/cities');
      const payload = response.data;
      const options = Array.isArray(payload) ? payload : (payload?.data || []);
      setCityOptions(options);
    } catch (err) {
      console.error('Failed to load Panchang cities:', err);
    }
  };

  const fetchPanchangData = async (city = selectedCity) => {
    try {
      setLoading(true);
      setError('');

      // Fetch panchang display settings and data
      const [settingsRes, panchangRes] = await Promise.allSettled([
        api.get('/api/v1/panchang/display-settings/'),
        api.get('/api/v1/panchang/today', { params: selectedLocationParams(city) }),
      ]);

      if (settingsRes.status === 'fulfilled' && settingsRes.value.data) {
        setSettings(settingsRes.value.data);
      } else if (settingsRes.status === 'rejected') {
        console.log('Settings API failed:', settingsRes.reason);
      }

      if (panchangRes.status === 'fulfilled' && panchangRes.value.data) {
        setPanchangData(panchangRes.value.data);
      } else if (panchangRes.status === 'rejected') {
        const error = panchangRes.reason;
        let errorMsg = 'Unknown error';

        if (error?.response?.data?.detail) {
          const detail = error.response.data.detail;
          errorMsg = typeof detail === 'object' ? (detail.error || JSON.stringify(detail)) : detail;
        } else if (error?.response?.data?.message) {
          errorMsg = error.response.data.message;
        } else if (error?.message) {
          errorMsg = error.message;
        } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
          errorMsg = 'Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000';
        }

        console.error('Panchang API error:', error);
        setError(`Failed to load panchang data: ${errorMsg}`);
      }
    } catch (err) {
      console.error('Error fetching panchang data:', err);
      let errorMsg = 'Unknown error';

      if (err?.response?.data?.detail) {
        const detail = err.response.data.detail;
        errorMsg = typeof detail === 'object' ? (detail.error || JSON.stringify(detail)) : detail;
      } else if (err?.response?.data?.message) {
        errorMsg = err.response.data.message;
      } else if (err?.message) {
        errorMsg = err.message;
      } else if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error')) {
        errorMsg = 'Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000';
      }

      setError(`Failed to load panchang data: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchPanchangForDate = async (date, city = selectedCity) => {
    try {
      setLoading(true);
      setError('');
      const response = await api.get('/api/v1/panchang/on-date-full', {
        params: { target_date: date, ...selectedLocationParams(city) },
      });
      if (response.data) {
        setPanchangData(response.data);
      }
    } catch (err) {
      console.error('Error fetching panchang for date:', err);
      let errorMsg = 'Unknown error';

      if (err?.response?.data?.detail) {
        const detail = err.response.data.detail;
        errorMsg = typeof detail === 'object' ? (detail.error || JSON.stringify(detail)) : detail;
      } else if (err?.response?.data?.message) {
        errorMsg = err.response.data.message;
      } else if (err?.message) {
        errorMsg = err.message;
      }

      setError(`Failed to load panchang for selected date: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCityChange = (_event, city) => {
    setSelectedCity(city);
    const today = new Date().toISOString().split('T')[0];
    if (selectedDate && selectedDate !== today) {
      fetchPanchangForDate(selectedDate, city);
    } else {
      fetchPanchangData(city);
    }
  };

  const handleFindNakshatraDates = async () => {
    if (!selectedNakshatra) {
      setWizardError('Please select a birth star (Nakshatra).');
      return;
    }
    try {
      setWizardError('');
      setNakshatraLoading(true);
      const response = await api.get(
        `/api/v1/dashboard/sacred-events/nakshatra/${encodeURIComponent(selectedNakshatra)}?limit=8`
      );
      setNakshatraMatches(response.data?.next_occurrences || []);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to find Nakshatra dates';
      setWizardError(String(msg));
      setNakshatraMatches([]);
    } finally {
      setNakshatraLoading(false);
    }
  };

  const handleFindDateNakshatra = async () => {
    if (!selectedDate) {
      setWizardError('Please select a date.');
      return;
    }
    try {
      setWizardError('');
      setDateLookupLoading(true);
      const response = await api.get('/api/v1/panchang/on-date', {
        params: { target_date: selectedDate, ...selectedLocationParams() },
      });
      setDateLookup(response.data || null);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to find Nakshatra for date';
      setWizardError(String(msg));
      setDateLookup(null);
    } finally {
      setDateLookupLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
          <CircularProgress />
        </Box>
      </Layout>
    );
  }

  return (
    <Layout>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
            Panchang Viewer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {selectedDate === new Date().toISOString().split('T')[0] ? "Today's Panchang" : `Panchang for ${selectedDate}`}
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<SettingsIcon />}
          onClick={() => navigate('/panchang/settings')}
        >
          Display Settings
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {settings && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: '#FFF3E0' }}>
          <Typography variant="body2" color="text.secondary">
            Display Mode: <strong>{settings.display_mode}</strong> |
            Language: <strong>{settings.primary_language}</strong> |
            Show on Dashboard: <strong>{settings.show_on_dashboard ? 'Yes' : 'No'}</strong>
          </Typography>
        </Paper>
      )}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <Autocomplete
            options={cityOptions}
            value={selectedCity}
            onChange={handleCityChange}
            getOptionLabel={(option) => option?.display || `${option?.name || ''}${option?.state ? `, ${option.state}` : ''}`}
            isOptionEqualToValue={(option, value) => option?.name === value?.name && option?.state === value?.state}
            sx={{ minWidth: 280, maxWidth: 420, flex: '1 1 280px' }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Panchang Location"
                size="small"
                helperText="Select a city to recalculate without changing temple default settings"
              />
            )}
          />
          <Typography variant="body2" color="text.secondary">
            Current calculation:{' '}
            <strong>
              {panchangData?.location?.city || settings?.city_name || 'Bengaluru'}
            </strong>
            {panchangData?.location?.latitude && panchangData?.location?.longitude
              ? ` (${Number(panchangData.location.latitude).toFixed(2)}°, ${Number(panchangData.location.longitude).toFixed(2)}°)`
              : ''}
          </Typography>
        </Box>
      </Paper>

      <Card sx={{ mb: 3, boxShadow: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            Janma Nakshatra Wizard
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Use this for seva counter lookups: birth star to next dates, and date to star.
          </Typography>

          {wizardError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {wizardError}
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
                  Birth Star to Next Dates
                </Typography>
                <TextField
                  select
                  fullWidth
                  label="Select Janma Nakshatra"
                  size="small"
                  value={selectedNakshatra}
                  onChange={(e) => setSelectedNakshatra(e.target.value)}
                  sx={{ mb: 1.5 }}
                >
                  {nakshatraOptions.map((nak) => (
                    <MenuItem key={nak} value={nak}>
                      {nak}
                    </MenuItem>
                  ))}
                </TextField>
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleFindNakshatraDates}
                  disabled={nakshatraLoading}
                >
                  {nakshatraLoading ? 'Finding...' : 'Find Next Dates'}
                </Button>

                {nakshatraMatches.length > 0 && (
                  <List dense sx={{ mt: 1 }}>
                    {nakshatraMatches.map((item, idx) => (
                      <ListItem key={`${item.event_date}-${idx}`} sx={{ px: 0 }}>
                        <ListItemText
                          primary={`${item.event_date} (${item.weekday})`}
                          secondary={item.is_today ? 'Today' : `${item.days_away} days away`}
                        />
                        {item.is_today && <Chip label="Today" size="small" color="success" />}
                      </ListItem>
                    ))}
                  </List>
                )}
                {!nakshatraLoading && selectedNakshatra && nakshatraMatches.length === 0 && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    No upcoming dates found in current window. Try another star or refresh data.
                  </Typography>
                )}
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
                  Date to Nakshatra
                </Typography>
                <TextField
                  fullWidth
                  type="date"
                  label="Select Date"
                  size="small"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  sx={{ mb: 1.5 }}
                />
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleFindDateNakshatra}
                  disabled={dateLookupLoading}
                >
                  {dateLookupLoading ? 'Finding...' : 'Find Nakshatra'}
                </Button>

                {dateLookup?.panchang?.nakshatra && (
                  <Paper variant="outlined" sx={{ mt: 2, p: 1.5, bgcolor: '#fafafa' }}>
                    <Typography variant="body2">
                      <strong>Date:</strong> {dateLookup.lookup_requested_date || selectedDate}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Nakshatra:</strong> {dateLookup.panchang.nakshatra.name}
                      {dateLookup.panchang.nakshatra.pada ? ` (Pada ${dateLookup.panchang.nakshatra.pada})` : ''}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Tithi:</strong> {dateLookup.panchang?.tithi?.full_name || dateLookup.panchang?.tithi?.name || 'N/A'}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Star changes at:</strong> {dateLookup.panchang.nakshatra.end_time_formatted || 'N/A'}
                    </Typography>
                  </Paper>
                )}
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Full Panchang Display */}
      <PanchangDisplay
        data={panchangData}
        settings={settings}
        compact={false}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
      />
    </Layout>
  );
}

export default Panchang;

