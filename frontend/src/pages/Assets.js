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
    Stack,
    Card,
    CardContent,
    Tab,
    Tabs,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    MenuItem,
    Tooltip,
    Avatar,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EngineeringIcon from '@mui/icons-material/Engineering';
import AssessmentIcon from '@mui/icons-material/Assessment';
import GavelIcon from '@mui/icons-material/Gavel';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ConstructionIcon from '@mui/icons-material/Construction';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import DiamondIcon from '@mui/icons-material/Diamond';
import HistoryIcon from '@mui/icons-material/History';
import Layout from '../components/Layout';
import api from '../services/api';

const assetTypes = [
    { value: 'fixed', label: 'Fixed Asset (Land/Bldg)', color: '#2196F3' },
    { value: 'movable', label: 'Movable Asset', color: '#4CAF50' },
    { value: 'precious', label: 'Precious Ornaments', color: '#FFD700' },
    { value: 'idol', label: 'Temple Idols (Vigrahas)', color: '#9C27B0' },
    { value: 'cwip', label: 'Work-in-Progress (CWIP)', color: '#FF9800' },
];

function Assets() {
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(true);
    const [assets, setAssets] = useState([]);
    const [cwipProjects, setCwipProjects] = useState([]);
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState('');

    // Revaluation Dialog State
    const [revalDialogOpen, setRevalDialogOpen] = useState(false);
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [revalData, setRevalData] = useState({
        revaluation_date: new Date().toISOString().split('T')[0],
        revalued_amount: 0,
        valuation_method: 'MARKET_VALUE',
        valuer_name: '',
        notes: ''
    });

    // fetchData is intentionally re-created from current tab state; rerun only when tab changes.
    useEffect(() => {
        fetchData();
    }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch Summary always to keep header updated
            const summaryRes = await api.get('/api/v1/assets/reports/summary/');
            setSummary(summaryRes.data);

            if (activeTab === 0) {
                // Asset Register
                const res = await api.get('/api/v1/assets/');
                setAssets(res.data);
            } else if (activeTab === 1) {
                // CWIP
                const res = await api.get('/api/v1/assets/cwip/');
                setCwipProjects(res.data);
            }
        } catch (err) {
            console.error('Error fetching Asset data:', err);
            setError('Failed to load asset data. Please check connection.');
        } finally {
            setLoading(false);
        }
    };

    const handleRevalOpen = (asset) => {
        setSelectedAsset(asset);
        setRevalData({
            ...revalData,
            revalued_amount: asset.current_book_value
        });
        setRevalDialogOpen(true);
    };

    const handleRevalSubmit = async () => {
        try {
            await api.post(`/api/v1/assets/revaluation/?asset_id=${selectedAsset.id}`, revalData);
            setRevalDialogOpen(false);
            fetchData();
        } catch (err) {
            alert('Error updating valuation: ' + (err.response?.data?.detail || err.message));
        }
    };

    const getAssetTypeLabel = (type) => {
        return assetTypes.find(t => t.value === type)?.label || type;
    };

    const getAssetTypeColor = (type) => {
        return assetTypes.find(t => t.value === type)?.color || '#757575';
    };

    const renderSummaryCards = () => (
        <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)', borderTop: '4px solid #FF9933' }}>
                    <CardContent>
                        <Stack direction="row" spacing={2} alignItems="center">
                            <Avatar sx={{ bgcolor: '#FFF3E0', color: '#FF9933' }}>
                                <AccountBalanceIcon />
                            </Avatar>
                            <Box>
                                <Typography color="textSecondary" variant="caption">Net Asset Value</Typography>
                                <Typography variant="h5" fontWeight="bold">ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹{summary?.net_asset_value?.toLocaleString('en-IN')}</Typography>
                            </Box>
                        </Stack>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)', borderTop: '4px solid #FFD700' }}>
                    <CardContent>
                        <Stack direction="row" spacing={2} alignItems="center">
                            <Avatar sx={{ bgcolor: '#FFFDE7', color: '#FFD700' }}>
                                <DiamondIcon />
                            </Avatar>
                            <Box>
                                <Typography color="textSecondary" variant="caption">Precious Assets</Typography>
                                <Typography variant="h5" fontWeight="bold">{assets.filter(a => a.asset_type === 'precious').length} Items</Typography>
                            </Box>
                        </Stack>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)', borderTop: '4px solid #2196F3' }}>
                    <CardContent>
                        <Stack direction="row" spacing={2} alignItems="center">
                            <Avatar sx={{ bgcolor: '#E3F2FD', color: '#2196F3' }}>
                                <ConstructionIcon />
                            </Avatar>
                            <Box>
                                <Typography color="textSecondary" variant="caption">Active Projects (CWIP)</Typography>
                                <Typography variant="h5" fontWeight="bold">{summary?.active_cwip_projects || 0}</Typography>
                            </Box>
                        </Stack>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)', borderTop: '4px solid #4CAF50' }}>
                    <CardContent>
                        <Stack direction="row" spacing={2} alignItems="center">
                            <Avatar sx={{ bgcolor: '#E8F5E9', color: '#4CAF50' }}>
                                <TrendingUpIcon />
                            </Avatar>
                            <Box>
                                <Typography color="textSecondary" variant="caption">Total Investment</Typography>
                                <Typography variant="h5" fontWeight="bold">ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹{summary?.total_cost?.toLocaleString('en-IN')}</Typography>
                            </Box>
                        </Stack>
                    </CardContent>
                </Card>
            </Grid>
        </Grid>
    );

    const renderRegister = () => (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6" fontWeight="bold">Temple Asset Register</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    sx={{ borderRadius: 2, bgcolor: '#FF9933', boxShadow: '0 4px 10px rgba(255,153,51,0.3)', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                    Register New Asset
                </Button>
            </Box>

            <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
                <Table>
                    <TableHead>
                        <TableRow sx={{ bgcolor: '#f8f9fa' }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Asset ID</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Asset Details</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Classification</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Physical Specs</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Market Value (ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹)</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {assets.map((asset) => (
                            <TableRow key={asset.id} hover>
                                <TableCell>
                                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 'bold', color: '#FF9933' }}>
                                        {asset.asset_number}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Typography variant="body2" fontWeight="bold">{asset.name}</Typography>
                                    <Typography variant="caption" color="textSecondary" display="block">
                                        Loc: {asset.location || 'Not Specified'}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={getAssetTypeLabel(asset.asset_type)}
                                        size="small"
                                        sx={{
                                            bgcolor: `${getAssetTypeColor(asset.asset_type)}15`,
                                            color: getAssetTypeColor(asset.asset_type),
                                            fontWeight: 'bold',
                                            border: `1px solid ${getAssetTypeColor(asset.asset_type)}30`
                                        }}
                                    />
                                </TableCell>
                                <TableCell>
                                    <Stack direction="row" spacing={0.5}>
                                        {asset.weight_grams > 0 && (
                                            <Tooltip title="Weight">
                                                <Chip label={`${asset.weight_grams}g`} size="small" sx={{ height: 20, fontSize: '0.65rem' }} />
                                            </Tooltip>
                                        )}
                                        {asset.purity && (
                                            <Tooltip title="Purity">
                                                <Chip label={asset.purity} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
                                            </Tooltip>
                                        )}
                                        {asset.material && (
                                            <Tooltip title="Material">
                                                <Chip label={asset.material} size="small" color="secondary" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
                                            </Tooltip>
                                        )}
                                    </Stack>
                                </TableCell>
                                <TableCell align="right">
                                    <Typography variant="body2" fontWeight="bold">
                                        {asset.current_book_value?.toLocaleString('en-IN')}
                                    </Typography>
                                    {asset.revaluation_reserve > 0 && (
                                        <Typography variant="caption" color="success.main" display="block">
                                            + {asset.revaluation_reserve.toLocaleString('en-IN')} (Appreciation)
                                        </Typography>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={asset.status.toUpperCase()}
                                        size="small"
                                        color={asset.status === 'active' ? 'success' : 'default'}
                                        sx={{ fontSize: '0.7rem', height: 22 }}
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Stack direction="row" spacing={1} justifyContent="center">
                                        <Tooltip title="View Details">
                                            <IconButton size="small" color="primary">
                                                <VisibilityIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        {(asset.asset_type === 'precious' || asset.asset_type === 'idol') && (
                                            <Tooltip title="Update Valuation / Appreciation">
                                                <IconButton size="small" sx={{ color: '#FF9933' }} onClick={() => handleRevalOpen(asset)}>
                                                    <TrendingUpIcon fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                        )}
                                    </Stack>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );

    const renderCWIP = () => (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6" fontWeight="bold">Work-in-Progress (CWIP) Projects</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    sx={{ borderRadius: 2, bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                    New Project
                </Button>
            </Box>

            <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
                <Table>
                    <TableHead>
                        <TableRow sx={{ bgcolor: '#f8f9fa' }}>
                            <TableCell sx={{ fontWeight: 'bold' }}>Project #</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Project Name</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Start Date</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Budget (ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹)</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Expenditure (ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹)</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {cwipProjects.map((project) => (
                            <TableRow key={project.id} hover>
                                <TableCell sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{project.cwip_number}</TableCell>
                                <TableCell>
                                    <Typography variant="body2" fontWeight="bold">{project.project_name}</Typography>
                                    <Typography variant="caption" color="textSecondary">{project.description}</Typography>
                                </TableCell>
                                <TableCell>{new Date(project.start_date).toLocaleDateString()}</TableCell>
                                <TableCell align="right">{project.total_budget?.toLocaleString('en-IN')}</TableCell>
                                <TableCell align="right">
                                    <Typography variant="body2" fontWeight="bold" color={project.total_expenditure > project.total_budget ? 'error.main' : 'inherit'}>
                                        {project.total_expenditure?.toLocaleString('en-IN')}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={project.status.replace('_', ' ').toUpperCase()}
                                        size="small"
                                        color={project.status === 'in_progress' ? 'warning' : 'success'}
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Stack direction="row" spacing={1} justifyContent="center">
                                        <Tooltip title="Add Expense">
                                            <IconButton size="small" color="primary">
                                                <AddIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title="Capitalize to Asset">
                                            <IconButton size="small" color="success">
                                                <GavelIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </Stack>
                                </TableCell>
                            </TableRow>
                        ))}
                        {cwipProjects.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={7} align="center">
                                    <Box p={3} textAlign="center">
                                        <ConstructionIcon sx={{ fontSize: 40, color: 'divider', mb: 1 }} />
                                        <Typography color="textSecondary">No active construction or work-in-progress projects</Typography>
                                    </Box>
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
            <Box sx={{ p: 4, bgcolor: '#fdfdfd', minHeight: '100%' }}>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={4}>
                    <Box>
                        <Typography variant="h4" fontWeight="bold" sx={{ color: '#FF9933', mb: 1 }}>
                            ÃƒÂ°Ã…Â¸Ã‚ÂÃ¢â‚¬ÂºÃƒÂ¯Ã‚Â¸Ã‚Â Asset Management
                        </Typography>
                        <Typography variant="body1" color="textSecondary">
                            Track, value, and manage temple properties, ornaments, and idols.
                        </Typography>
                    </Box>
                    <Stack direction="row" spacing={2}>
                        <Button variant="outlined" startIcon={<HistoryIcon />} sx={{ borderRadius: 2 }}>
                            History
                        </Button>
                        <Button variant="outlined" startIcon={<AssessmentIcon />} sx={{ borderRadius: 2 }}>
                            Audit Report
                        </Button>
                    </Stack>
                </Box>

                {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

                {renderSummaryCards()}

                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                    <Tabs
                        value={activeTab}
                        onChange={(e, nv) => setActiveTab(nv)}
                        sx={{
                            '& .MuiTab-root': { fontWeight: 'bold' },
                            '& .Mui-selected': { color: '#FF9933' },
                            '& .MuiTabs-indicator': { bgcolor: '#FF9933' }
                        }}
                    >
                        <Tab icon={<EngineeringIcon />} label="Asset Register" iconPosition="start" />
                        <Tab icon={<ConstructionIcon />} label="Work in Progress (CWIP)" iconPosition="start" />
                        <Tab icon={<AssessmentIcon />} label="Valuation & Reports" iconPosition="start" />
                    </Tabs>
                </Box>

                {loading ? (
                    <Box display="flex" justifyContent="center" p={10}>
                        <CircularProgress sx={{ color: '#FF9933' }} />
                    </Box>
                ) : (
                    <Box sx={{ animation: 'fadeIn 0.5s ease-in' }}>
                        {activeTab === 0 ? renderRegister() : activeTab === 1 ? renderCWIP() : <Typography p={5} align="center" color="textSecondary">Reports & Analytics coming soon</Typography>}
                    </Box>
                )}

                {/* Revaluation Dialog */}
                <Dialog open={revalDialogOpen} onClose={() => setRevalDialogOpen(false)} maxWidth="sm" fullWidth>
                    <DialogTitle sx={{ bgcolor: '#FF9933', color: 'white', fontWeight: 'bold' }}>
                        Update Asset Valuation / Appreciation
                    </DialogTitle>
                    <DialogContent sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                            Asset: <strong>{selectedAsset?.name}</strong> ({selectedAsset?.asset_number})
                        </Typography>
                        <Typography variant="body2" color="textSecondary" mb={3}>
                            Current Book Value: ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹{selectedAsset?.current_book_value?.toLocaleString('en-IN')}
                        </Typography>

                        <Grid container spacing={2}>
                            <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    label="New Revalued Amount (ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹)"
                                    type="number"
                                    value={revalData.revalued_amount}
                                    onChange={(e) => setRevalData({ ...revalData, revalued_amount: e.target.value })}
                                    helperText={revalData.revalued_amount > selectedAsset?.current_book_value ? "Value Appreciation (Positive Reserve)" : "Value Impairment (Negative Reserve)"}
                                />
                            </Grid>
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    label="Revaluation Date"
                                    type="date"
                                    value={revalData.revaluation_date}
                                    onChange={(e) => setRevalData({ ...revalData, revaluation_date: e.target.value })}
                                />
                            </Grid>
                            <Grid item xs={6}>
                                <TextField
                                    fullWidth
                                    select
                                    label="Valuation Method"
                                    value={revalData.valuation_method}
                                    onChange={(e) => setRevalData({ ...revalData, valuation_method: e.target.value })}
                                >
                                    <MenuItem value="MARKET_VALUE">Current Market Price</MenuItem>
                                    <MenuItem value="PROFESSIONAL_VALUER">Professional Valuator</MenuItem>
                                    <MenuItem value="INDEX_BASED">Index Based</MenuItem>
                                </TextField>
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    label="Valuator Name / Agency"
                                    value={revalData.valuer_name}
                                    onChange={(e) => setRevalData({ ...revalData, valuer_name: e.target.value })}
                                />
                            </Grid>
                        </Grid>
                    </DialogContent>
                    <DialogActions sx={{ p: 3 }}>
                        <Button onClick={() => setRevalDialogOpen(false)}>Cancel</Button>
                        <Button variant="contained" onClick={handleRevalSubmit} sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}>
                            Update Valuation
                        </Button>
                    </DialogActions>
                </Dialog>
            </Box>
        </Layout>
    );
}

export default Assets;
