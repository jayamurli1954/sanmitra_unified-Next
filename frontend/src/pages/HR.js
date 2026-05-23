import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Grid,
    Paper,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    IconButton,
    Alert,
    CircularProgress,
    Card,
    CardContent,
    Tab,
    Tabs,
    Avatar,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import BadgeIcon from '@mui/icons-material/Badge';
import EventAvailableIcon from '@mui/icons-material/EventAvailable';
import PaymentsIcon from '@mui/icons-material/Payments';
import VisibilityIcon from '@mui/icons-material/Visibility';
import Layout from '../components/Layout';
import api from '../services/api';

function HR() {
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(true);
    const [employees, setEmployees] = useState([]);
    const [attendance, setAttendance] = useState([]);
    const [error, setError] = useState('');

    // fetchData is intentionally tied to the active tab rather than function identity.
    useEffect(() => {
        fetchData();
    }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchData = async () => {
        setLoading(true);
        try {
            if (activeTab === 0) {
                // Employee List
                const res = await api.get('/api/v1/hr/employees/');
                setEmployees(res.data);
            } else if (activeTab === 1) {
                // Attendance
                const res = await api.get('/api/v1/hr/attendance/monthly', {
                    params: {
                        month: new Date().getMonth() + 1,
                        year: new Date().getFullYear(),
                    },
                });
                setAttendance(res.data);
            }
        } catch (err) {
            console.error('Error fetching HR data:', err);
            setError('Failed to load HR data. Note: The backend HR module must be fully initialized.');
        } finally {
            setLoading(false);
        }
    };

    const renderEmployees = () => (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6">Employee & Priest Directory</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                    Add New Employee
                </Button>
            </Box>

            <Grid container spacing={3} mb={4}>
                <Grid item xs={12} sm={4}>
                    <Card variant="outlined" sx={{ textAlign: 'center', p: 1, borderTop: '4px solid #FF9933' }}>
                        <Typography color="textSecondary" variant="caption">Total Staff</Typography>
                        <Typography variant="h5" fontWeight="bold">{employees.length}</Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card variant="outlined" sx={{ textAlign: 'center', p: 1, borderTop: '4px solid #4CAF50' }}>
                        <Typography color="textSecondary" variant="caption">Active Employees</Typography>
                        <Typography variant="h5" fontWeight="bold" color="success.main">
                            {employees.filter(e => e.is_active).length}
                        </Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card variant="outlined" sx={{ textAlign: 'center', p: 1, borderTop: '4px solid #2196F3' }}>
                        <Typography color="textSecondary" variant="caption">Departments</Typography>
                        <Typography variant="h5" fontWeight="bold">
                            {[...new Set(employees.map(e => e.department))].filter(Boolean).length || 1}
                        </Typography>
                    </Card>
                </Grid>
            </Grid>

            <Grid container spacing={2}>
                {employees.map((emp) => (
                    <Grid item xs={12} sm={6} md={4} key={emp.id}>
                        <Card variant="outlined" sx={{ borderLeft: '5px solid #2196F3' }}>
                            <CardContent>
                                <Box display="flex" alignItems="center" mb={2}>
                                    <Avatar sx={{ bgcolor: '#2196F3', mr: 2 }}>{emp.full_name[0]}</Avatar>
                                    <Box>
                                        <Typography variant="h6" fontWeight="bold">
                                            {emp.full_name}
                                        </Typography>
                                        <Typography variant="body2" color="textSecondary">
                                            {emp.designation} | {emp.department}
                                        </Typography>
                                    </Box>
                                </Box>
                                <Typography variant="body2">
                                    <strong>ID:</strong> {emp.employee_id} | <strong>Mobile:</strong> {emp.mobile}
                                </Typography>
                                <Box mt={2} display="flex" justifyContent="space-between" alignItems="center">
                                    <Chip label={emp.employment_type} size="small" variant="outlined" />
                                    <Chip
                                        label={emp.is_active ? 'Active' : 'Inactive'}
                                        color={emp.is_active ? 'success' : 'default'}
                                        size="small"
                                    />
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
                {employees.length === 0 && (
                    <Grid item xs={12}>
                        <Paper sx={{ p: 3, textAlign: 'center' }}>
                            <Typography color="textSecondary">No employees registered found</Typography>
                        </Paper>
                    </Grid>
                )}
            </Grid>
        </Box>
    );

    const renderAttendance = () => (
        <Box>
            <Typography variant="h6" mb={3}>Monthly Attendance Tracking</Typography>
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                            <TableCell>Employee Name</TableCell>
                            <TableCell align="center">Present Days</TableCell>
                            <TableCell align="center">Leaves</TableCell>
                            <TableCell align="center">Late Entries</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {attendance.map((row) => (
                            <TableRow key={row.employee_id}>
                                <TableCell fontWeight="500">{row.employee_name}</TableCell>
                                <TableCell align="center">{row.present_days}</TableCell>
                                <TableCell align="center">{row.leave_days}</TableCell>
                                <TableCell align="center">{row.late_days}</TableCell>
                                <TableCell align="center">
                                    <IconButton color="primary" size="small">
                                        <VisibilityIcon fontSize="small" />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                        {attendance.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={5} align="center">
                                    No attendance records found for the current month
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );

    return (
        <Layout>
            <Box sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom fontWeight="bold" sx={{ color: '#FF9933' }}>
                    ÃƒÂ°Ã…Â¸Ã¢â‚¬ËœÃ‚Â¥ HR & Salary Management
                </Typography>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                    <Tabs value={activeTab} onChange={(e, nv) => setActiveTab(nv)}>
                        <Tab icon={<BadgeIcon />} label="Employee List" iconPosition="start" />
                        <Tab icon={<EventAvailableIcon />} label="Attendance" iconPosition="start" />
                        <Tab icon={<PaymentsIcon />} label="Payroll & Salaries" iconPosition="start" disabled />
                    </Tabs>
                </Box>

                {loading ? (
                    <Box display="flex" justifyContent="center" p={5}>
                        <CircularProgress />
                    </Box>
                ) : activeTab === 0 ? (
                    renderEmployees()
                ) : (
                    renderAttendance()
                )}
            </Box>
        </Layout>
    );
}

export default HR;
