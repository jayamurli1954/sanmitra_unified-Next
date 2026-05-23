import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, Button, Switch, FormControlLabel, TextField,
  Dialog, DialogTitle, DialogContent, DialogActions, Alert, Snackbar,
  Tabs, Tab, Tooltip, CircularProgress, IconButton, Badge,
} from '@mui/material';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EmailIcon from '@mui/icons-material/Email';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import SettingsIcon from '@mui/icons-material/Settings';
import SendIcon from '@mui/icons-material/Send';
import RefreshIcon from '@mui/icons-material/Refresh';
import Layout from '../components/Layout';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ pt: 3 }}>{children}</Box> : null;
}

function DaysChip({ days }) {
  if (days === 0) return <Chip label="Expires today" color="error" size="small" />;
  if (days <= 7) return <Chip label={`${days}d left`} color="error" size="small" />;
  if (days <= 14) return <Chip label={`${days}d left`} color="warning" size="small" />;
  return <Chip label={`${days}d left`} color="success" size="small" />;
}

export default function SevaReminders() {
  const [tab, setTab] = useState(0);

  // --- Reminder Config tab ---
  const [sevas, setSevas] = useState([]);
  const [sevasLoading, setSevasLoading] = useState(false);
  const [editSeva, setEditSeva] = useState(null); // seva being edited
  const [editDialog, setEditDialog] = useState(false);
  const [editForm, setEditForm] = useState({ reminder_enabled: false, reminder_days_before: 30, duration_days: 365 });
  const [saving, setSaving] = useState(false);

  // --- Upcoming Renewals tab ---
  const [upcoming, setUpcoming] = useState([]);
  const [upcomingLoading, setUpcomingLoading] = useState(false);
  const [daysFilter, setDaysFilter] = useState(30);

  // --- Trigger ---
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);

  // --- Snackbar ---
  const [snack, setSnack] = useState({ open: false, msg: '', severity: 'success' });
  const showSnack = (msg, severity = 'success') => setSnack({ open: true, msg, severity });

  // --- Load seva reminder configs ---
  const loadSevas = useCallback(async () => {
    setSevasLoading(true);
    try {
      const res = await fetchWithApiFallback('/api/v1/sevas/reminder-config');
      if (res.ok) setSevas(await res.json());
      else showSnack('Failed to load seva configuration', 'error');
    } catch (_e) { /* best-effort */ }
    setSevasLoading(false);
  }, []);

  // --- Load upcoming renewals ---
  const loadUpcoming = useCallback(async () => {
    setUpcomingLoading(true);
    try {
      const res = await fetchWithApiFallback(`/api/v1/sevas/reminders/upcoming?days=${daysFilter}`);
      if (res.ok) setUpcoming(await res.json());
      else showSnack('Failed to load upcoming renewals', 'error');
    } catch (_e) { /* best-effort */ }
    setUpcomingLoading(false);
  }, [daysFilter]);

  useEffect(() => { loadSevas(); }, [loadSevas]);
  useEffect(() => { if (tab === 1) loadUpcoming(); }, [tab, loadUpcoming]);

  // --- Edit seva reminder config ---
  const openEdit = (seva) => {
    setEditSeva(seva);
    setEditForm({
      reminder_enabled: seva.reminder_enabled,
      reminder_days_before: seva.reminder_days_before || 30,
      duration_days: seva.duration_days || 365,
    });
    setEditDialog(true);
  };

  const saveEdit = async () => {
    if (!editSeva) return;
    setSaving(true);
    try {
      const res = await fetchWithApiFallback(`/api/v1/sevas/${editSeva.seva_id}/reminder-config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reminder_enabled: editForm.reminder_enabled,
          reminder_days_before: Number(editForm.reminder_days_before),
          duration_days: Number(editForm.duration_days),
        }),
      });
      if (res.ok) {
        showSnack('Reminder configuration saved');
        setEditDialog(false);
        loadSevas();
      } else {
        const err = await res.json().catch(() => ({}));
        showSnack(err.detail || 'Failed to save', 'error');
      }
    } catch (_e) { /* best-effort */ }
    setSaving(false);
  };

  // --- Trigger email reminders ---
  const triggerReminders = async (sevaId = null, force = false) => {
    setTriggerLoading(true);
    setTriggerResult(null);
    try {
      const res = await fetchWithApiFallback('/api/v1/sevas/reminders/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...(sevaId ? { seva_id: sevaId } : {}), force }),
      });
      if (res.ok) {
        const data = await res.json();
        setTriggerResult(data.result);
        showSnack(`Done! Scanned ${data.result.scanned}, sent ${data.result.sent} emails`);
        loadUpcoming();
      } else {
        showSnack('Failed to trigger reminders', 'error');
      }
    } catch (_e) { /* best-effort */ }
    setTriggerLoading(false);
  };

  return (
    <Layout>
      <Box sx={{ p: 3, maxWidth: 1100, mx: 'auto' }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <NotificationsActiveIcon sx={{ color: '#FF9933', fontSize: 36 }} />
          <Box>
            <Typography variant="h5" fontWeight="bold">Seva Renewal Reminders</Typography>
            <Typography variant="body2" color="text.secondary">
              Configure which sevas get renewal reminders — send via Email (auto) or WhatsApp (manual one-click)
            </Typography>
          </Box>
        </Box>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 1 }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)}>
            <Tab icon={<SettingsIcon />} label="Reminder Config" iconPosition="start" />
            <Tab
              icon={
                <Badge badgeContent={upcoming.length || null} color="error">
                  <NotificationsActiveIcon />
                </Badge>
              }
              label="Upcoming Renewals"
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* TAB 0 — Reminder Config */}
        <TabPanel value={tab} index={0}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2, gap: 1 }}>
            <Button startIcon={<RefreshIcon />} onClick={loadSevas} disabled={sevasLoading}>
              Refresh
            </Button>
          </Box>

          {sevasLoading ? (
            <Box sx={{ textAlign: 'center', py: 6 }}><CircularProgress /></Box>
          ) : (
            <TableContainer component={Paper} elevation={2}>
              <Table size="small">
                <TableHead sx={{ bgcolor: '#FFF3E0' }}>
                  <TableRow>
                    <TableCell><strong>Seva Name</strong></TableCell>
                    <TableCell align="right"><strong>Amount (Rs.)</strong></TableCell>
                    <TableCell align="center"><strong>Duration (days)</strong></TableCell>
                    <TableCell align="center"><strong>Reminder Enabled</strong></TableCell>
                    <TableCell align="center"><strong>Remind Before</strong></TableCell>
                    <TableCell align="center"><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sevas.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                        No sevas found. Add sevas from Seva Management first.
                      </TableCell>
                    </TableRow>
                  ) : sevas.map((seva) => (
                    <TableRow key={seva.seva_id} hover>
                      <TableCell>{seva.seva_name}</TableCell>
                      <TableCell align="right">
                        {seva.amount?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </TableCell>
                      <TableCell align="center">
                        {seva.duration_days
                          ? <Chip label={`${seva.duration_days}d`} size="small" color="info" />
                          : <Chip label="Not set" size="small" variant="outlined" />}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={seva.reminder_enabled ? 'ON' : 'OFF'}
                          color={seva.reminder_enabled ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        {seva.reminder_enabled
                          ? <Chip label={`${seva.reminder_days_before} days before`} size="small" variant="outlined" />
                          : '—'}
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="Configure reminder settings">
                          <IconButton size="small" onClick={() => openEdit(seva)} color="primary">
                            <SettingsIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {seva.reminder_enabled && (
                          <Tooltip title="Trigger email reminders now for this seva">
                            <IconButton
                              size="small"
                              color="warning"
                              onClick={() => triggerReminders(seva.seva_id, false)}
                              disabled={triggerLoading}
                            >
                              <SendIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          <Alert severity="info" sx={{ mt: 3 }}>
            <strong>How it works:</strong> Once enabled, the system automatically sends email reminders to
            devotees whose seva subscription expires within the configured number of days. For WhatsApp
            reminders, switch to the <em>Upcoming Renewals</em> tab and click the WhatsApp button next to
            each devotee.
          </Alert>

          {triggerResult && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Trigger result — Scanned: <strong>{triggerResult.scanned}</strong> |
              Sent: <strong>{triggerResult.sent}</strong> |
              Email OK: <strong>{triggerResult.email_ok}</strong> |
              Skipped (already reminded): <strong>{triggerResult.skipped}</strong>
            </Alert>
          )}
        </TabPanel>

        {/* TAB 1 — Upcoming Renewals */}
        <TabPanel value={tab} index={1}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
            <TextField
              label="Show renewals within (days)"
              type="number"
              size="small"
              value={daysFilter}
              onChange={(e) => setDaysFilter(Number(e.target.value))}
              inputProps={{ min: 1, max: 365 }}
              sx={{ width: 220 }}
            />
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadUpcoming} disabled={upcomingLoading}>
              Refresh
            </Button>
            <Box sx={{ flex: 1 }} />
            <Tooltip title="Send email reminders to all eligible devotees in the list">
              <Button
                variant="contained"
                color="warning"
                startIcon={<EmailIcon />}
                onClick={() => triggerReminders(null, false)}
                disabled={triggerLoading || upcoming.length === 0}
              >
                {triggerLoading ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
                Send Email Reminders
              </Button>
            </Tooltip>
            <Tooltip title="Force re-send even if already reminded recently">
              <Button
                variant="outlined"
                color="error"
                startIcon={<SendIcon />}
                onClick={() => triggerReminders(null, true)}
                disabled={triggerLoading || upcoming.length === 0}
              >
                Force Send
              </Button>
            </Tooltip>
          </Box>

          {upcomingLoading ? (
            <Box sx={{ textAlign: 'center', py: 6 }}><CircularProgress /></Box>
          ) : (
            <TableContainer component={Paper} elevation={2}>
              <Table size="small">
                <TableHead sx={{ bgcolor: '#FFF3E0' }}>
                  <TableRow>
                    <TableCell><strong>Devotee</strong></TableCell>
                    <TableCell><strong>Seva</strong></TableCell>
                    <TableCell><strong>Phone</strong></TableCell>
                    <TableCell align="right"><strong>Amount (Rs.)</strong></TableCell>
                    <TableCell align="center"><strong>Expiry Date</strong></TableCell>
                    <TableCell align="center"><strong>Days Left</strong></TableCell>
                    <TableCell align="center"><strong>Reminders Sent</strong></TableCell>
                    <TableCell align="center"><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {upcoming.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                        No renewals due within {daysFilter} days.
                        <br />
                        <Typography variant="caption">
                          Make sure sevas have <em>duration_days</em> set and reminder is enabled.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : upcoming.map((r) => (
                    <TableRow
                      key={r.booking_id}
                      hover
                      sx={{ bgcolor: r.days_left <= 7 ? '#fff8f0' : 'inherit' }}
                    >
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">{r.devotee_name}</Typography>
                        {r.devotee_email && (
                          <Typography variant="caption" color="text.secondary">{r.devotee_email}</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{r.seva_name}</Typography>
                        <Typography variant="caption" color="text.secondary">{r.receipt_number}</Typography>
                      </TableCell>
                      <TableCell>{r.devotee_phone || '—'}</TableCell>
                      <TableCell align="right">
                        {r.amount?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" color={r.days_left <= 7 ? 'error.main' : 'text.primary'}>
                          {r.expiry_date_label}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <DaysChip days={r.days_left} />
                      </TableCell>
                      <TableCell align="center">
                        {r.reminder_count > 0 ? (
                          <Chip label={`${r.reminder_count} sent`} size="small" color="success" variant="outlined" />
                        ) : (
                          <Chip label="Not sent" size="small" variant="outlined" />
                        )}
                      </TableCell>
                      <TableCell align="center">
                        {r.whatsapp_link ? (
                          <Tooltip title={`Send WhatsApp reminder to ${r.devotee_name}`}>
                            <IconButton
                              size="small"
                              component="a"
                              href={r.whatsapp_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              sx={{ color: '#25D366' }}
                            >
                              <WhatsAppIcon />
                            </IconButton>
                          </Tooltip>
                        ) : (
                          <Tooltip title="No phone number available">
                            <span>
                              <IconButton size="small" disabled>
                                <WhatsAppIcon />
                              </IconButton>
                            </span>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {triggerResult && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Email reminder result — Scanned: <strong>{triggerResult.scanned}</strong> |
              Sent: <strong>{triggerResult.sent}</strong> |
              Skipped: <strong>{triggerResult.skipped}</strong>
            </Alert>
          )}

          <Alert severity="info" sx={{ mt: 3 }}>
            <strong>WhatsApp (manual):</strong> Click the <WhatsAppIcon sx={{ fontSize: 16, verticalAlign: 'middle', color: '#25D366' }} /> button
            to open WhatsApp with a pre-filled renewal reminder message to the devotee. The message will open
            in WhatsApp Web or the WhatsApp app on your phone.
            <br />
            <strong>Email (automatic):</strong> Click <em>Send Email Reminders</em> to immediately trigger
            emails to all devotees in this list who have an email address on record. The system also runs
            this automatically every hour.
          </Alert>
        </TabPanel>
      </Box>

      {/* Edit Dialog */}
      <Dialog open={editDialog} onClose={() => setEditDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>
          <SettingsIcon sx={{ mr: 1, verticalAlign: 'middle', color: '#FF9933' }} />
          Reminder Config — {editSeva?.seva_name}
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={editForm.reminder_enabled}
                  onChange={(e) => setEditForm((f) => ({ ...f, reminder_enabled: e.target.checked }))}
                  color="success"
                />
              }
              label={editForm.reminder_enabled ? 'Reminder Enabled' : 'Reminder Disabled'}
            />
            <TextField
              label="Duration (days) — e.g. 365 for annual"
              type="number"
              size="small"
              value={editForm.duration_days}
              onChange={(e) => setEditForm((f) => ({ ...f, duration_days: e.target.value }))}
              helperText="How long this seva subscription is valid. Used to compute expiry date on new bookings."
              inputProps={{ min: 1, max: 3650 }}
              disabled={!editForm.reminder_enabled}
            />
            <TextField
              label="Remind how many days before expiry?"
              type="number"
              size="small"
              value={editForm.reminder_days_before}
              onChange={(e) => setEditForm((f) => ({ ...f, reminder_days_before: e.target.value }))}
              helperText="Reminder will be sent when expiry is within this many days (default: 30)"
              inputProps={{ min: 1, max: 365 }}
              disabled={!editForm.reminder_enabled}
            />
            <Alert severity="info" sx={{ fontSize: 12 }}>
              Changes apply to <strong>new bookings</strong> for duration_days.
              Existing bookings already have their expiry date set.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog(false)}>Cancel</Button>
          <Button
            onClick={saveEdit}
            variant="contained"
            disabled={saving}
            sx={{ bgcolor: '#FF9933', '&:hover': { bgcolor: '#e65c00' } }}
          >
            {saving ? <CircularProgress size={20} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snack.open}
        autoHideDuration={5000}
        onClose={() => setSnack((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} onClose={() => setSnack((s) => ({ ...s, open: false }))}>
          {snack.msg}
        </Alert>
      </Snackbar>
    </Layout>
  );
}
