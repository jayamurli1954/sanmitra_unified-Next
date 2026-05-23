import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
  Alert,
  CircularProgress,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../services/api';
import ExportButton from '../components/ExportButton';
import PrintButton from '../components/PrintButton';
import { exportToCSV, exportToExcel, exportToPDF } from '../utils/export';

const getCategoryRows = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.categories)) return data.categories;
  if (Array.isArray(data?.by_category)) return data.by_category;
  if (Array.isArray(data?.items)) return data.items;
  return [];
};

function CategoryWiseDonationReport() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fromDate, setFromDate] = useState(new Date());
  const [toDate, setToDate] = useState(new Date());
  const [reportData, setReportData] = useState(null);
  const categoryRows = getCategoryRows(reportData);
  const totalCount = reportData?.total_count ?? reportData?.count ?? categoryRows.reduce((sum, item) => sum + (Number(item?.count) || 0), 0);
  const totalAmount = reportData?.total_amount ?? reportData?.total ?? categoryRows.reduce((sum, item) => sum + (Number(item?.amount) || 0), 0);

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await api.get('/api/v1/reports/donations/category-wise', {
        params: {
          from_date: fromDate.toISOString().split('T')[0],
          to_date: toDate.toISOString().split('T')[0],
        }
      });
      
      setReportData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load report');
      console.error('Report error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial report load should happen once on mount; later refreshes are user-driven.
  useEffect(() => {
    fetchReport();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExport = (format) => {
    if (!reportData) return;

    const exportData = categoryRows.map(cat => ({
      'Category': cat.category,
      'Count': cat.count,
      'Amount (INR)': cat.amount,
    }));

    if (format === 'csv') {
      exportToCSV(exportData, `category-wise-donation-${fromDate.toISOString().split('T')[0]}`);
    } else if (format === 'excel') {
      exportToExcel(exportData, `Category-Wise Donation Report`);
    } else if (format === 'pdf') {
      exportToPDF(exportData, 'Category-Wise Donation Report', {
        period: {
          from: fromDate.toLocaleDateString('en-GB'),
          to: toDate.toLocaleDateString('en-GB'),
        },
      });
    }
  };

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
            Category-Wise Donation Report
          </Typography>
          <Button variant="outlined" onClick={() => navigate('/reports')}>
            Back to Reports
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Date Range Selection */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="From Date"
                  value={fromDate}
                  onChange={(newValue) => setFromDate(newValue)}
                  renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12} sm={4}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="To Date"
                  value={toDate}
                  onChange={(newValue) => setToDate(newValue)}
                  renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                variant="contained"
                fullWidth
                onClick={fetchReport}
                disabled={loading}
                sx={{ height: '40px' }}
              >
                {loading ? <CircularProgress size={20} /> : 'Generate Report'}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {/* Report Table */}
        {reportData && (
          <Paper id="category-wise-donation-report-content" sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Report Period: {new Date(reportData.from_date).toLocaleDateString()} to {new Date(reportData.to_date).toLocaleDateString()}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <ExportButton onExport={handleExport} />
                <PrintButton
                  elementId="category-wise-donation-report-content"
                  title="Category-Wise Donation Report"
                  reportContext={{
                    period: {
                      from: fromDate.toLocaleDateString('en-GB'),
                      to: toDate.toLocaleDateString('en-GB'),
                    },
                  }}
                />
              </Box>
            </Box>

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Category</strong></TableCell>
                    <TableCell align="right"><strong>Count</strong></TableCell>
                    <TableCell align="right"><strong>Amount (INR)</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {categoryRows.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>{item.category}</TableCell>
                      <TableCell align="right">{item.count}</TableCell>
                      <TableCell align="right">
                        {new Intl.NumberFormat('en-IN', {
                          style: 'currency',
                          currency: 'INR',
                          maximumFractionDigits: 0,
                        }).format(item.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow sx={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                    <TableCell><strong>TOTAL</strong></TableCell>
                    <TableCell align="right"><strong>{totalCount}</strong></TableCell>
                    <TableCell align="right">
                      <strong>
                        {new Intl.NumberFormat('en-IN', {
                          style: 'currency',
                          currency: 'INR',
                          maximumFractionDigits: 0,
                        }).format(totalAmount)}
                      </strong>
                    </TableCell>
                  </TableRow>
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

export default CategoryWiseDonationReport;

