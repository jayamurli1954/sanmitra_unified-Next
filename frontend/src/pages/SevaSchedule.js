import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
  Alert,
  CircularProgress,
  Chip,
  TextField,
  Button,
} from '@mui/material';
import Layout from '../components/Layout';
import api from '../services/api';
import ExportButton from '../components/ExportButton';
import PrintButton from '../components/PrintButton';
import { exportToCSV, exportToExcel, exportToPDF } from '../utils/export';

function SevaSchedule() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [days, setDays] = useState(3);
  const [scheduleData, setScheduleData] = useState(null);

  const fetchSchedule = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await api.get('/api/v1/reports/sevas/schedule', {
        params: { days }
      });
      
      setScheduleData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load schedule');
      console.error('Schedule error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Schedule reload is intentionally keyed to days; manual refresh uses the same fetch.
  useEffect(() => {
    fetchSchedule();
  }, [days]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExport = (format) => {
    if (!scheduleData) return;

    const exportData = scheduleData.schedule.map(s => ({
      'Date': new Date(s.date).toLocaleDateString(),
      'Time': s.time || 'N/A',
      'Seva Name': s.seva_name,
      'Devotee Name': s.devotee_name,
      'Mobile': s.devotee_mobile || 'N/A',
      'Amount (â‚¹)': s.amount,
      'Status': s.status,
      'Special Request': s.special_request || 'N/A',
    }));

    if (format === 'csv') {
      exportToCSV(exportData, `seva-schedule-${days}-days`);
    } else if (format === 'excel') {
      exportToExcel(exportData, `Seva Schedule - Next ${days} Days`);
    } else if (format === 'pdf') {
      exportToPDF(exportData, `Seva Schedule - Next ${days} Days`, {
        period: scheduleData
          ? {
              from: new Date(scheduleData.from_date).toLocaleDateString('en-GB'),
              to: new Date(scheduleData.to_date).toLocaleDateString('en-GB'),
            }
          : `Next ${days} Days`,
      });
    }
  };

  const getStatusColor = (status) => {
    if (status === 'Today') return 'primary';
    if (status === 'Completed') return 'success';
    if (status === 'Upcoming') return 'warning';
    return 'default';
  };

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3, fontWeight: 'bold' }}>
          Seva Schedule - Next {days} Days
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Days Selector */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <TextField
                label="Number of Days"
                type="number"
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value) || 3)}
                inputProps={{ min: 1, max: 30 }}
                size="small"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                variant="contained"
                onClick={fetchSchedule}
                disabled={loading}
                fullWidth
              >
                {loading ? <CircularProgress size={20} /> : 'Refresh Schedule'}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {/* Schedule Table */}
        {scheduleData && (
          <Paper id="seva-schedule-report-content" sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Period: {new Date(scheduleData.from_date).toLocaleDateString()} to {new Date(scheduleData.to_date).toLocaleDateString()} | 
                Total Bookings: {scheduleData.total_bookings}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <ExportButton onExport={handleExport} />
                <PrintButton
                  elementId="seva-schedule-report-content"
                  title="Seva Schedule Report"
                  reportContext={{
                    period: scheduleData
                      ? {
                          from: new Date(scheduleData.from_date).toLocaleDateString('en-GB'),
                          to: new Date(scheduleData.to_date).toLocaleDateString('en-GB'),
                        }
                      : `Next ${days} Days`,
                  }}
                />
              </Box>
            </Box>

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Date</strong></TableCell>
                    <TableCell><strong>Time</strong></TableCell>
                    <TableCell><strong>Seva Name</strong></TableCell>
                    <TableCell><strong>Devotee Name</strong></TableCell>
                    <TableCell><strong>Mobile</strong></TableCell>
                    <TableCell align="right"><strong>Amount (â‚¹)</strong></TableCell>
                    <TableCell><strong>Status</strong></TableCell>
                    <TableCell><strong>Special Request</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {scheduleData.schedule.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography color="text.secondary">No sevas scheduled for the next {days} days</Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    scheduleData.schedule.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{new Date(item.date).toLocaleDateString()}</TableCell>
                        <TableCell>{item.time || 'N/A'}</TableCell>
                        <TableCell>{item.seva_name}</TableCell>
                        <TableCell>{item.devotee_name}</TableCell>
                        <TableCell>{item.devotee_mobile || 'N/A'}</TableCell>
                        <TableCell align="right">
                          {new Intl.NumberFormat('en-IN', {
                            style: 'currency',
                            currency: 'INR',
                            maximumFractionDigits: 0,
                          }).format(item.amount)}
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={item.status} 
                            color={getStatusColor(item.status)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{item.special_request || 'N/A'}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}
      </Box>
    </Layout>
  );
}

export default SevaSchedule;



