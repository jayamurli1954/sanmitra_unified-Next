import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import PhoneIcon from '@mui/icons-material/Phone';
import EmailIcon from '@mui/icons-material/Email';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import Layout from '../components/Layout';
import api from '../services/api';
import ExportButton from '../components/ExportButton';
import PrintButton from '../components/PrintButton';
import { exportToCSV, exportToExcel, exportToPDF } from '../utils/export';

const CONTRIBUTION_FETCH_LIMIT = 500;

function Devotees() {
  const [devotees, setDevotees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [contributionFilter, setContributionFilter] = useState('all');

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

  const filteredDevotees = devotees.filter((devotee) => {
    if (contributionFilter === 'all') return true;
    if (contributionFilter === 'donation') return (devotee.donation_count || 0) > 0;
    if (contributionFilter === 'seva') return (devotee.booking_count || 0) > 0;
    return true;
  });

  const handleExport = (format) => {
    if (!filteredDevotees.length) return;
    const exportData = filteredDevotees.map((devotee) => ({
      Name: `${devotee.name_prefix ? `${devotee.name_prefix} ` : ''}${devotee.name || devotee.full_name || 'N/A'}`.trim(),
      Phone: devotee.phone || 'N/A',
      Email: devotee.email || 'N/A',
      Address: devotee.address || 'N/A',
      Category: devotee.category || (devotee.is_vip ? 'VIP' : 'General'),
      Donations: devotee.donation_count || 0,
      'Total Donated': devotee.total_donations ?? devotee.total_donated ?? 0,
      Sevas: devotee.booking_count || 0,
      'Total Seva': devotee.total_seva_amount || 0,
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
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Devotees
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Devotees are automatically created when donations are recorded. This list includes both donation and seva contribution totals.
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Paper id="devotees-report-content" sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 2, flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel>Filter Category</InputLabel>
            <Select
              value={contributionFilter}
              label="Filter Category"
              onChange={(e) => setContributionFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="donation">Donation</MenuItem>
              <MenuItem value="seva">Seva</MenuItem>
            </Select>
          </FormControl>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <ExportButton onExport={handleExport} />
            <PrintButton
              elementId="devotees-report-content"
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
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Phone</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Address</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell align="right">Donations</TableCell>
                  <TableCell align="right">Total Donated</TableCell>
                  <TableCell align="right">Sevas</TableCell>
                  <TableCell align="right">Total Seva</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredDevotees.map((devotee) => (
                  <TableRow key={devotee.id || devotee.phone}>
                    <TableCell>
                      <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                        {devotee.name_prefix ? `${devotee.name_prefix} ` : ''}{devotee.name || devotee.full_name || 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <PhoneIcon fontSize="small" color="action" />
                        {devotee.phone || 'N/A'}
                      </Box>
                    </TableCell>
                    <TableCell>
                      {devotee.email ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <EmailIcon fontSize="small" color="action" />
                          {devotee.email}
                        </Box>
                      ) : (
                        'N/A'
                      )}
                    </TableCell>
                    <TableCell>
                      {devotee.address ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <LocationOnIcon fontSize="small" color="action" />
                          {devotee.address}
                        </Box>
                      ) : (
                        'N/A'
                      )}
                    </TableCell>
                    <TableCell>{devotee.category || (devotee.is_vip ? 'VIP' : 'General')}</TableCell>
                    <TableCell align="right">{devotee.donation_count || 0}</TableCell>
                    <TableCell align="right">
                      {formatCurrency(devotee.total_donations ?? devotee.total_donated ?? 0)}
                    </TableCell>
                    <TableCell align="right">{devotee.booking_count || 0}</TableCell>
                    <TableCell align="right">
                      {formatCurrency(devotee.total_seva_amount || 0)}
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
