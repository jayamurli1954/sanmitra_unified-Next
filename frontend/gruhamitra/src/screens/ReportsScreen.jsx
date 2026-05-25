import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { authService } from '../services/authService';
import resourceService from '../services/resourceService';

// Helper function to safely extract error message from API errors
const getErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (Array.isArray(detail)) {
      // Pydantic validation errors - extract messages
      return detail.map(err => {
        if (typeof err === 'string') return err;
        if (typeof err === 'object' && err.msg) return err.msg;
        if (typeof err === 'object' && err.message) return err.message;
        return JSON.stringify(err);
      }).join(', ');
    } else if (typeof detail === 'string') {
      return detail;
    } else if (typeof detail === 'object') {
      return detail.msg || detail.message || 'Validation error occurred';
    }
  }
  if (error.message) {
    return error.message;
  }
  return 'An error occurred. Please try again.';
};

const ReportsScreen = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportData, setReportData] = useState(null);
  const reportResultRef = useRef(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [dateRange, setDateRange] = useState({
    from_date: new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0], // Jan 1 of current year
    to_date: new Date().toISOString().split('T')[0], // Today
    as_on_date: new Date().toISOString().split('T')[0] // For trial balance
  });
  const [uploadingResource, setUploadingResource] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadDescription, setUploadDescription] = useState('');
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadCategory, setUploadCategory] = useState(null);

  // Check authentication and backend connectivity on mount
  useEffect(() => {
    const checkAuthAndConnectivity = async () => {
      try {
        const isAuthenticated = await authService.isAuthenticated();
        if (!isAuthenticated) {
          navigate('/login');
          return;
        }
        const user = await authService.getCurrentUser();
        if (!user) {
          navigate('/login');
          return;
        }
        setCurrentUser(user);
        console.log('ReportsScreen: User authenticated:', user.email, 'Role:', user.role);
      } catch (error) {
        console.error('ReportsScreen: Auth check failed:', error);
        navigate('/login');
      }
    };
    checkAuthAndConnectivity();
  }, [navigate]);

  const reports = [
    {
      id: 'society_summary',
      title: 'Society Summary',
      description: 'High-level financial overview for all members',
      icon: '',
      color: '#FFCC00',
      needsDate: 'date_range',
      endpoint: '/reports/society-summary'
    },
    {
      id: 'trial_balance',
      title: 'Trial Balance',
      description: 'Account balances as on a specific date',
      icon: '',
      color: '#007AFF',
      needsDate: 'as_on_date',
      endpoint: '/reports/trial-balance'
    },
    {
      id: 'general_ledger',
      title: 'General Ledger',
      description: 'Consolidated transaction ledger by account',
      icon: '',
      color: '#34C759',
      needsDate: 'date_range',
      endpoint: '/reports/general-ledger'
    },
    {
      id: 'receipts_payments',
      title: 'Receipts & Payments',
      description: 'Cash-based report showing all receipts and payments',
      icon: '',
      color: '#FF9500',
      needsDate: 'date_range',
      endpoint: '/reports/receipts-and-payments'
    },
    {
      id: 'income_expenditure',
      title: 'Income & Expenditure',
      description: 'Accrual-based profit & loss statement',
      icon: '',
      color: '#5856D6',
      needsDate: 'date_range',
      endpoint: '/reports/income-and-expenditure'
    },
    {
      id: 'balance_sheet',
      title: 'Balance Sheet',
      description: 'Assets, Liabilities and Capital position',
      icon: '',
      color: '#AF52DE',
      needsDate: 'as_on_date',
      endpoint: '/reports/balance-sheet'
    },
    {
      id: 'member_dues',
      title: 'Member Dues Report',
      description: 'Outstanding dues from all members',
      icon: '',
      color: '#FF3B30',
      needsDate: 'date_range',
      endpoint: '/reports/member-dues'
    },
    {
      id: 'asset_register',
      title: 'Asset Register',
      description: 'Formal record of all society assets and their book value',
      icon: '',
      color: '#AF52DE',
      needsDate: 'none',
      endpoint: '/reports/asset-register'
    },
    {
      id: 'my_ledger',
      title: 'My Ledger',
      description: 'Your personal transaction history',
      icon: '',
      color: '#007AFF',
      needsDate: 'date_range',
      endpoint: '/reports/member-ledger'
    },
    {
      id: 'my_bills',
      title: 'My Bills',
      description: 'Your maintenance bills and payment history',
      icon: '',
      color: '#34C759',
      needsDate: 'date_range',
      endpoint: '/maintenance/my-bills' // Assuming this exists or will be implemented
    },
    {
      id: 'agm_docs',
      title: 'AGM Documents',
      description: 'Annual General Meeting notices and minutes',
      icon: '',
      color: '#5856D6',
      needsDate: 'none',
      endpoint: '/reports/agm-documents'
    },
    {
      id: 'audit_report',
      title: 'Audit Report',
      description: 'Final signed audit reports for the society',
      icon: '',
      color: '#AF52DE',
      needsDate: 'none',
      endpoint: '/reports/audit-reports'
    }
  ];

  const filteredReports = reports.filter(report => {
    if (!currentUser) return false;

    const committeeRoles = ['super_admin', 'admin', 'accountant', 'chairman', 'secretary', 'treasurer'];
    const auditorRoles = ['auditor'];
    const isCommitteeOrAuditor = [...committeeRoles, ...auditorRoles].includes(currentUser.role);

    // Members only see their own summary and specific reports
    if (currentUser.role === 'resident') {
      return ['society_summary', 'my_ledger', 'my_bills', 'agm_docs', 'audit_report'].includes(report.id);
    }

    // For everyone else (Committee/Auditor), show all
    return true;
  });

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return ' 0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleViewVoucher = (entry) => {
    // Placeholder for View Voucher logic
    console.log('Viewing voucher for entry:', entry);
    if (entry.journal_entry_id) {
      window.open(`${api.defaults.baseURL}/transactions/vouchers/${entry.journal_entry_id}/pdf`, '_blank');
    } else {
      alert('Voucher PDF not available for this entry (legacy data).');
    }
  };

  const handleEditEntry = (entry) => {
    // Placeholder for Edit Entry logic
    console.log('Editing entry:', entry);
    alert('Edit Voucher feature coming soon as part of the new voucher system.');
  };

  const handleReverseEntry = async (entry) => {
    if (!window.confirm('Are you sure you want to reverse this transaction? This will create a reversing entry.')) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.post(`/transactions/${entry.id}/reverse`);
      setMessage({ type: 'success', text: 'Transaction reversed successfully. New reversal voucher created.' });
      // Refresh report
      if (selectedReport) handleGenerateReport(selectedReport);
    } catch (error) {
      console.error('Error reversing transaction:', error);
      setMessage({ type: 'error', text: getErrorMessage(error) || 'Failed to reverse transaction.' });
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!selectedReport) {
      setMessage({ type: 'error', text: 'Please generate a report first' });
      return;
    }

    try {
      setLoading(true);
      let url = '';
      let exportParams = {};

      // Ensure dates are in YYYY-MM-DD format
      const formatDate = (dateStr) => {
        if (!dateStr) return null;
        // Remove time if present
        return dateStr.split('T')[0];
      };

      const asOnDate = formatDate(dateRange.as_on_date || dateRange.to_date || dateRange.from_date);
      const fromDate = formatDate(dateRange.from_date);
      const toDate = formatDate(dateRange.to_date);

      // Map report IDs to PDF export endpoints
      if (selectedReport.id === 'trial_balance') {
        if (!asOnDate) {
          setMessage({ type: 'error', text: 'Please select an "As On Date" for Trial Balance' });
          setLoading(false);
          return;
        }
        url = '/reports/trial-balance/export/pdf';
        exportParams = { as_on_date: asOnDate };
      } else if (selectedReport.id === 'general_ledger') {
        if (!fromDate || !toDate) {
          setMessage({ type: 'error', text: 'Please select both "From Date" and "To Date" for General Ledger' });
          setLoading(false);
          return;
        }
        url = '/reports/general-ledger/export/pdf';
        exportParams = { 
          from_date: fromDate, 
          to_date: toDate 
        };
      } else if (selectedReport.id === 'income_expenditure') {
        if (!fromDate || !toDate) {
          setMessage({ type: 'error', text: 'Please select both "From Date" and "To Date" for Income & Expenditure' });
          setLoading(false);
          return;
        }
        url = '/reports/income-and-expenditure/export/pdf';
        exportParams = { 
          from_date: fromDate, 
          to_date: toDate 
        };
      } else if (selectedReport.id === 'balance_sheet') {
        if (!asOnDate) {
          setMessage({ type: 'error', text: 'Please select an "As On Date" for Balance Sheet' });
          setLoading(false);
          return;
        }
        url = '/reports/balance-sheet/export/pdf';
        exportParams = { as_on_date: asOnDate };
      } else if (selectedReport.id === 'receipts_payments') {
        if (!fromDate || !toDate) {
          setMessage({ type: 'error', text: 'Please select both "From Date" and "To Date" for Receipts & Payments' });
          setLoading(false);
          return;
        }
        url = '/reports/receipts-and-payments/export/pdf';
        exportParams = { 
          from_date: fromDate, 
          to_date: toDate 
        };
      } else {
        setMessage({ type: 'error', text: 'PDF export is not available for this report type' });
        setLoading(false);
        return;
      }

      console.log('Exporting PDF:', url, exportParams);
      const response = await api.get(url, { 
        params: exportParams, 
        responseType: 'blob' 
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      const reportName = selectedReport.id.replace(/_/g, '-');
      link.setAttribute('download', `${reportName}_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
      setMessage({ type: 'success', text: 'PDF exported successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (err) {
      console.error('PDF export error:', err);
      setMessage({ type: 'error', text: getErrorMessage(err) || 'Failed to export PDF. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async (report) => {
    setLoading(true);
    setMessage({ type: '', text: '' });
    setSelectedReport(report);
    setReportData(null);

    try {
      let response;

      // Check authentication before making API call
      const isAuthenticated = await authService.isAuthenticated();
      if (!isAuthenticated) {
        setMessage({ type: 'error', text: 'Session expired. Please login again.' });
        setTimeout(() => navigate('/login'), 2000);
        setLoading(false);
        return;
      }

      // Get endpoint
      const baseURL = api.defaults.baseURL || 'http://localhost:8002/api';
      const endpoint = typeof report.endpoint === 'function' ? report.endpoint(currentUser) : report.endpoint;

      console.log('ReportsScreen: Base URL:', baseURL);
      console.log('ReportsScreen: Endpoint:', endpoint);

      if (report.needsDate === 'as_on_date') {
        if (!dateRange.as_on_date) {
          setMessage({ type: 'error', text: 'Please select an "As On Date" for this report' });
          setLoading(false);
          return;
        }
        // Ensure date is in YYYY-MM-DD format
        const asOnDate = dateRange.as_on_date.split('T')[0]; // Remove time if present
        const requestParams = {
          as_on_date: asOnDate
        };
        if (report.id === 'my_ledger' && currentUser?.flat_id) {
          requestParams.flat_id = currentUser.flat_id;
        }
        console.log('Generating report:', endpoint, 'with params:', requestParams);
        console.log('As On Date value:', asOnDate);
        response = await api.get(endpoint, { params: requestParams });
      } else if (report.needsDate === 'none') {
        console.log('Generating report:', endpoint);
        response = await api.get(endpoint);
      } else {
        if (!dateRange.from_date || !dateRange.to_date) {
          setMessage({ type: 'error', text: 'Please select both "From Date" and "To Date" for this report' });
          setLoading(false);
          return;
        }
        const requestParams = {
          from_date: dateRange.from_date,
          to_date: dateRange.to_date
        };
        if (report.id === 'my_ledger' && currentUser?.flat_id) {
          requestParams.flat_id = currentUser.flat_id;
        }
        console.log('Generating report:', endpoint, 'with params:', requestParams);
        response = await api.get(endpoint, { params: requestParams });
      }

      console.log('Report response:', response.data);
      setReportData(response.data);
      setMessage({ type: 'success', text: `${report.title} generated successfully!` });

      // Scroll to result after a short delay to allow DOM update
      setTimeout(() => {
        reportResultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (error) {
      console.error('Error generating report:', error);
      console.error('Error details:', {
        code: error.code,
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        config: error.config
      });
      let errorMessage = 'Failed to generate report';

      if (error.code === 'CONNECTION_ERROR' || !error.response) {
        errorMessage = `Cannot connect to server. (Error: ${error.code || 'Unknown'}, Message: ${error.message || 'No message'})\n\nPlease check:\n1. Backend is running at http://localhost:8002\n2. CORS is enabled in backend\n3. No firewall blocking the connection\n\nPotential causes:\n1. Backend is not running\n2. Network timeout\n3. CORS/Firewall block`;
      } else if (error.response?.status === 401) {
        errorMessage = 'Session expired. Please login again.';
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to view reports.';
      } else if (error.response?.status === 404) {
        errorMessage = 'Report endpoint not found. Please check the API path.';
      } else if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // Format FastAPI validation errors more clearly
          errorMessage = detail.map(err => {
            const field = err.loc ? err.loc.join('.') : 'unknown';
            const msg = err.msg || JSON.stringify(err);
            return `${field}: ${msg}`;
          }).join('\n');
        } else {
          errorMessage = JSON.stringify(detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      setMessage({
        type: 'error',
        text: errorMessage
      });
    } finally {
      setLoading(false);
    }
  };

  const renderTrialBalance = (data) => {
    if (!data) return null;
    const items = data.items || [];

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>Trial Balance as on {data.as_on_date || dateRange.as_on_date}</h3>
        {items.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', backgroundColor: '#f9f9f9', borderRadius: '8px', border: '1px dashed #ccc' }}>
            No account balances found for the selected date.
          </div>
        ) : (
          <div className="settings-table-container">
            <table className="settings-table">
              <thead>
                <tr>
                  <th>Account Code</th>
                  <th>Account Name</th>
                  <th style={{ textAlign: 'right' }}>Debit ()</th>
                  <th style={{ textAlign: 'right' }}>Credit ()</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((account, idx) => (
                  <tr key={idx}>
                    <td>{account.account_code}</td>
                    <td>{account.account_name}</td>
                    <td style={{ textAlign: 'right' }}>{formatCurrency(account.debit_balance)}</td>
                    <td style={{ textAlign: 'right' }}>{formatCurrency(account.credit_balance)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                  <td colSpan="2">Total</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_debit)}</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_credit)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    );
  };

  const renderGeneralLedger = (data) => {
    if (!data) return null;
    const entries = data.ledger_entries || [];

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>
          General Ledger from {dateRange.from_date} to {dateRange.to_date}
        </h3>
        {entries.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', backgroundColor: '#f9f9f9', borderRadius: '8px', border: '1px dashed #ccc' }}>
            No ledger entries found for the selected period.
          </div>
        ) : (
          entries.map((account, idx) => (
            <div key={idx} style={{ marginBottom: '30px', border: '1px solid #ddd', borderRadius: '8px', padding: '15px' }}>
              <h4 style={{ marginTop: 0, color: '#007AFF' }}>
                {account.account_code} - {account.account_name}
              </h4>
              <div style={{ marginBottom: '10px', fontSize: '14px', color: '#666' }}>
                Opening Balance: {formatCurrency(account.opening_balance)} |
                Closing Balance: {formatCurrency(account.closing_balance)}
              </div>
              {account.transactions && account.transactions.length > 0 ? (
                <div className="settings-table-container">
                  <table className="settings-table" style={{ fontSize: '13px' }}>
                    <thead>
                      <tr>
                        <th style={{ width: '10%' }}>Date</th>
                        <th style={{ width: '40%' }}>Description</th>
                        <th style={{ width: '15%' }}>Reference</th>
                        <th style={{ textAlign: 'right', width: '10%' }}>Debit ()</th>
                        <th style={{ textAlign: 'right', width: '10%' }}>Credit ()</th>
                        <th style={{ textAlign: 'right', width: '15%' }}>Balance ()</th>
                        <th style={{ textAlign: 'center', width: '10%' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {account.transactions.map((entry, eIdx) => (
                        <tr key={eIdx}>
                          <td>{new Date(entry.date).toLocaleDateString('en-GB')}</td>
                          <td>{entry.description || '-'}</td>
                          <td>{entry.reference || '-'}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(entry.debit)}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(entry.credit)}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(entry.balance)}</td>
                          <td style={{ textAlign: 'center' }}>
                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                              <button
                                title="View Voucher"
                                onClick={() => handleViewVoucher(entry)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}
                              >
                                
                              </button>
                              <button
                                title="Edit Entry"
                                onClick={() => handleEditEntry(entry)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}
                              >
                                
                              </button>
                              <button
                                title="Reverse Entry"
                                onClick={() => handleReverseEntry(entry)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}
                              >
                                
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ color: '#666', fontStyle: 'italic' }}>No transactions in this period</p>
              )}
            </div>
          ))
        )}
      </div>
    );
  };

  const renderReceiptsPayments = (data) => {
    if (!data) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>
          Receipts & Payments from {dateRange.from_date} to {dateRange.to_date}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '15px', marginBottom: '20px' }}>
          <div style={{ padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px', border: '1px solid #ddd' }}>
            <h4 style={{ marginTop: 0, color: '#666', fontSize: '14px' }}>Opening Balance</h4>
            <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
              {formatCurrency(data.opening_balance)}
            </div>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#e8f5e9', borderRadius: '8px', border: '1px solid #c8e6c9' }}>
            <h4 style={{ marginTop: 0, color: '#2e7d32', fontSize: '14px' }}>Total Receipts</h4>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2e7d32' }}>
              {formatCurrency(data.total_receipts)}
            </div>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#ffebee', borderRadius: '8px', border: '1px solid #ffcdd2' }}>
            <h4 style={{ marginTop: 0, color: '#c62828', fontSize: '14px' }}>Total Payments</h4>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#c62828' }}>
              {formatCurrency(data.total_payments)}
            </div>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#e3f2fd', borderRadius: '8px', border: '1px solid #bbdefb' }}>
            <h4 style={{ marginTop: 0, color: '#1565c0', fontSize: '14px' }}>Closing Balance</h4>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#1565c0' }}>
              {formatCurrency(data.closing_balance)}
            </div>
          </div>
        </div>
        {data.receipts && data.receipts.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <h4>Receipts Details</h4>
            <div className="settings-table-container">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th style={{ textAlign: 'right' }}>Amount ()</th>
                  </tr>
                </thead>
                <tbody>
                  {data.receipts.map((item, idx) => (
                    <tr key={idx}>
                      <td>{new Date(item.date).toLocaleDateString()}</td>
                      <td>{item.description}</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {data.payments && data.payments.length > 0 && (
          <div>
            <h4>Payments Details</h4>
            <div className="settings-table-container">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th style={{ textAlign: 'right' }}>Amount ()</th>
                  </tr>
                </thead>
                <tbody>
                  {data.payments.map((item, idx) => (
                    <tr key={idx}>
                      <td>{new Date(item.date).toLocaleDateString()}</td>
                      <td>{item.description}</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderIncomeExpenditure = (data) => {
    if (!data) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>
          Income & Expenditure from {dateRange.from_date} to {dateRange.to_date}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          <div style={{ padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '8px' }}>
            <h4 style={{ marginTop: 0, color: '#007AFF' }}>Total Income</h4>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#007AFF' }}>
              {formatCurrency(data.total_income)}
            </div>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#fff0f0', borderRadius: '8px' }}>
            <h4 style={{ marginTop: 0, color: '#FF3B30' }}>Total Expenditure</h4>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#FF3B30' }}>
              {formatCurrency(data.total_expenditure)}
            </div>
          </div>
        </div>
        <div style={{ padding: '15px', backgroundColor: data.net_income >= 0 ? '#f0fff0' : '#fff0f0', borderRadius: '8px', marginBottom: '20px' }}>
          <h4 style={{ marginTop: 0 }}>Net Income / (Loss)</h4>
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: data.net_income >= 0 ? '#34C759' : '#FF3B30' }}>
            {formatCurrency(data.net_income)}
          </div>
        </div>
        {data.income_items && data.income_items.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <h4>Income Details</h4>
            <div className="settings-table-container">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Description</th>
                    <th style={{ textAlign: 'right' }}>Amount ()</th>
                  </tr>
                </thead>
                <tbody>
                  {data.income_items.map((item, idx) => (
                    <tr key={idx}>
                      <td>{item.account_code}</td>
                      <td>{item.account_name}</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f8ff', borderTop: '2px solid #007AFF' }}>
                    <td colSpan="2">Total Income</td>
                    <td style={{ textAlign: 'right', color: '#007AFF' }}>{formatCurrency(data.total_income)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
        {data.expenditure_items && data.expenditure_items.length > 0 && (
          <div>
            <h4>Expenditure Details</h4>
            <div className="settings-table-container">
              <table className="settings-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Description</th>
                    <th style={{ textAlign: 'right' }}>Amount ()</th>
                  </tr>
                </thead>
                <tbody>
                  {data.expenditure_items.map((item, idx) => (
                    <tr key={idx}>
                      <td>{item.account_code}</td>
                      <td>{item.account_name}</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 'bold', backgroundColor: '#fff0f0', borderTop: '2px solid #FF3B30' }}>
                    <td colSpan="2">Total Expenditure</td>
                    <td style={{ textAlign: 'right', color: '#FF3B30' }}>{formatCurrency(data.total_expenditure)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderBalanceSheet = (data) => {
    if (!data) return null;

    const asOnDate = data.as_on_date || dateRange.as_on_date || dateRange.to_date;
    const isBalanced = data.is_balanced !== false;

    // Standard Balance Sheet Format for Housing Society
    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px', textAlign: 'center' }}>
          Balance Sheet as on {asOnDate}
        </h3>
        
        {/* Balance Check Message */}
        {isBalanced ? (
          <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#d4edda', borderRadius: '8px', color: '#155724', textAlign: 'center' }}>
             Balance Sheet is balanced: Assets = Liabilities
          </div>
        ) : (
          <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f8d7da', borderRadius: '8px', color: '#721c24', textAlign: 'center' }}>
             Balance Sheet mismatch detected. Assets: {formatCurrency(data.total_assets || 0)}  Liabilities: {formatCurrency(data.total_liabilities || 0)}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginTop: '20px' }}>
          {/* LIABILITIES SIDE */}
          <div>
            <h4 style={{ color: '#FF3B30', marginBottom: '15px', borderBottom: '3px solid #FF3B30', paddingBottom: '8px', fontSize: '18px', fontWeight: 'bold' }}>
               LIABILITIES
            </h4>
            
            {/* A. Capital & Funds */}
            <div style={{ marginBottom: '20px' }}>
              <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>A. Capital & Funds</h5>
              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Particulars</th>
                      <th style={{ textAlign: 'right' }}>Amount ()</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.capital_funds && data.capital_funds.length > 0 ? (
                      data.capital_funds.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.name}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No capital & funds recorded</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                      <td>Total Funds</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_capital_funds || 0)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* B. Current Liabilities & Provisions */}
            <div style={{ marginBottom: '20px' }}>
              <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>B. Current Liabilities & Provisions</h5>
              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Particulars</th>
                      <th style={{ textAlign: 'right' }}>Amount ()</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.current_liabilities && data.current_liabilities.length > 0 ? (
                      data.current_liabilities.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.name}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No current liabilities recorded</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                      <td>Total Current Liabilities</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_current_liabilities || 0)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* TOTAL LIABILITIES */}
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff9e6', borderRadius: '8px', border: '2px solid #FF3B30' }}>
              <h4 style={{ margin: 0, textAlign: 'center', fontWeight: 'bold', fontSize: '16px' }}>
                TOTAL LIABILITIES
              </h4>
              <div style={{ textAlign: 'center', fontSize: '18px', fontWeight: 'bold', marginTop: '10px' }}>
                {formatCurrency(data.total_liabilities || 0)}
              </div>
            </div>
          </div>

          {/* ASSETS SIDE */}
          <div>
            <h4 style={{ color: '#007AFF', marginBottom: '15px', borderBottom: '3px solid #007AFF', paddingBottom: '8px', fontSize: '18px', fontWeight: 'bold' }}>
               ASSETS
            </h4>
            
            {/* A. Fixed Assets */}
            <div style={{ marginBottom: '20px' }}>
              <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>A. Fixed Assets</h5>
              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Particulars</th>
                      <th style={{ textAlign: 'right' }}>Amount ()</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.fixed_assets && data.fixed_assets.length > 0 ? (
                      data.fixed_assets.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.name}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No fixed assets recorded</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                      <td>Net Fixed Assets</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_fixed_assets || 0)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* B. Investments */}
            <div style={{ marginBottom: '20px' }}>
              <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>B. Investments</h5>
              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Particulars</th>
                      <th style={{ textAlign: 'right' }}>Amount ()</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.investments && data.investments.length > 0 ? (
                      data.investments.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.name}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No investments recorded</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                      <td>Total Investments</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_investments || 0)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* C. Current Assets */}
            <div style={{ marginBottom: '20px' }}>
              <h5 style={{ marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>C. Current Assets</h5>
              <div className="settings-table-container">
                <table className="settings-table">
                  <thead>
                    <tr>
                      <th>Particulars</th>
                      <th style={{ textAlign: 'right' }}>Amount ()</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.current_assets && data.current_assets.length > 0 ? (
                      data.current_assets.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.name}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999', fontStyle: 'italic' }}>No current assets recorded</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0' }}>
                      <td>Total Current Assets</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(data.total_current_assets || 0)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* TOTAL ASSETS */}
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e6f3ff', borderRadius: '8px', border: '2px solid #007AFF' }}>
              <h4 style={{ margin: 0, textAlign: 'center', fontWeight: 'bold', fontSize: '16px' }}>
                TOTAL ASSETS
              </h4>
              <div style={{ textAlign: 'center', fontSize: '18px', fontWeight: 'bold', marginTop: '10px' }}>
                {formatCurrency(data.total_assets || 0)}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderMemberDues = (data) => {
    if (!data || !data.members) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>
          Member Dues Report as on {dateRange.to_date}
        </h3>
        <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#fff0f0', borderRadius: '8px' }}>
          <strong>Total Outstanding: {formatCurrency(data.total_outstanding)}</strong>
        </div>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Flat Number</th>
                <th>Member Name</th>
                <th style={{ textAlign: 'right' }}>Outstanding ()</th>
                <th>Last Payment</th>
              </tr>
            </thead>
            <tbody>
              {data.members.map((member, idx) => (
                <tr key={idx}>
                  <td><strong>{member.flat_number}</strong></td>
                  <td>{member.owner_name || member.member_name || '-'}</td>
                  <td style={{ textAlign: 'right', color: (member.outstanding_amount || member.outstanding || 0) > 0 ? '#FF3B30' : '#34C759' }}>
                    {formatCurrency(member.outstanding_amount || member.outstanding || 0)}
                  </td>
                  <td>{member.last_payment_date ? new Date(member.last_payment_date).toLocaleDateString() : 'Never'}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ fontWeight: 'bold', backgroundColor: '#f0f0f0', borderTop: '2px solid #ccc' }}>
                <td colSpan="2" style={{ textAlign: 'right', paddingRight: '10px' }}>Total Outstanding:</td>
                <td style={{ textAlign: 'right', color: '#FF3B30', fontSize: '16px' }}>
                  {formatCurrency(data.total_outstanding || 0)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    );
  };

  const renderSocietySummary = (data) => {
    if (!data || !data.summary) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>
          Society Financial Summary for {new Date(data.period.from).toLocaleDateString()} to {new Date(data.period.to).toLocaleDateString()}
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '30px' }}>
          <div style={{ padding: '20px', backgroundColor: '#f0f8ff', borderRadius: '12px', borderLeft: '6px solid #007AFF', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px', fontWeight: '600' }}>SOCIETY BALANCE</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#007AFF' }}>
              {formatCurrency(data.summary.society_balance)}
            </div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '10px' }}>Net of Assets & Liabilities</div>
          </div>

          <div style={{ padding: '20px', backgroundColor: '#f0fff0', borderRadius: '12px', borderLeft: '6px solid #34C759', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px', fontWeight: '600' }}>PERIOD INCOME</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#34C759' }}>
              {formatCurrency(data.summary.period_income)}
            </div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '10px' }}>Revenue from bills & receipts</div>
          </div>

          <div style={{ padding: '20px', backgroundColor: '#fff0f0', borderRadius: '12px', borderLeft: '6px solid #FF3B30', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px', fontWeight: '600' }}>PERIOD EXPENSES</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#FF3B30' }}>
              {formatCurrency(data.summary.period_expenses)}
            </div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '10px' }}>Actual expenses incurred</div>
          </div>
        </div>

        <div style={{ padding: '25px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #eee', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h4 style={{ marginTop: 0, marginBottom: '20px', color: '#333' }}>Society Health Metrics</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid #f9f9f9' }}>
                <span style={{ color: '#666' }}>Total Assets:</span>
                <span style={{ fontWeight: '600' }}>{formatCurrency(data.summary.total_assets)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid #f9f9f9' }}>
                <span style={{ color: '#666' }}>Total Liabilities:</span>
                <span style={{ fontWeight: '600', color: '#FF3B30' }}>{formatCurrency(data.summary.total_liabilities)}</span>
              </div>
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid #f9f9f9' }}>
                <span style={{ color: '#666' }}>Period Surplus/Deficit:</span>
                <span style={{ fontWeight: '600', color: data.summary.surplus_deficit >= 0 ? '#34C759' : '#FF3B30' }}>
                  {formatCurrency(data.summary.surplus_deficit)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <p style={{ marginTop: '20px', fontSize: '13px', color: '#888', fontStyle: 'italic', textAlign: 'center' }}>
          * This is a summarized report for members. For detailed audit queries, please contact the treasurer.
        </p>
      </div>
    );
  };

  const renderMemberLedger = (data) => {
    if (!data || !data.transactions) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>
          My Ledger for Flat {data.flat?.flat_number}
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '20px' }}>
          <div style={{ padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>TOTAL BILLED</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#007AFF' }}>
              {formatCurrency(data.summary?.total_billed)}
            </div>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#f0fff0', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>TOTAL PAID</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#34C759' }}>
              {formatCurrency(data.summary?.total_paid)}
            </div>
          </div>
          <div style={{ padding: '15px', backgroundColor: '#fff0f0', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>OUTSTANDING</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#FF3B30' }}>
              {formatCurrency(data.summary?.outstanding)}
            </div>
          </div>
        </div>

        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Date/Period</th>
                <th>Description</th>
                <th style={{ textAlign: 'right' }}>Amount ()</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.transactions.map((txn, idx) => (
                <tr key={idx}>
                  <td>{txn.date}</td>
                  <td>{txn.description}</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(txn.amount)}</td>
                  <td>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: txn.status === 'paid' ? '#E8F5E9' : '#FFEBEE',
                      color: txn.status === 'paid' ? '#2E7D32' : '#C62828'
                    }}>
                      {txn.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderMyBills = (data) => {
    if (!data || !Array.isArray(data)) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>My Maintenance Bills</h3>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Bill Period</th>
                <th>Bill Number</th>
                <th style={{ textAlign: 'right' }}>Amount ()</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.map((bill, idx) => (
                <tr key={idx}>
                  <td>{`${bill.month}/${bill.year}`}</td>
                  <td>{bill.bill_number}</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(bill.total_amount)}</td>
                  <td>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: bill.status === 'paid' ? '#E8F5E9' : '#FFEBEE',
                      color: bill.status === 'paid' ? '#2E7D32' : '#C62828'
                    }}>
                      {bill.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => window.open(`${api.defaults.baseURL}/maintenance/bills/${bill.id}/download-pdf`, '_blank')}
                      style={{ padding: '4px 8px', backgroundColor: '#007AFF', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
                    >
                      Download PDF
                    </button>
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#666' }}>No bills found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderResources = (data, title, category) => {
    if (!data || !Array.isArray(data)) return null;

    const isAdmin = currentUser && ['SUPER_ADMIN', 'ADMIN', 'SECRETARY', 'TREASURER', 'CHAIRMAN'].includes(currentUser.role);
    const isCurrentCategory = uploadCategory === category;

    const handleFileSelect = (e) => {
      if (e.target.files && e.target.files[0]) {
        setUploadFile(e.target.files[0]);
        setUploadCategory(category);
      }
    };

    const handleUpload = async () => {
      if (!uploadFile) {
        setMessage({ type: 'error', text: 'Please select a file to upload' });
        return;
      }

      setUploadingResource(true);
      setMessage({ type: 'info', text: 'Uploading file...' });

      try {
        await resourceService.uploadResourceFile(uploadFile, category, uploadDescription || null);
        setMessage({ type: 'success', text: 'File uploaded successfully!' });
        setUploadFile(null);
        setUploadDescription('');
        setShowUploadForm(false);
        setUploadCategory(null);
        
        // Refresh the report data
        if (selectedReport) {
          handleGenerateReport(selectedReport);
        }
        
        setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      } catch (error) {
        console.error('Upload error:', error);
        setMessage({ type: 'error', text: getErrorMessage(error) });
      } finally {
        setUploadingResource(false);
      }
    };

    const handleShowUpload = () => {
      setShowUploadForm(!showUploadForm);
      setUploadCategory(category);
      if (showUploadForm && isCurrentCategory) {
        setUploadFile(null);
        setUploadDescription('');
      }
    };

    const getFileUrl = (doc) => {
      // If file_url starts with http, use it directly, otherwise construct download URL
      if (doc.file_url && doc.file_url.startsWith('http')) {
        return doc.file_url;
      }
      // Use the download endpoint
      return resourceService.getFileDownloadUrl(doc.id);
    };

    return (
      <div style={{ marginTop: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          {isAdmin && (
            <button
              onClick={handleShowUpload}
              style={{
                padding: '8px 16px',
                backgroundColor: (showUploadForm && isCurrentCategory) ? '#FF3B30' : '#007AFF',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              {(showUploadForm && isCurrentCategory) ? 'Cancel Upload' : '+ Upload Document'}
            </button>
          )}
        </div>

        {showUploadForm && isAdmin && isCurrentCategory && (
          <div style={{
            marginBottom: '20px',
            padding: '20px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
            border: '1px solid #ddd'
          }}>
            <h4 style={{ marginTop: 0, marginBottom: '15px' }}>Upload New Document</h4>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                Select File (PDF, DOCX, XLSX, Images - Max 10MB)
              </label>
              <input
                type="file"
                accept=".pdf,.docx,.xlsx,.xls,.jpg,.jpeg,.png"
                onChange={handleFileSelect}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
              {uploadFile && (
                <div style={{ marginTop: '5px', fontSize: '12px', color: '#666' }}>
                  Selected: {uploadFile.name} ({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)
                </div>
              )}
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                Description (Optional)
              </label>
              <input
                type="text"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                placeholder="e.g., Annual Audit Report 2024-25"
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
            </div>
            <button
              onClick={handleUpload}
              disabled={!uploadFile || uploadingResource}
              style={{
                padding: '10px 20px',
                backgroundColor: uploadingResource || !uploadFile ? '#ccc' : '#34C759',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: uploadingResource || !uploadFile ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              {uploadingResource ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        )}

        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Description</th>
                <th>Date Added</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.map((doc, idx) => (
                <tr key={idx}>
                  <td><strong>{doc.file_name}</strong></td>
                  <td>{doc.description || '-'}</td>
                  <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                  <td>
                    <a
                      href={getFileUrl(doc)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-block',
                        padding: '6px 12px',
                        backgroundColor: '#34C759',
                        color: 'white',
                        textDecoration: 'none',
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}
                    >
                      View Document
                    </a>
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: '30px', color: '#999' }}>
                    No documents have been uploaded yet in this category.
                    {isAdmin && (
                      <div style={{ marginTop: '10px' }}>
                        <button
                          onClick={() => {
                            setShowUploadForm(true);
                            setUploadCategory(category);
                          }}
                          style={{
                            padding: '8px 16px',
                            backgroundColor: '#007AFF',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '14px'
                          }}
                        >
                          Upload First Document
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderAssetRegister = (data) => {
    if (!data || !data.data) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px' }}>Asset Register - Common Property Record</h3>
        <div className="settings-table-container">
          <table className="settings-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Asset Name</th>
                <th>Category</th>
                <th>Acquisition</th>
                <th style={{ textAlign: 'right' }}>Cost ()</th>
                <th style={{ textAlign: 'right' }}>Book Value ()</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((item, idx) => (
                <tr key={idx}>
                  <td className="font-mono">{item.asset_code}</td>
                  <td style={{ fontWeight: '500' }}>{item.name}</td>
                  <td style={{ textTransform: 'capitalize' }}>{item.category}</td>
                  <td>{new Date(item.acquisition_date).toLocaleDateString()}</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(item.original_cost)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold', color: '#28a745' }}>{formatCurrency(item.wdv)}</td>
                  <td>{item.status}</td>
                </tr>
              ))}
              {data.data.length === 0 && (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '30px', color: '#999' }}>
                    No assets recorded in the register yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderReportData = () => {
    if (!selectedReport || !reportData) return null;

    switch (selectedReport.id) {
      case 'society_summary':
        return renderSocietySummary(reportData);
      case 'my_ledger':
        return renderMemberLedger(reportData);
      case 'trial_balance':
        return renderTrialBalance(reportData);
      case 'general_ledger':
        return renderGeneralLedger(reportData);
      case 'receipts_payments':
        return renderReceiptsPayments(reportData);
      case 'income_expenditure':
        return renderIncomeExpenditure(reportData);
      case 'balance_sheet':
        return renderBalanceSheet(reportData);
      case 'member_dues':
        return renderMemberDues(reportData);
      case 'my_bills':
        return renderMyBills(reportData);
      case 'agm_docs':
        return renderResources(reportData, 'Annual General Meeting (AGM) Documents', 'agm');
      case 'audit_report':
        return renderResources(reportData, 'Society Audit Reports', 'audit');
      case 'asset_register':
        return renderAssetRegister(reportData);
      default:
        return <pre>{JSON.stringify(reportData, null, 2)}</pre>;
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1 className="dashboard-header-title"> Reports</h1>
        <div className="dashboard-header-right">
          <button onClick={() => navigate('/dashboard')} className="dashboard-logout-button">
            Back to Dashboard
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        {message.text && (
          <div className={`message ${message.type}`} style={{
            marginBottom: '20px',
            padding: '15px',
            borderRadius: '8px',
            backgroundColor: message.type === 'error' ? '#fee' : message.type === 'success' ? '#efe' : '#eef',
            border: `1px solid ${message.type === 'error' ? '#f44' : message.type === 'success' ? '#4f4' : '#44f'}`,
            color: message.type === 'error' ? '#c00' : message.type === 'success' ? '#0c0' : '#00c',
          }}>
            {message.text}
          </div>
        )}

        {/* Date Range Selection */}
        <div className="settings-section no-print" style={{ marginBottom: '30px' }}>
          <h2 className="settings-section-title">Date Range Selection</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
            <div className="settings-form-group">
              <label>From Date</label>
              <input
                type="date"
                value={dateRange.from_date}
                onChange={(e) => setDateRange({ ...dateRange, from_date: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
              />
            </div>
            <div className="settings-form-group">
              <label>To Date</label>
              <input
                type="date"
                value={dateRange.to_date}
                onChange={(e) => setDateRange({ ...dateRange, to_date: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
              />
            </div>
            <div className="settings-form-group">
              <label>As On Date (for Trial Balance & Balance Sheet)</label>
              <input
                type="date"
                value={dateRange.as_on_date}
                onChange={(e) => setDateRange({ ...dateRange, as_on_date: e.target.value })}
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                required
              />
            </div>
          </div>
        </div>



        {/* Report Results - Moved Above Grid for visibility */}
        <div ref={reportResultRef}>
          {reportData && (
            <div className="settings-section report-result-section" style={{ marginTop: '0px', marginBottom: '40px', border: '2px solid #007AFF', boxShadow: '0 4px 20px rgba(0,122,255,0.1)' }}>
              <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '15px', borderBottom: '1px solid #ee' }}>
                <h2 className="settings-section-title" style={{ margin: 0, color: '#007AFF' }}>
                  {selectedReport?.title} Result
                </h2>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setReportData(null);
                      setSelectedReport(null);
                    }}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#f5f5f5',
                      color: '#666',
                      border: '1px solid #ddd',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                     Close
                  </button>
                  <button
                    type="button"
                    onClick={() => alert('Exporting to Excel... (Feature coming soon)')}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#34C759',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                     Excel
                  </button>
                  <button
                    type="button"
                    onClick={handleExportPDF}
                    disabled={!selectedReport || !reportData || loading}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: (!selectedReport || !reportData || loading) ? '#ccc' : '#FF3B30',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: (!selectedReport || !reportData || loading) ? 'not-allowed' : 'pointer',
                      fontSize: '14px',
                      opacity: (!selectedReport || !reportData || loading) ? 0.6 : 1
                    }}
                  >
                    {loading ? ' Exporting...' : ' PDF'}
                  </button>
                  <button
                    type="button"
                    onClick={() => window.print()}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#007AFF',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                     Print View
                  </button>
                </div>
              </div>
              <div style={{ padding: '10px' }}>
                {renderReportData()}
              </div>
            </div>
          )}
        </div>

        {/* Available Reports Selection */}
        <div className="settings-section no-print">
          <h2 className="settings-section-title">Available Reports</h2>
          <div className="reports-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '20px'
          }}>
            {filteredReports.map((report) => (
              <div
                key={report.id}
                className={`report-card ${selectedReport?.id === report.id ? 'active' : ''}`}
                style={{
                  padding: '20px',
                  border: '2px solid',
                  borderColor: selectedReport?.id === report.id ? report.color : '#ddd',
                  borderRadius: '12px',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  boxShadow: selectedReport?.id === report.id ? `0 8px 16px ${report.color}22` : '0 2px 4px rgba(0,0,0,0.05)',
                  transform: selectedReport?.id === report.id ? 'translateY(-2px)' : 'none'
                }}
                onClick={() => handleGenerateReport(report)}
              >
                <div style={{ fontSize: '40px', marginBottom: '15px' }}>{report.icon}</div>
                <h3 style={{ marginTop: 0, marginBottom: '10px', color: report.color, fontSize: '18px' }}>
                  {report.title}
                </h3>
                <p style={{ margin: 0, color: '#666', fontSize: '14px', lineHeight: '1.4' }}>
                  {report.description}
                </p>
                {loading && selectedReport?.id === report.id && (
                  <div style={{ marginTop: '15px', color: report.color, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: '600' }}>
                    <div className="spinner-small" style={{
                      width: '16px',
                      height: '16px',
                      border: `2px solid ${report.color}33`,
                      borderTop: `2px solid ${report.color}`,
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite'
                    }}></div>
                    Generating...
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsScreen;

