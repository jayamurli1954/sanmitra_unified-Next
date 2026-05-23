/* eslint-disable no-irregular-whitespace */
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
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import HistoryIcon from '@mui/icons-material/History';
import SavingsIcon from '@mui/icons-material/Savings';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import VisibilityIcon from '@mui/icons-material/Visibility';
import Layout from '../components/Layout';
import api from '../services/api';

function Hundi() {
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(true);
    const [hundiMasters, setHundiMasters] = useState([]);
    const [openings, setOpenings] = useState([]);
    const [_reportRange, _setReportRange] = useState({
        from: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
        to: new Date().toISOString().split('T')[0],
    });
    const [error, setError] = useState('');
    const [_success, _setSuccess] = useState('');

    // fetchData is intentionally tied to the active tab rather than function identity.
    useEffect(() => {
        fetchData();
    }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchData = async () => {
        setLoading(true);
        try {
            if (activeTab === 0) {
                // Hundi Register
                const res = await api.get('/api/v1/hundi/masters');
                setHundiMasters(res.data);
            } else if (activeTab === 1) {
                // Recent Openings
                const res = await api.get('/api/v1/hundi/openings');
                setOpenings(res.data);
            }
        } catch (err) {
            console.error('Error fetching hundi data:', err);
            setError('Failed to load hundi data');
        } finally {
            setLoading(false);
        }
    };

    const renderRegister = () => (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6">Hundi (Collection Box) Register</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                    Register New Hundi
                </Button>
            </Box>

            <Grid container spacing={2}>
                {hundiMasters.map((hundi) => (
                    <Grid item xs={12} sm={6} md={4} key={hundi.id}>
                        <Card variant="outlined" sx={{ borderLeft: '5px solid #FF9933' }}>
                            <CardContent>
                                <Typography variant="h6" fontWeight="bold">
                                    {hundi.hundi_name}
                                </Typography>
                                <Typography variant="body2" color="textSecondary" gutterBottom>
                                    Code: {hundi.hundi_code} | Location: {hundi.hundi_location}
                                </Typography>
                                <Box mt={2} display="flex" justifyContent="space-between" alignItems="center">
                                    <Chip
                                        label={hundi.is_active ? 'Active' : 'Inactive'}
                                        color={hundi.is_active ? 'success' : 'default'}
                                        size="small"
                                    />
                                    <Button size="small" startIcon={<HistoryIcon />}>
                                        History
                                    </Button>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
                {hundiMasters.length === 0 && (
                    <Grid item xs={12}>
                        <Paper sx={{ p: 3, textAlign: 'center' }}>
                            <Typography color="textSecondary">No hundis registered yet</Typography>
                        </Paper>
                    </Grid>
                )}
            </Grid>
        </Box>
    );

    const renderOpenings = () => (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6">Recent Hundi Openings & Counting</Typography>
                <Button variant="outlined" startIcon={<AddIcon />}>
                    Schedule Opening
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                            <TableCell>Opening Date</TableCell>
                            <TableCell>Hundi Code</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="right">Amount (Rs)</TableCell>
                            <TableCell>Verified By</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {openings.map((op) => (
                            <TableRow key={op.id}>
                                <TableCell>{new Date(op.scheduled_date).toLocaleDateString()}</TableCell>
                                <TableCell fontWeight="500">{op.hundi_code}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={op.status}
                                        size="small"
                                        color={
                                            op.status === 'RECONCILED' || op.status === 'DEPOSITED'
                                                ? 'success'
                                                : op.status === 'SCHEDULED'
                                                    ? 'info'
                                                    : 'warning'
                                        }
                                    />
                                </TableCell>
                                <TableCell align="right">{op.total_amount?.toLocaleString('en-IN') || 0}</TableCell>
                                <TableCell>
                                    {op.verified_by_user_1_id ? 'Yes' : 'Pending'}
                                </TableCell>
                                <TableCell align="center">
                                    <IconButton color="primary" size="small">
                                        <VisibilityIcon fontSize="small" />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                        {openings.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} align="center">
                                    No hundi opening records found
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
                    Hundi Management
                </Typography>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                    <Tabs value={activeTab} onChange={(e, nv) => setActiveTab(nv)}>
                        <Tab icon={<SavingsIcon />} label="Hundi Register" iconPosition="start" />
                        <Tab icon={<HistoryIcon />} label="Counting Sessions" iconPosition="start" />
                        <Tab icon={<AccountBalanceIcon />} label="Bank Deposits" iconPosition="start" disabled />
                    </Tabs>
                </Box>

                {loading ? (
                    <Box display="flex" justifyContent="center" p={5}>
                        <CircularProgress />
                    </Box>
                ) : activeTab === 0 ? (
                    renderRegister()
                ) : (
                    renderOpenings()
                )}
            </Box>
        </Layout>
    );
}

export default Hundi;
