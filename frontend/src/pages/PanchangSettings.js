/* eslint-disable no-irregular-whitespace */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Alert,
  Grid,
  CircularProgress,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import SaveIcon from '@mui/icons-material/Save';
import api from '../services/api';

function PanchangSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [detectingLocation, setDetectingLocation] = useState(false);

  // Location settings
  const [locationSettings, setLocationSettings] = useState({
    city_name: '',
    latitude: '',
    longitude: '',
    timezone: 'Asia/Kolkata'
  });

  // City lists
  const [cities, setCities] = useState({
    karnataka: [],
    south_india: [],
    major_cities: []
  });

  // Selected city
  const [selectedCity, setSelectedCity] = useState('');
  const [manualMode, setManualMode] = useState(false);

  useEffect(() => {
    fetchCities();
    fetchCurrentSettings();
  }, []);

  const fetchCities = async () => {
    try {
      const response = await api.get('/api/v1/panchang/display-settings/cities');
      if (response.data.success) {
        setCities(response.data.data);
      }
    } catch (err) {
      console.error('Failed to load cities:', err);
    }
  };

  const fetchCurrentSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/panchang/display-settings/');
      const settings = response.data;

      setLocationSettings({
        city_name: settings.city_name || '',
        latitude: settings.latitude || '',
        longitude: settings.longitude || '',
        timezone: settings.timezone || 'Asia/Kolkata'
      });

      setLoading(false);
    } catch (err) {
      setError('Failed to load current settings');
      setLoading(false);
    }
  };

  const handleCitySelect = (cityData) => {
    setLocationSettings({
      city_name: cityData.name,
      latitude: cityData.lat,
      longitude: cityData.lon,
      timezone: 'Asia/Kolkata'
    });
    setSelectedCity(cityData.name);
    setMessage(`Selected: ${cityData.display}`);
    setTimeout(() => setMessage(null), 3000);
  };

  const handleAutoDetect = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      return;
    }

    setDetectingLocation(true);
    setMessage('Detecting your location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude.toFixed(4);
        const lon = position.coords.longitude.toFixed(4);

        setLocationSettings({
          ...locationSettings,
          latitude: lat,
          longitude: lon,
          city_name: `Auto-detected (${lat}, ${lon})`
        });

        setMessage('Location detected successfully! Please save to apply.');
        setDetectingLocation(false);
        setManualMode(true);
      },
      (error) => {
        setError(`Failed to detect location: ${error.message}`);
        setDetectingLocation(false);
      }
    );
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      await api.put('/api/v1/panchang/display-settings/', locationSettings);

      setMessage('Location settings saved successfully! Panchang calculations will now use this location.');
      setSaving(false);

      // Reload current settings to confirm
      setTimeout(() => {
        fetchCurrentSettings();
      }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save settings');
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: '#fff', mb: 0.5 }}>
          Panchang Location Settings
        </Typography>
        <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.9)' }}>
          Configure your temple's location for accurate Panchang calculations
        </Typography>
      </Paper>

      {/* Messages */}
      {message && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2}} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Current Location Info */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
          <LocationOnIcon sx={{ mr: 1 }} /> Current Location
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">City:</Typography>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {locationSettings.city_name || 'Not set'}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="text.secondary">Latitude:</Typography>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {locationSettings.latitude || 'Not set'}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="body2" color="text.secondary">Longitude:</Typography>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {locationSettings.longitude || 'Not set'}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Auto-Detect Button */}
      <Paper sx={{ p: 3, mb: 3, bgcolor: '#E3F2FD' }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <MyLocationIcon color="primary" />
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Auto-Detect Location
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Use your browser's location to automatically set coordinates
            </Typography>
          </Box>
          <Button
            variant="contained"
            onClick={handleAutoDetect}
            disabled={detectingLocation}
            startIcon={detectingLocation ? <CircularProgress size={20} /> : <MyLocationIcon />}
          >
            {detectingLocation ? 'Detecting...' : 'Auto-Detect'}
          </Button>
        </Stack>
      </Paper>

      {/* City Selection */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Select City from List
        </Typography>

        {/* Karnataka Cities */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Karnataka Cities ({cities.karnataka.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={1}>
              {cities.karnataka.map((city) => (
                <Grid item xs={12} sm={6} md={4} key={city.name}>
                  <Button
                    fullWidth
                    variant={selectedCity === city.name ? 'contained' : 'outlined'}
                    onClick={() => handleCitySelect(city)}
                    size="small"
                  >
                    {city.display}
                  </Button>
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* South India Cities */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              South India Cities ({cities.south_india.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={1}>
              {cities.south_india.map((city) => (
                <Grid item xs={12} sm={6} md={4} key={city.name}>
                  <Button
                    fullWidth
                    variant={selectedCity === city.name ? 'contained' : 'outlined'}
                    onClick={() => handleCitySelect(city)}
                    size="small"
                  >
                    {city.display}
                  </Button>
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Major Cities */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Other Major Cities ({cities.major_cities.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={1}>
              {cities.major_cities.map((city) => (
                <Grid item xs={12} sm={6} md={4} key={city.name}>
                  <Button
                    fullWidth
                    variant={selectedCity === city.name ? 'contained' : 'outlined'}
                    onClick={() => handleCitySelect(city)}
                    size="small"
                  >
                    {city.display}
                  </Button>
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
      </Paper>

      {/* Manual Entry */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Manual Entry
          </Typography>
          <Button
            size="small"
            onClick={() => setManualMode(!manualMode)}
          >
            {manualMode ? 'Hide' : 'Show'} Manual Entry
          </Button>
        </Box>

        {manualMode && (
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="City Name"
                value={locationSettings.city_name}
                onChange={(e) => setLocationSettings({ ...locationSettings, city_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Latitude"
                value={locationSettings.latitude}
                onChange={(e) => setLocationSettings({ ...locationSettings, latitude: e.target.value })}
                helperText="Example: 12.9716"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Longitude"
                value={locationSettings.longitude}
                onChange={(e) => setLocationSettings({ ...locationSettings, longitude: e.target.value })}
                helperText="Example: 77.5946"
              />
            </Grid>
          </Grid>
        )}
      </Paper>

      {/* Save Button */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        <Button
          variant="contained"
          size="large"
          startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
          onClick={handleSave}
          disabled={saving || !locationSettings.latitude || !locationSettings.longitude}
          sx={{ px: 4 }}
        >
          {saving ? 'Saving...' : 'Save Location Settings'}
        </Button>
      </Box>

      {/* Info Box */}
      <Paper sx={{ p: 3, mt: 3, bgcolor: '#FFF3E0' }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Important Notes:
        </Typography>
        <Typography variant="body2" component="div">
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            <li>Accurate location ensures correct Tithi, Nakshatra, Rahu Kaal, and sunrise/sunset times</li>
            <li>Location is used for all Panchang calculations in your temple</li>
            <li>After saving, restart your backend server for changes to take effect</li>
            <li>You can use Google Maps to find exact coordinates if needed</li>
          </ul>
        </Typography>
      </Paper>
    </Box>
  );
}

export default PanchangSettings;
