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
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    MenuItem,
    Alert,
    CircularProgress,
    Stack,
    Card,
    CardContent,
    Tab,
    Tabs,
    Tooltip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import StoreIcon from '@mui/icons-material/Store';
import HistoryIcon from '@mui/icons-material/History';
import MinimizeIcon from '@mui/icons-material/Minimize';
import Layout from '../components/Layout';
import api from '../services/api';

const categories = [
    { value: 'POOJA_MATERIAL', label: 'Pooja Materials' },
    { value: 'GROCERY', label: 'Grocery & Annadanam' },
    { value: 'CLEANING_SUPPLY', label: 'Cleaning Supplies' },
    { value: 'MAINTENANCE', label: 'Maintenance Items' },
    { value: 'STATIONERY', label: 'Stationery' },
    { value: 'CLOTHING', label: 'Clothing/Vastram' },
    { value: 'FURNITURE', label: 'Furniture' },
    { value: 'KITCHEN_EQUIPMENT', label: 'Kitchen Equipment' },
    { value: 'ELECTRONICS', label: 'Electronics' },
    { value: 'OTHER', label: 'Other' },
];

const units = ['KG', 'GRAM', 'LITRE', 'ML', 'PIECE', 'PACKET', 'BOX', 'BUNDLE', 'METRE', 'SET'];

function Inventory() {
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState([]);
    const [balances, setBalances] = useState([]);
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Dialog states
    const [openItemDialog, setOpenItemDialog] = useState(false);
    const [itemDialogMinimized, setItemDialogMinimized] = useState(false);
    const [editingItem, setEditingItem] = useState(null);
    const [itemForm, setItemForm] = useState({
        code: '',
        name: '',
        category: 'POOJA_MATERIAL',
        unit: 'PIECE',
        reorder_level: 0,
        reorder_quantity: 0,
        description: '',
    });

    // fetchData is intentionally tied to the active tab rather than function identity.
    useEffect(() => {
        fetchData();
    }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchData = async () => {
        setLoading(true);
        try {
            if (activeTab === 0) {
                // Dashboard Summary
                const [sumRes, balRes] = await Promise.all([
                    api.get('/api/v1/inventory/summary/'),
                    api.get('/api/v1/inventory/stock-balances/'),
                ]);
                setSummary(sumRes.data);
                setBalances(balRes.data);
            } else if (activeTab === 1) {
                // Item Master
                const res = await api.get('/api/v1/inventory/items/');
                setItems(res.data);
            }
        } catch (err) {
            console.error('Error fetching inventory data:', err);
            setError('Failed to load inventory data');
        } finally {
            setLoading(false);
        }
    };

    const handleOpenItemDialog = (item = null) => {
        if (item) {
            setEditingItem(item);
            setItemForm({
                code: item.code,
                name: item.name,
                category: item.category,
                unit: item.unit,
                reorder_level: item.reorder_level,
                reorder_quantity: item.reorder_quantity,
                description: item.description || '',
            });
        } else {
            setEditingItem(null);
            setItemForm({
                code: '',
                name: '',
                category: 'POOJA_MATERIAL',
                unit: 'PIECE',
                reorder_level: 0,
                reorder_quantity: 0,
                description: '',
            });
        }
        setItemDialogMinimized(false);
        setOpenItemDialog(true);
    };

    const handleCloseItemDialog = () => {
        setOpenItemDialog(false);
        setItemDialogMinimized(false);
    };

    const handleMinimizeItemDialog = () => {
        setOpenItemDialog(false);
        setItemDialogMinimized(true);
    };

    const handleRestoreItemDialog = () => {
        setOpenItemDialog(true);
        setItemDialogMinimized(false);
    };

    const handleItemDialogRequestClose = (_event, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
            handleMinimizeItemDialog();
            return;
        }
        handleCloseItemDialog();
    };

    const handleSaveItem = async () => {
        try {
            setLoading(true);
            if (editingItem) {
                await api.put(`/api/v1/inventory/items/${editingItem.id}`, itemForm);
                setSuccess('Item updated successfully');
            } else {
                await api.post('/api/v1/inventory/items/', itemForm);
                setSuccess('Item created successfully');
            }
            handleCloseItemDialog();
            fetchData();
        } catch (err) {
            setError(err.response?.data?.detail || 'Error saving item');
        } finally {
            setLoading(false);
            setTimeout(() => {
                setSuccess('');
                setError('');
            }, 3000);
        }
    };

    const handleDeleteItem = async (id) => {
        if (window.confirm('Are you sure you want to deactivate this item?')) {
            try {
                await api.delete(`/api/v1/inventory/items/${id}`);
                setSuccess('Item deactivated');
                fetchData();
            } catch (err) {
                setError('Error deleting item');
            }
        }
    };

    const renderDashboard = () => (
        <Box>
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#E3F2FD', borderLeft: '5px solid #2196F3' }}>
                        <CardContent>
                            <Box display="flex" alignItems="center">
                                <Inventory2Icon sx={{ color: '#2196F3', fontSize: 40, mr: 2 }} />
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {summary?.totalItems || 0}
                                    </Typography>
                                    <Typography variant="body2" color="textSecondary">
                                        Total Items
                                    </Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#FFF3E0', borderLeft: '5px solid #FF9800' }}>
                        <CardContent>
                            <Box display="flex" alignItems="center">
                                <WarningAmberIcon sx={{ color: '#FF9800', fontSize: 40, mr: 2 }} />
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {summary?.lowStockItems || 0}
                                    </Typography>
                                    <Typography variant="body2" color="textSecondary">
                                        Low Stock Alerts
                                    </Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#E8F5E9', borderLeft: '5px solid #4CAF50' }}>
                        <CardContent>
                            <Box display="flex" alignItems="center">
                                <StoreIcon sx={{ color: '#4CAF50', fontSize: 40, mr: 2 }} />
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {summary?.totalStores || 0}
                                    </Typography>
                                    <Typography variant="body2" color="textSecondary">
                                        Total Stores
                                    </Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: '#F3E5F5', borderLeft: '5px solid #9C27B0' }}>
                        <CardContent>
                            <Box display="flex" alignItems="center">
                                <Typography variant="h4" sx={{ color: '#9C27B0', mr: 2, fontWeight: 'bold' }}>
                                    ₹
                                </Typography>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {summary?.totalValue?.toLocaleString('en-IN') || 0}
                                    </Typography>
                                    <Typography variant="body2" color="textSecondary">
                                        Inventory Value
                                    </Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom display="flex" alignItems="center">
                    <Inventory2Icon sx={{ mr: 1 }} /> Current Stock Balances
                </Typography>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                                <TableCell>Item Code</TableCell>
                                <TableCell>Item Name</TableCell>
                                <TableCell>Store</TableCell>
                                <TableCell align="right">Quantity</TableCell>
                                <TableCell>Unit</TableCell>
                                <TableCell align="right">Value (₹)</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {balances.length > 0 ? (
                                balances.map((row) => (
                                    <TableRow key={row.id}>
                                        <TableCell>{row.item_code}</TableCell>
                                        <TableCell fontWeight="500">{row.item_name}</TableCell>
                                        <TableCell>{row.store_name}</TableCell>
                                        <TableCell align="right">{row.quantity}</TableCell>
                                        <TableCell>{row.unit}</TableCell>
                                        <TableCell align="right">{row.value.toLocaleString('en-IN')}</TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={6} align="center">
                                        No stock data available
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>
        </Box>
    );

    const renderItemMaster = () => (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6">Item Master Register</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpenItemDialog()}
                    sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#E68A2E' } }}
                >
                    Add New Item
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                            <TableCell>Code</TableCell>
                            <TableCell>Name</TableCell>
                            <TableCell>Category</TableCell>
                            <TableCell>Unit</TableCell>
                            <TableCell align="right">Reorder Level</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {items.map((item) => (
                            <TableRow key={item.id}>
                                <TableCell>{item.code}</TableCell>
                                <TableCell fontWeight="500">{item.name}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={item.category.replace('_', ' ')}
                                        size="small"
                                        variant="outlined"
                                        sx={{ textTransform: 'capitalize' }}
                                    />
                                </TableCell>
                                <TableCell>{item.unit}</TableCell>
                                <TableCell align="right">{item.reorder_level}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={item.is_active ? 'Active' : 'Inactive'}
                                        color={item.is_active ? 'success' : 'default'}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <IconButton onClick={() => handleOpenItemDialog(item)} color="primary" size="small">
                                        <EditIcon fontSize="small" />
                                    </IconButton>
                                    <IconButton onClick={() => handleDeleteItem(item.id)} color="error" size="small">
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Item Dialog */}
            <Dialog open={openItemDialog} onClose={handleItemDialogRequestClose} maxWidth="sm" fullWidth>
                <DialogTitle sx={{ pr: 7, position: 'relative' }}>
                    <Tooltip title="Minimize">
                        <IconButton
                            aria-label="minimize inventory item dialog"
                            onClick={handleMinimizeItemDialog}
                            size="small"
                            sx={{ position: 'absolute', right: 12, top: 12 }}
                        >
                            <MinimizeIcon />
                        </IconButton>
                    </Tooltip>
                    {editingItem ? 'Edit Item' : 'Add New Item'}
                </DialogTitle>
                <DialogContent dividers>
                    <Stack spacing={2} sx={{ mt: 1 }}>
                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    fullWidth
                                    label="Item Code"
                                    value={itemForm.code}
                                    onChange={(e) => setItemForm({ ...itemForm, code: e.target.value })}
                                    placeholder="e.g. PJ-OIL-01"
                                    required
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    fullWidth
                                    select
                                    label="Category"
                                    value={itemForm.category}
                                    onChange={(e) => setItemForm({ ...itemForm, category: e.target.value })}
                                >
                                    {categories.map((cat) => (
                                        <MenuItem key={cat.value} value={cat.value}>
                                            {cat.label}
                                        </MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    label="Item Name"
                                    value={itemForm.name}
                                    onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })}
                                    placeholder="e.g. Gingelly Oil"
                                    required
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField
                                    fullWidth
                                    select
                                    label="Unit"
                                    value={itemForm.unit}
                                    onChange={(e) => setItemForm({ ...itemForm, unit: e.target.value })}
                                >
                                    {units.map((u) => (
                                        <MenuItem key={u} value={u}>
                                            {u}
                                        </MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField
                                    fullWidth
                                    label="Reorder Level"
                                    type="number"
                                    value={itemForm.reorder_level}
                                    onChange={(e) => setItemForm({ ...itemForm, reorder_level: parseFloat(e.target.value) })}
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField
                                    fullWidth
                                    label="Reorder Qty"
                                    type="number"
                                    value={itemForm.reorder_quantity}
                                    onChange={(e) => setItemForm({ ...itemForm, reorder_quantity: parseFloat(e.target.value) })}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    label="Description"
                                    multiline
                                    rows={2}
                                    value={itemForm.description}
                                    onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })}
                                />
                            </Grid>
                        </Grid>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseItemDialog}>Cancel</Button>
                    <Button variant="contained" onClick={handleSaveItem}>
                        Save Item
                    </Button>
                </DialogActions>
            </Dialog>

            {itemDialogMinimized && (
                <Box
                    sx={{
                        position: 'fixed',
                        right: 24,
                        bottom: 24,
                        zIndex: (theme) => theme.zIndex.modal + 1,
                    }}
                >
                    <Button variant="contained" color="warning" onClick={handleRestoreItemDialog}>
                        Resume Item Form
                    </Button>
                </Box>
            )}
        </Box>
    );

    return (
        <Layout>
            <Box sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom fontWeight="bold" sx={{ color: '#FF9933' }}>
                    Inventory Management
                </Typography>

                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}
                {success && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                        {success}
                    </Alert>
                )}

                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                    <Tabs value={activeTab} onChange={(e, nv) => setActiveTab(nv)}>
                        <Tab icon={<StoreIcon />} label="Dashboard & Stocks" iconPosition="start" />
                        <Tab icon={<Inventory2Icon />} label="Item Master" iconPosition="start" />
                        <Tab icon={<HistoryIcon />} label="Movements" iconPosition="start" disabled />
                    </Tabs>
                </Box>

                {loading ? (
                    <Box display="flex" justifyContent="center" p={5}>
                        <CircularProgress />
                    </Box>
                ) : activeTab === 0 ? (
                    renderDashboard()
                ) : (
                    renderItemMaster()
                )}
            </Box>
        </Layout>
    );
}

export default Inventory;
