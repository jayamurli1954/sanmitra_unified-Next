import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Paper,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  InputAdornment,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import PhoneIcon from '@mui/icons-material/Phone';
import EmailIcon from '@mui/icons-material/Email';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PeopleIcon from '@mui/icons-material/People';
import SearchIcon from '@mui/icons-material/Search';
import VolunteerActivismIcon from '@mui/icons-material/VolunteerActivism';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import CurrencyRupeeIcon from '@mui/icons-material/CurrencyRupee';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import Layout from '../components/Layout';
import api from '../services/api';
import ExportButton from '../components/ExportButton';
import PrintButton from '../components/PrintButton';
import { exportToCSV, exportToExcel, exportToPDF } from '../utils/export';

const CONTRIBUTION_FETCH_LIMIT = 500;

function Devotees() {
  const navigate = useNavigate();
  const [devotees, setDevotees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [contributionFilter, setContributionFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchDevotees();
  }, []);

  const firstText = (...values) => {
    for (const value of values) {
      const text = value === null || value === undefined ? '' : String(value).trim();
      if (text) return text;
    }
    return '';
  };

  const normalizePhone = (value) => {
    const digits = String(value || '').replace(/\D/g, '');
    return digits || '';
  };

  const toNumber = (value) => {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
  };

  const resolveCategory = (source = {}) => {
    const rawCategory = firstText(
      source.devotee_category,
      source.category,
      source.type,
      source.member_type,
      source.segment
    );
    const isVip = Boolean(source.is_vip) || String(source.vip || '').toLowerCase() === 'yes';
    if (rawCategory) return rawCategory;
    if (isVip) return 'VIP';
    return '';
  };

  const devoteeKey = (source = {}) => {
    const id = firstText(source.id, source.devotee_id, source._id);
    if (id) return `id:${id}`;
    const phone = normalizePhone(firstText(source.phone, source.mobile, source.devotee_phone));
    if (phone) return `phone:${phone}`;
    const email = firstText(source.email, source.devotee_email).toLowerCase();
    if (email) return `email:${email}`;
    const name = firstText(source.name, source.full_name, source.devotee_name, source.devotee_names).toLowerCase();
    if (name) return `name:${name}`;
    return '';
  };

  const fetchDevotees = async () => {
    try {
      setLoading(true);
      setError('');

      const [devoteesRes, donationsRes, sevasRes] = await Promise.allSettled([
        api.get('/api/v1/devotees'),
        api.get('/api/v1/donations?limit=2000'),
        api.get(`/api/v1/sevas/bookings?limit=${CONTRIBUTION_FETCH_LIMIT}`),
      ]);

      const devoteesList = devoteesRes.status === 'fulfilled' && devoteesRes.value && Array.isArray(devoteesRes.value.data)
        ? devoteesRes.value.data
        : [];
      const donationsList = donationsRes.status === 'fulfilled' && donationsRes.value && Array.isArray(donationsRes.value.data)
        ? donationsRes.value.data
        : [];
      const sevasList = sevasRes.status === 'fulfilled' && sevasRes.value && Array.isArray(sevasRes.value.data)
        ? sevasRes.value.data
        : [];

      const devoteeMap = new Map();
      const idMap = new Map(); // Map to track devotee IDs across different sources

      const ensureDevotee = (source = {}, overrides = {}) => {
        const key = devoteeKey({ ...source, ...overrides }) || `fallback:${devoteeMap.size + 1}`;

        // If this key doesn't exist, create a new devotee entry
        if (!devoteeMap.has(key)) {
          const devoteeId = firstText(source.id, source.devotee_id, source._id, overrides.id);
          const entry = {
            id: devoteeId || key,
            name_prefix: firstText(source.name_prefix, source.devotee_prefix, overrides.name_prefix),
            name: firstText(source.name, source.full_name, source.devotee_name, source.devotee_names, overrides.name, 'Unknown'),
            phone: normalizePhone(firstText(source.phone, source.mobile, source.devotee_phone, overrides.phone)),
            email: firstText(source.email, source.devotee_email, overrides.email) || null,
            address: firstText(source.address, source.devotee_address, overrides.address) || null,
            city: firstText(source.city, source.devotee_city, overrides.city) || null,
            state: firstText(source.state, source.devotee_state, overrides.state) || null,
            pincode: firstText(source.pincode, source.devotee_pincode, overrides.pincode) || null,
            category: firstText(resolveCategory(source), resolveCategory(overrides)) || null,
            is_vip: Boolean(source.is_vip || overrides.is_vip),
            donation_count: toNumber(source.donation_count ?? source.donations ?? 0),
            total_donations: toNumber(source.total_donations ?? source.total_donated ?? 0),
            booking_count: toNumber(source.booking_count ?? source.sevas ?? 0),
            total_seva_amount: toNumber(source.total_seva_amount ?? source.total_sevas ?? 0),
          };
          devoteeMap.set(key, entry);

          // Track ID mapping for better merging
          if (devoteeId) {
            idMap.set(String(devoteeId), key);
          }
        }
        return devoteeMap.get(key);
      };

      devoteesList.forEach((devotee) => {
        ensureDevotee(devotee);
      });

      donationsList.forEach((donation) => {
        const snapshot = donation.devotee && typeof donation.devotee === 'object' ? donation.devotee : {};
        const donationDevoteeId = firstText(snapshot.id, donation.devotee_id);

        const devotee = ensureDevotee({
          ...snapshot,
          id: donationDevoteeId,
          devotee_name: firstText(donation.devotee_name, snapshot.name),
          devotee_phone: firstText(donation.devotee_phone, snapshot.phone),
          devotee_email: firstText(donation.devotee_email, snapshot.email),
          devotee_address: firstText(donation.devotee_address, snapshot.address),
          devotee_city: firstText(donation.devotee_city, snapshot.city),
          devotee_state: firstText(donation.devotee_state, snapshot.state),
          devotee_pincode: firstText(donation.devotee_pincode, snapshot.pincode),
        });

        // Increment donation count (only once per donation, not per merge)
        if (!donation._counted) {
          devotee.donation_count = (devotee.donation_count || 0) + 1;
          donation._counted = true;
        }
        devotee.total_donations += toNumber(donation.amount);
        if (!devotee.category) {
          devotee.category = resolveCategory(donation) || devotee.category;
        }
      });

      sevasList.forEach((seva) => {
        const snapshot = seva.devotee && typeof seva.devotee === 'object' ? seva.devotee : {};
        const sevaDevoteeId = firstText(snapshot.id, seva.devotee_id);

        const devotee = ensureDevotee({
          ...snapshot,
          id: sevaDevoteeId,
          devotee_name: firstText(seva.devotee_name, seva.devotee_names, snapshot.name),
          devotee_phone: firstText(seva.devotee_phone, seva.phone, snapshot.phone),
          devotee_email: firstText(seva.devotee_email, snapshot.email),
          devotee_address: firstText(seva.devotee_address, seva.address, snapshot.address),
          devotee_city: firstText(seva.devotee_city, seva.city, snapshot.city),
          devotee_state: firstText(seva.devotee_state, seva.state, snapshot.state),
          devotee_pincode: firstText(seva.devotee_pincode, seva.pincode, snapshot.pincode),
        });

        // Increment booking count (only once per booking, not per merge)
        if (!seva._counted) {
          devotee.booking_count = (devotee.booking_count || 0) + 1;
          seva._counted = true;
        }
        devotee.total_seva_amount += toNumber(seva.amount_paid ?? seva.amount);
        if (!devotee.category) {
          devotee.category = resolveCategory(seva) || devotee.category;
        }
      });

      const mergedDevotees = Array.from(devoteeMap.values())
        .map((devotee) => ({
          ...devotee,
          phone: devotee.phone || null,
          address: devotee.address || [devotee.city, devotee.state, devotee.pincode].filter(Boolean).join(', ') || null,
        }))
        .sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));

      setDevotees(mergedDevotees);

      if (mergedDevotees.length === 0) {
        setError('No devotee records available from donations or sevas yet.');
      }
    } catch (err) {
      console.error('Error fetching devotees:', err);
      setError(`Failed to load devotees: ${err.response?.data?.detail || err.message || 'Unknown error'}.`);
      setDevotees([]);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const devoteeDisplayName = (devotee) => (
    `${devotee.name_prefix ? `${devotee.name_prefix} ` : ''}${devotee.name || devotee.full_name || 'N/A'}`.trim()
  );

  const devoteeDisplayId = (devotee, index) => {
    const rawId = firstText(devotee.id, devotee.devotee_id);
    if (rawId && !rawId.startsWith('phone:') && !rawId.startsWith('name:') && !rawId.startsWith('fallback:')) {
      return rawId;
    }
    return `DM${String(index + 1).padStart(4, '0')}`;
  };

  const devoteeLocation = (devotee) => (
    devotee.address || [devotee.city, devotee.state, devotee.pincode].filter(Boolean).join(', ') || ''
  );

  const totalDonationAmount = devotees.reduce(
    (sum, devotee) => sum + toNumber(devotee.total_donations ?? devotee.total_donated),
    0
  );
  const totalSevaAmount = devotees.reduce(
    (sum, devotee) => sum + toNumber(devotee.total_seva_amount),
    0
  );
  const activeDonors = devotees.filter((devotee) => (devotee.donation_count || 0) > 0).length;
  const activeSevaDevotees = devotees.filter((devotee) => (devotee.booking_count || 0) > 0).length;

  const filteredDevotees = devotees.filter((devotee) => {
    if (contributionFilter === 'all') return true;
    if (contributionFilter === 'donation') return (devotee.donation_count || 0) > 0;
    if (contributionFilter === 'seva') return (devotee.booking_count || 0) > 0;
    return true;
  }).filter((devotee) => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return true;
    return [
      devoteeDisplayName(devotee),
      devotee.phone,
      devotee.email,
      devoteeLocation(devotee),
      devotee.category,
    ].some((value) => String(value || '').toLowerCase().includes(query));
  });

  const reportRows = filteredDevotees.map((devotee, index) => ({
    name: devoteeDisplayName(devotee),
    devotee_id: devoteeDisplayId(devotee, index),
    phone: devotee.phone || 'N/A',
    email: devotee.email || 'N/A',
    address: devoteeLocation(devotee) || 'N/A',
    category: devotee.category || (devotee.is_vip ? 'VIP' : 'General'),
    donations: devotee.donation_count || 0,
    total_donated: formatCurrency(devotee.total_donations ?? devotee.total_donated ?? 0),
    sevas: devotee.booking_count || 0,
    total_seva: formatCurrency(devotee.total_seva_amount || 0),
  }));

  const reportColumns = [
    { field: 'name', label: 'Name' },
    { field: 'devotee_id', label: 'Devotee ID' },
    { field: 'phone', label: 'Phone' },
    { field: 'email', label: 'Email' },
    { field: 'address', label: 'Address' },
    { field: 'category', label: 'Category' },
    { field: 'donations', label: 'Donations' },
    { field: 'total_donated', label: 'Total Donated' },
    { field: 'sevas', label: 'Sevas' },
    { field: 'total_seva', label: 'Total Seva' },
  ];

  const handleExport = (format) => {
    if (!reportRows.length) return;
    const exportData = reportRows.map((row) => ({
      Name: row.name,
      'Devotee ID': row.devotee_id,
      Phone: row.phone,
      Email: row.email,
      Address: row.address,
      Category: row.category,
      Donations: row.donations,
      'Total Donated': row.total_donated,
      Sevas: row.sevas,
      'Total Seva': row.total_seva,
    }));

    if (format === 'csv') {
      exportToCSV(exportData, 'devotees-report');
    } else if (format === 'excel') {
      exportToExcel(exportData, 'Devotees Report');
    } else if (format === 'pdf') {
      exportToPDF(exportData, 'Devotees Report');
    }
  };

  return (
    <Layout>
      <Box sx={{ mb: 3 }}>
        <Paper
          sx={{
            p: { xs: 2, md: 3 },
            borderRadius: 2,
            background: 'linear-gradient(135deg, #fff8e8 0%, #ffffff 55%, #f2fbf8 100%)',
            border: '1px solid #f0dfbd',
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <Box>
              <Typography variant="overline" sx={{ color: '#B66A00', fontWeight: 800, letterSpacing: 0.6 }}>
                MANDIRMITRA DIRECTORY
              </Typography>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 800, color: '#17212b' }}>
                Devotee Directory
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Tenant-scoped donation and seva contact register
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                startIcon={<VolunteerActivismIcon />}
                onClick={() => navigate('/donations')}
                sx={{ borderColor: '#D97706', color: '#A65300' }}
              >
                Donations
              </Button>
              <Button
                variant="contained"
                startIcon={<TempleHinduIcon />}
                onClick={() => navigate('/sevas')}
                sx={{ bgcolor: '#C27612', '&:hover': { bgcolor: '#A8620D' } }}
              >
                Book Seva
              </Button>
            </Box>
          </Box>
        </Paper>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Total Devotees', value: devotees.length, icon: <PeopleIcon />, color: '#0F766E', bg: '#E6FFFA' },
          { label: 'Active Donors', value: activeDonors, icon: <VolunteerActivismIcon />, color: '#B45309', bg: '#FFF7ED' },
          { label: 'Seva Devotees', value: activeSevaDevotees, icon: <TempleHinduIcon />, color: '#6D28D9', bg: '#F3E8FF' },
          { label: 'Total Giving', value: formatCurrency(totalDonationAmount + totalSevaAmount), icon: <CurrencyRupeeIcon />, color: '#166534', bg: '#ECFDF5' },
        ].map((stat) => (
          <Grid item xs={12} sm={6} md={3} key={stat.label}>
            <Paper
              sx={{
                p: 2,
                height: '100%',
                borderRadius: 2,
                border: '1px solid #e8e1d5',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 700 }}>
                  {stat.label}
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 800, mt: 0.5 }}>
                  {stat.value}
                </Typography>
              </Box>
              <Box sx={{ bgcolor: stat.bg, color: stat.color, width: 44, height: 44, borderRadius: '50%', display: 'grid', placeItems: 'center' }}>
                {stat.icon}
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Paper id="devotees-report-content" sx={{ p: { xs: 2, md: 3 }, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', flex: 1 }}>
            <TextField
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, phone, email, city..."
              sx={{ minWidth: { xs: '100%', sm: 360 } }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            <FormControl size="small" sx={{ minWidth: 190 }}>
              <InputLabel>Contribution</InputLabel>
              <Select
                value={contributionFilter}
                label="Contribution"
                onChange={(e) => setContributionFilter(e.target.value)}
              >
                <MenuItem value="all">All Devotees</MenuItem>
                <MenuItem value="donation">Donors</MenuItem>
                <MenuItem value="seva">Seva Bookings</MenuItem>
              </Select>
            </FormControl>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button
              variant="outlined"
              startIcon={<PersonAddAltIcon />}
              onClick={() => navigate('/donations')}
              sx={{ borderColor: '#D97706', color: '#A65300' }}
            >
              Add Via Donation
            </Button>
            <ExportButton onExport={handleExport} />
            <PrintButton
              data={reportRows}
              columns={reportColumns}
              title="Devotees Report"
              reportContext={{
                period: contributionFilter === 'all' ? 'All Time' : (contributionFilter === 'donation' ? 'Donation Contributors' : 'Seva Contributors'),
              }}
            />
          </Box>
        </Box>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : filteredDevotees.length > 0 ? (
          <TableContainer sx={{ border: '1px solid #ece3d5', borderRadius: 2 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }}>Devotee</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }}>Contact</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }}>Address</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }}>History</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }}>Category</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }} align="right">Donations</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }} align="right">Sevas</TableCell>
                  <TableCell sx={{ bgcolor: '#FFF8E7', fontWeight: 800 }} align="center">Quick Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredDevotees.map((devotee, index) => (
                  <TableRow
                    key={devotee.id || devotee.phone}
                    hover
                    sx={{
                      '&:nth-of-type(odd)': { bgcolor: '#fffdf8' },
                      '&:hover': { bgcolor: '#fff4df !important' },
                    }}
                  >
                    <TableCell sx={{ minWidth: 220 }}>
                      <Typography variant="body1" sx={{ fontWeight: 800 }}>
                        {devoteeDisplayName(devotee)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ID: {devoteeDisplayId(devotee, index)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ minWidth: 250 }}>
                      <Box sx={{ display: 'grid', gap: 0.75 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                          <PhoneIcon fontSize="small" color="action" />
                          <Typography variant="body2">{devotee.phone || 'N/A'}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                          <EmailIcon fontSize="small" color="action" />
                          <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                            {devotee.email || 'N/A'}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ minWidth: 240 }}>
                      {devoteeLocation(devotee) ? (
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.75 }}>
                          <LocationOnIcon fontSize="small" color="action" sx={{ mt: 0.2 }} />
                          <Typography variant="body2">{devoteeLocation(devotee)}</Typography>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">N/A</Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ minWidth: 180 }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {(devotee.donation_count || 0) > 0 ? `Recent donor` : 'No donation yet'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {(devotee.booking_count || 0) > 0 ? `${devotee.booking_count} seva booking(s)` : 'No seva booking'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={devotee.category || (devotee.is_vip ? 'VIP' : 'General')}
                        size="small"
                        sx={{ bgcolor: devotee.is_vip ? '#7C2D12' : '#F3E8D0', color: devotee.is_vip ? '#fff' : '#6B3F00', fontWeight: 700 }}
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ minWidth: 130 }}>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        {formatCurrency(devotee.total_donations ?? devotee.total_donated ?? 0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {devotee.donation_count || 0} receipt(s)
                      </Typography>
                    </TableCell>
                    <TableCell align="right" sx={{ minWidth: 120 }}>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        {formatCurrency(devotee.total_seva_amount || 0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {devotee.booking_count || 0} booking(s)
                      </Typography>
                    </TableCell>
                    <TableCell align="center" sx={{ minWidth: 170 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Button size="small" variant="outlined" onClick={() => navigate('/donations')}>
                          Donate
                        </Button>
                        <Button size="small" variant="contained" onClick={() => navigate('/sevas')} sx={{ bgcolor: '#C27612', '&:hover': { bgcolor: '#A8620D' } }}>
                          Seva
                        </Button>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box sx={{ textAlign: 'center', p: 4 }}>
            <Typography variant="body1" color="text.secondary" gutterBottom>
              No devotees found for selected filter
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try changing filter or add donation/seva records.
            </Typography>
          </Box>
        )}
      </Paper>
    </Layout>
  );
}

export default Devotees;
