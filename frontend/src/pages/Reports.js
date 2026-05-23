import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  MenuItem,
  CircularProgress,
  Alert,
} from '@mui/material';
import GetAppIcon from '@mui/icons-material/GetApp';
import DownloadIcon from '@mui/icons-material/Download';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { useCurrentUser } from '../contexts/CurrentUserContext';
import api from '../services/api';

function Reports() {
  const navigate = useNavigate();
  const { user, loading: currentUserLoading } = useCurrentUser();
  const [loading, setLoading] = useState(false);
  const [dateFrom, setDateFrom] = useState(new Date(new Date().setDate(1))); // First day of month
  const [dateTo, setDateTo] = useState(new Date());
  const [reportType, setReportType] = useState('daily');
  const [reportData, setReportData] = useState(null);
  const [error, setError] = useState('');

  const reportTypes = [
    { value: 'daily', label: 'Daily Collection' },
    { value: 'monthly', label: 'Monthly Summary' },
    { value: 'category', label: 'Category-wise' },
    { value: 'devotee', label: 'Devotee-wise' },
  ];
  const canApproveReschedule = !currentUserLoading && (
    Boolean(user?.action_permissions?.approve_seva_reschedule)
    || ['admin', 'temple_manager', 'super_admin'].includes(user?.role)
    || Boolean(user?.is_superuser)
  );

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError('');
      
      let response;
      if (reportType === 'daily') {
        response = await api.get(`/api/v1/donations/report/daily?date=${dateTo.toISOString().split('T')[0]}`);
        setReportData(response.data);
      } else if (reportType === 'monthly') {
        response = await api.get(`/api/v1/donations/report/monthly?month=${dateFrom.getMonth() + 1}&year=${dateFrom.getFullYear()}`);
        setReportData(response.data);
      } else {
        // For period/category reports, get donations and calculate
        response = await api.get(`/api/v1/donations?date_from=${dateFrom.toISOString().split('T')[0]}&date_to=${dateTo.toISOString().split('T')[0]}&limit=1000`);
        const donations = response.data || [];
        const total = donations.reduce((sum, d) => sum + (d.amount || 0), 0);
        
        // Group by category
        const byCategory = {};
        donations.forEach(d => {
          const catName = d.category?.name || 'Unknown';
          if (!byCategory[catName]) {
            byCategory[catName] = { amount: 0, count: 0 };
          }
          byCategory[catName].amount += (d.amount || 0);
          byCategory[catName].count += 1;
        });
        
        setReportData({
          total,
          count: donations.length,
          by_category: Object.entries(byCategory).map(([category, data]) => ({
            category,
            amount: data.amount,
            count: data.count
          }))
        });
      }
    } catch (err) {
      console.error('Error fetching report:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Unknown error';
      setError(`Failed to load report data: ${errorMsg}`);
      // Don't use mock data - show empty state instead
      setReportData({
        total: 0,
        count: 0,
        by_category: [],
        donations: []
      });
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh when report type changes; date-range refresh remains user-driven.
  useEffect(() => {
    fetchReport();
  }, [reportType]); // eslint-disable-line react-hooks/exhaustive-deps

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleDownloadExcel = async () => {
    try {
      setError('');
      setLoading(true);
      const response = await api.get('/api/v1/donations/export/excel', {
        params: {
          date_from: dateFrom.toISOString().split('T')[0],
          date_to: dateTo.toISOString().split('T')[0],
        },
        responseType: 'blob',
      });
      
      // Handle Excel response
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `donations_${dateFrom.toISOString().split('T')[0]}_to_${dateTo.toISOString().split('T')[0]}.xlsx`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading Excel:', err);
      const errorMsg = err.response?.data 
        ? (typeof err.response.data === 'string' ? err.response.data : err.response.data.detail || 'Unknown error')
        : err.message || 'Failed to download Excel file. Please ensure the backend is running and try again.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      setError('');
      setLoading(true);
      const response = await api.get('/api/v1/donations/export/pdf', {
        params: {
          date_from: dateFrom.toISOString().split('T')[0],
          date_to: dateTo.toISOString().split('T')[0],
        },
        responseType: 'blob',
      });
      
      // Handle PDF response
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `donations_${dateFrom.toISOString().split('T')[0]}_to_${dateTo.toISOString().split('T')[0]}.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading PDF:', err);
      const errorMsg = err.response?.data 
        ? (typeof err.response.data === 'string' ? err.response.data : err.response.data.detail || 'Unknown error')
        : err.message || 'Failed to download PDF file. Please ensure the backend is running and try again.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Reports
      </Typography>

      {/* Quick Links to New Reports */}
      <Paper sx={{ p: 3, mt: 2, mb: 3, background: 'linear-gradient(135deg, #FF9933 0%, #FF6B35 100%)' }}>
        <Typography variant="h6" sx={{ color: '#fff', mb: 2, fontWeight: 'bold' }}>
          Available Reports
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Button
              fullWidth
              variant="contained"
              sx={{ backgroundColor: '#fff', color: '#FF9933', '&:hover': { backgroundColor: '#f5f5f5' } }}
              onClick={() => navigate('/reports/donations/category-wise')}
            >
              Category-Wise Donation
            </Button>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Button
              fullWidth
              variant="contained"
              sx={{ backgroundColor: '#fff', color: '#FF9933', '&:hover': { backgroundColor: '#f5f5f5' } }}
              onClick={() => navigate('/reports/donations/detailed')}
            >
              Detailed Donation Report
            </Button>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Button
              fullWidth
              variant="contained"
              sx={{ backgroundColor: '#fff', color: '#FF9933', '&:hover': { backgroundColor: '#f5f5f5' } }}
              onClick={() => navigate('/reports/sevas/detailed')}
            >
              Detailed Seva Report
            </Button>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Button
              fullWidth
              variant="contained"
              sx={{ backgroundColor: '#fff', color: '#FF9933', '&:hover': { backgroundColor: '#f5f5f5' } }}
              onClick={() => navigate('/reports/sevas/schedule')}
            >
              3-Day Seva Schedule
            </Button>
          </Grid>
          {canApproveReschedule && (
            <Grid item xs={12} sm={6} md={3}>
              <Button
                fullWidth
                variant="contained"
                sx={{ backgroundColor: '#fff', color: '#FF9933', '&:hover': { backgroundColor: '#f5f5f5' } }}
                onClick={() => navigate('/sevas/reschedule-approval')}
              >
                Reschedule Approvals
              </Button>
            </Grid>
          )}
        </Grid>
      </Paper>

      <Paper sx={{ p: 3, mt: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth
              select
              label="Report Type"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              {reportTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth
              type="date"
              label="From Date"
              value={dateFrom.toISOString().split('T')[0]}
              onChange={(e) => setDateFrom(new Date(e.target.value))}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth
              type="date"
              label="To Date"
              value={dateTo.toISOString().split('T')[0]}
              onChange={(e) => setDateTo(new Date(e.target.value))}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button
              fullWidth
              variant="contained"
              onClick={fetchReport}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <GetAppIcon />}
            >
              Generate Report
            </Button>
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button
              fullWidth
              variant="outlined"
              onClick={handleDownloadExcel}
              disabled={!reportData || loading}
              startIcon={<DownloadIcon />}
            >
              Excel
            </Button>
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button
              fullWidth
              variant="outlined"
              onClick={handleDownloadPDF}
              disabled={!reportData || loading}
              startIcon={<PictureAsPdfIcon />}
            >
              PDF
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : reportData ? (
        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Total Collection
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                  {formatCurrency(reportData.total || 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {reportData.count || 0} donations
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Category-wise Breakdown
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Category</TableCell>
                      <TableCell align="right">Count</TableCell>
                      <TableCell align="right">Amount</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {reportData.by_category?.map((item, index) => (
                      <TableRow key={index}>
                        <TableCell>{item.category}</TableCell>
                        <TableCell align="right">{item.count}</TableCell>
                        <TableCell align="right">{formatCurrency(item.amount)}</TableCell>
                      </TableRow>
                    ))}
                    {(!reportData.by_category || reportData.by_category.length === 0) && (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          No data available
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      ) : (
        <Paper sx={{ p: 3, mt: 2, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            Select report type and date range, then click "Generate Report"
          </Typography>
        </Paper>
      )}
    </Layout>
  );
}

export default Reports;
