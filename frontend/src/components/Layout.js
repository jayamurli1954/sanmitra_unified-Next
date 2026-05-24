import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { fetchWithApiFallback } from '../utils/apiBaseUrl';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Button,
  Collapse,
  FormControl,
  MenuItem,
  Select,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import AssessmentIcon from '@mui/icons-material/Assessment';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import TempleHinduIcon from '@mui/icons-material/TempleHindu';
import LogoutIcon from '@mui/icons-material/Logout';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import ReceiptIcon from '@mui/icons-material/Receipt';
import PaymentIcon from '@mui/icons-material/Payment';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import SummarizeIcon from '@mui/icons-material/Summarize';
import MoneyOffIcon from '@mui/icons-material/MoneyOff';
import LockIcon from '@mui/icons-material/Lock';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import InventoryIcon from '@mui/icons-material/Inventory';
import EngineeringIcon from '@mui/icons-material/Engineering';
import BadgeIcon from '@mui/icons-material/Badge';
import SavingsIcon from '@mui/icons-material/Savings';
import AssignmentIcon from '@mui/icons-material/Assignment';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import { useCurrentUser } from '../contexts/CurrentUserContext';
import { clearAuthSession, getAccessToken, hasAccessToken } from '../utils/authStorage';
import { useTranslation } from 'react-i18next';
import AppInstallButton from './AppInstallButton';
import {
  ACTIVE_TEMPLE_EVENT,
  getActiveTempleId,
  setActiveTempleId,
  emitActiveTempleChanged,
} from '../utils/activeTemple';

const drawerWidth = 260;

const menuItems = [
  { id: 'dashboard', labelKey: 'layout.nav.dashboard', defaultLabel: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard', permissionKey: 'dashboard' },
  { id: 'donations', labelKey: 'layout.nav.donations', defaultLabel: 'Donations', icon: <AccountBalanceIcon />, path: '/donations', moduleFlag: 'module_donations_enabled', permissionKey: 'donations' },
  { id: 'devotees', labelKey: 'layout.nav.devotees', defaultLabel: 'Devotees', icon: <PeopleIcon />, path: '/devotees', permissionKey: 'devotees' },
  { id: 'publicPayments', labelKey: 'layout.nav.accounting.publicPayments', defaultLabel: 'Public Payments', icon: <AccountBalanceWalletIcon />, path: '/accounting/public-payments', permissionKey: 'accounting' },
  { id: 'inventory', labelKey: 'layout.nav.inventory', defaultLabel: 'Inventory', icon: <InventoryIcon />, path: '/inventory', moduleFlag: 'module_inventory_enabled', permissionKey: 'inventory' },
  { id: 'assets', labelKey: 'layout.nav.templeAssets', defaultLabel: 'Temple Assets', icon: <EngineeringIcon />, path: '/assets', moduleFlag: 'module_assets_enabled', permissionKey: 'assets' },
  { id: 'hr', labelKey: 'layout.nav.hrSalary', defaultLabel: 'HR & Salary', icon: <BadgeIcon />, path: '/hr', moduleFlag: 'module_hr_enabled', permissionKey: 'hr' },
  { id: 'hundi', labelKey: 'layout.nav.hundi', defaultLabel: 'Hundi', icon: <SavingsIcon />, path: '/hundi', moduleFlag: 'module_hundi_enabled', permissionKey: 'hundi' },
  { id: 'reports', labelKey: 'layout.nav.reports', defaultLabel: 'Reports', icon: <AssessmentIcon />, path: '/reports', moduleFlag: 'module_reports_enabled', permissionKey: 'reports' },
  { id: 'panchang', labelKey: 'layout.nav.panchang', defaultLabel: 'Panchang', icon: <CalendarTodayIcon />, path: '/panchang', moduleFlag: 'module_panchang_enabled', permissionKey: 'panchang' },
  { id: 'settings', labelKey: 'layout.nav.settings', defaultLabel: 'Settings', icon: <SettingsIcon />, path: '/settings', permissionKey: 'settings' },
  { id: 'implementationChecks', labelKey: 'layout.nav.implementationChecks', defaultLabel: 'Implementation Checks', icon: <FactCheckIcon />, path: '/implementation-checks', permissionKey: 'settings', superAdminOnly: true },
  { id: 'platformOperations', labelKey: 'layout.nav.platformOperations', defaultLabel: 'Platform Owners', icon: <TempleHinduIcon />, path: '/platform/operations', superAdminOnly: true },
];
const sevaMenuItems = [
  { id: 'bookSevas', labelKey: 'layout.nav.sevas.bookSevas', defaultLabel: 'Book Sevas', icon: <TempleHinduIcon />, path: '/sevas' },
  { id: 'sevaBookingsReschedule', labelKey: 'layout.nav.sevas.bookingsReschedule', defaultLabel: 'Seva Bookings / Reschedule', icon: <AssignmentIcon />, path: '/reports/sevas/detailed' },
  { id: 'sevaManagement', labelKey: 'layout.nav.sevas.management', defaultLabel: 'Seva Management', icon: <AssignmentIcon />, path: '/sevas/manage', requires: 'manage_seva_master' },
  { id: 'rescheduleApproval', labelKey: 'layout.nav.sevas.rescheduleApproval', defaultLabel: 'Reschedule Approval', icon: <AssignmentTurnedInIcon />, path: '/sevas/reschedule-approval', requires: 'approve_seva_reschedule' },
];
const accountingMenuItems = [
  { id: 'chartOfAccounts', labelKey: 'layout.nav.accounting.chartOfAccounts', defaultLabel: 'Chart of Accounts', icon: <AccountTreeIcon />, path: '/accounting/chart-of-accounts' },
  { id: 'quickExpense', labelKey: 'layout.nav.accounting.quickExpense', defaultLabel: 'Quick Expense', icon: <MoneyOffIcon />, path: '/accounting/quick-expense' },
  { id: 'journalEntries', labelKey: 'layout.nav.accounting.journalEntries', defaultLabel: 'Journal Entries', icon: <ReceiptIcon />, path: '/accounting/journal-entries' },
  { id: 'bankReconciliation', labelKey: 'layout.nav.accounting.bankReconciliation', defaultLabel: 'Bank Reconciliation', icon: <AccountBalanceIcon />, path: '/accounting/bank-reconciliation' },
  { id: 'financialClosing', labelKey: 'layout.nav.accounting.financialClosing', defaultLabel: 'Financial Closing', icon: <LockIcon />, path: '/accounting/financial-closing' },
  { id: 'upiPayments', labelKey: 'layout.nav.accounting.upiPayments', defaultLabel: 'UPI Payments', icon: <PaymentIcon />, path: '/accounting/upi-payments' },
  { id: 'sevaReminders', labelKey: 'layout.nav.accounting.sevaReminders', defaultLabel: 'Seva Reminders', icon: <NotificationsActiveIcon />, path: '/accounting/seva-reminders' },
  { id: 'accountingReports', labelKey: 'layout.nav.accounting.reports', defaultLabel: 'Accounting Reports', icon: <SummarizeIcon />, path: '/accounting/reports' },
];
const DEFAULT_MODULE_CONFIG = {
  module_donations_enabled: true,
  module_sevas_enabled: true,
  module_inventory_enabled: false,
  module_assets_enabled: false,
  module_hr_enabled: false,
  module_hundi_enabled: false,
  module_accounting_enabled: true,
  module_reports_enabled: true,
  module_panchang_enabled: true,
};

const PLATFORM_ADMIN_ROLES = new Set(['super_admin', 'superadmin', 'platform_owner', 'platform_admin']);

const LAYOUT_CACHE_TTL_MS = 2 * 60 * 1000;
const MODULE_CONFIG_CACHE_KEY = 'layout_module_config_cache_v1';
const LANGUAGE_OPTIONS = [
  { code: 'en', labelKey: 'layout.languageOptions.en', defaultLabel: 'English' },
  { code: 'kn', labelKey: 'layout.languageOptions.kn', defaultLabel: 'Kannada' },
  { code: 'hi', labelKey: 'layout.languageOptions.hi', defaultLabel: 'Hindi' },
];

const readLayoutCache = (key) => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      localStorage.removeItem(key);
      return null;
    }
    if (typeof parsed.expiresAt !== 'number' || Date.now() > parsed.expiresAt) {
      localStorage.removeItem(key);
      return null;
    }
    return parsed.value ?? null;
  } catch (err) {
    localStorage.removeItem(key);
    return null;
  }
};

const writeLayoutCache = (key, value, ttlMs = LAYOUT_CACHE_TTL_MS) => {
  try {
    localStorage.setItem(key, JSON.stringify({ value, expiresAt: Date.now() + ttlMs }));
  } catch (err) {
    // Ignore storage failures.
  }
};

function Layout({ children }) {
  const { t, i18n } = useTranslation();
  const { user, clearUser, loading: currentUserLoading } = useCurrentUser();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [accountingOpen, setAccountingOpen] = useState(true);
  const [sevasOpen, setSevasOpen] = useState(true);
  const [moduleConfig, setModuleConfig] = useState(DEFAULT_MODULE_CONFIG);
  const [temples, setTemples] = useState([]);
  const [hasPlatformOwnerAccess, setHasPlatformOwnerAccess] = useState(false);
  const [activeTempleId, setActiveTempleState] = useState(() => getActiveTempleId());
  const navigate = useNavigate();
  const location = useLocation();
  const userInfo = user || {};

  const systemRole = userInfo.system_role || userInfo.role;
  const modulePermissions = userInfo.module_permissions || {};
  const actionPermissions = userInfo.action_permissions || {};
  const hasResolvedCurrentUser = Boolean(userInfo.id || userInfo.email || userInfo.role || userInfo.system_role || userInfo.is_superuser);
  const isPlatformSuperAdmin = Boolean(userInfo.is_superuser) || PLATFORM_ADMIN_ROLES.has(String(systemRole || '').toLowerCase());
  const hasPlatformAccess = isPlatformSuperAdmin || hasPlatformOwnerAccess;

  const hasModuleAccess = (permissionKey) => {
    if ((currentUserLoading && hasAccessToken()) || (!hasResolvedCurrentUser && hasAccessToken())) {
      return false;
    }
    if (userInfo.is_superuser) {
      return true;
    }
    if (!permissionKey) {
      return true;
    }
    if (Object.prototype.hasOwnProperty.call(modulePermissions, permissionKey)) {
      return Boolean(modulePermissions[permissionKey]);
    }
    return true;
  };

  const hasActionAccess = (permissionKey) => {
    if ((currentUserLoading && hasAccessToken()) || (!hasResolvedCurrentUser && hasAccessToken())) {
      return false;
    }
    if (userInfo.is_superuser) {
      return true;
    }
    if (!permissionKey) {
      return true;
    }
    if (Object.prototype.hasOwnProperty.call(actionPermissions, permissionKey)) {
      return Boolean(actionPermissions[permissionKey]);
    }
    return false;
  };

  const isFeatureEnabled = (moduleFlag) => (!moduleFlag ? true : Boolean(moduleConfig[moduleFlag]));
  const isSevaManager = !currentUserLoading && (hasActionAccess('manage_seva_master') || ['admin', 'tenant_admin', 'temple_admin', 'super_admin', 'temple_manager'].includes(systemRole) || Boolean(userInfo.is_superuser));
  const canApproveReschedule = hasActionAccess('approve_seva_reschedule') || isSevaManager;

  const visibleSevaMenuItems = sevaMenuItems.filter((item) => {
    if (item.requires === 'manage_seva_master') {
      return isSevaManager;
    }
    if (item.requires === 'approve_seva_reschedule') {
      return canApproveReschedule;
    }
    return true;
  });

  const displayName = userInfo.full_name || userInfo.name || (userInfo.email ? userInfo.email.split('@')[0] : '') || t('common.user');

  useEffect(() => {
    const fetchTempleInfo = async () => {
      const cachedModuleConfig = readLayoutCache(MODULE_CONFIG_CACHE_KEY);
      if (cachedModuleConfig && typeof cachedModuleConfig === 'object') {
        setModuleConfig({ ...DEFAULT_MODULE_CONFIG, ...cachedModuleConfig });
      }

      try {
        const token = getAccessToken();
        if (!token) {
          return;
        }

        const response = await fetchWithApiFallback('/api/v1/temples/', {
          headers: { Authorization: `Bearer ${token}` },
        }, { timeoutMs: 12000 });
        if (!response.ok) {
          return;
        }

        const data = await response.json();
        const templeList = Array.isArray(data) ? data : (data ? [data] : []);
        setTemples(templeList);

        if (!templeList.length) {
          setModuleConfig(DEFAULT_MODULE_CONFIG);
          writeLayoutCache(MODULE_CONFIG_CACHE_KEY, DEFAULT_MODULE_CONFIG);
          return;
        }

        if (isPlatformSuperAdmin) {
          if (!activeTempleId) {
            const demoEditableTemples = templeList.filter((temple) => Boolean(temple?.platform_can_write));
            const selectableTemples = demoEditableTemples.length > 0 ? demoEditableTemples : templeList;
            const preferredTemple = selectableTemples[0];
            if (preferredTemple?.id) {
              const preferredTempleId = Number(preferredTemple.id);
              setActiveTempleId(preferredTempleId, preferredTemple?.tenant_id);
              setActiveTempleState(preferredTempleId);
              emitActiveTempleChanged(preferredTempleId, preferredTemple?.tenant_id);
              const normalizedPreferredTemple = { ...DEFAULT_MODULE_CONFIG, ...preferredTemple };
              setModuleConfig(normalizedPreferredTemple);
              writeLayoutCache(MODULE_CONFIG_CACHE_KEY, normalizedPreferredTemple);
              return;
            }

            setModuleConfig(DEFAULT_MODULE_CONFIG);
            writeLayoutCache(MODULE_CONFIG_CACHE_KEY, DEFAULT_MODULE_CONFIG);
            return;
          }

          const selectedTemple = templeList.find((temple) => Number(temple?.id) === Number(activeTempleId));
          if (!selectedTemple) {
            setActiveTempleId(null);
            setActiveTempleState(null);
            emitActiveTempleChanged(null);
            setModuleConfig(DEFAULT_MODULE_CONFIG);
            writeLayoutCache(MODULE_CONFIG_CACHE_KEY, DEFAULT_MODULE_CONFIG);
            return;
          }

          setActiveTempleId(activeTempleId, selectedTemple?.tenant_id);
          const normalizedSelectedTemple = { ...DEFAULT_MODULE_CONFIG, ...selectedTemple };
          setModuleConfig(normalizedSelectedTemple);
          writeLayoutCache(MODULE_CONFIG_CACHE_KEY, normalizedSelectedTemple);
          return;
        }

        const preferredTemple = templeList.find((temple) => temple.id === activeTempleId) || templeList[0];
        if (preferredTemple?.id && preferredTemple.id !== activeTempleId) {
          setActiveTempleId(preferredTemple.id, preferredTemple?.tenant_id);
          setActiveTempleState(preferredTemple.id);
        }
        const normalized = { ...DEFAULT_MODULE_CONFIG, ...(preferredTemple || {}) };
        setModuleConfig(normalized);
        writeLayoutCache(MODULE_CONFIG_CACHE_KEY, normalized);
      } catch (err) {
        console.error('Failed to fetch temple info', err);
      }
    };

    fetchTempleInfo();
  }, [activeTempleId, isPlatformSuperAdmin]);

  useEffect(() => {
    const verifyPlatformOwnerAccess = async () => {
      const token = getAccessToken();
      if (!token) {
        setHasPlatformOwnerAccess(false);
        return;
      }
      if (isPlatformSuperAdmin) {
        setHasPlatformOwnerAccess(true);
        return;
      }

      try {
        const response = await fetchWithApiFallback('/api/v1/platform-owner/dashboard?limit=1', {
          headers: { Authorization: `Bearer ${token}` },
        }, { timeoutMs: 8000, maxAttemptsPerOrigin: 1 });
        setHasPlatformOwnerAccess(response.ok);
      } catch (_error) {
        setHasPlatformOwnerAccess(false);
      }
    };

    verifyPlatformOwnerAccess();
  }, [isPlatformSuperAdmin, systemRole, userInfo.email]);

  useEffect(() => {
    const handleModuleConfigUpdated = (event) => {
      if (event?.detail && typeof event.detail === 'object') {
        setModuleConfig((prev) => {
          const merged = { ...prev, ...event.detail };
          writeLayoutCache(MODULE_CONFIG_CACHE_KEY, merged);
          return merged;
        });
      }
    };
    window.addEventListener('module-config-updated', handleModuleConfigUpdated);
    return () => window.removeEventListener('module-config-updated', handleModuleConfigUpdated);
  }, []);

  useEffect(() => {
    const handleActiveTempleChanged = (event) => {
      const nextTempleId = Number.parseInt(String(event?.detail?.templeId || ''), 10);
      if (Number.isInteger(nextTempleId) && nextTempleId > 0) {
        setActiveTempleState(nextTempleId);
        setActiveTempleId(nextTempleId, event?.detail?.tenantId);
      } else {
        setActiveTempleState(null);
        setActiveTempleId(null);
      }
    };
    window.addEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChanged);
    return () => window.removeEventListener(ACTIVE_TEMPLE_EVENT, handleActiveTempleChanged);
  }, []);

  const handleProfileClick = () => navigate('/profile');
  const handleDrawerToggle = () => setMobileOpen((prev) => !prev);
  const handleGoToDashboard = () => navigateTo('/dashboard');
  const handleLanguageChange = (event) => {
    const languageCode = String(event.target.value || 'en').trim();
    if (!languageCode) {
      return;
    }
    i18n.changeLanguage(languageCode);
  };

  const handleLogout = () => {
    clearAuthSession();
    localStorage.removeItem(MODULE_CONFIG_CACHE_KEY);
    setActiveTempleId(null);
    clearUser();
    window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { clear: true } }));
    navigate('/login');
  };

  const isPlatformConsole = hasPlatformAccess && !activeTempleId;
  const visibleMenuItems = menuItems.filter((item) => {
    if (item.superAdminOnly && !hasPlatformAccess) {
      return false;
    }
    if (item.superAdminOnly && hasPlatformAccess) {
      return true;
    }
    if (isPlatformConsole && item.id !== 'dashboard' && item.id !== 'platformOperations' && item.id !== 'implementationChecks') {
      return false;
    }
    return isFeatureEnabled(item.moduleFlag) && hasModuleAccess(item.permissionKey);
  });
  const showSevaSection = !isPlatformConsole && isFeatureEnabled('module_sevas_enabled') && hasModuleAccess('sevas');
  const showAccountingSection = !isPlatformConsole && isFeatureEnabled('module_accounting_enabled') && hasModuleAccess('accounting');

  const navigateTo = (path) => {
    const destination = path === '/dashboard' && hasPlatformAccess && !activeTempleId ? '/platform/operations' : path;
    navigate(destination);
    setMobileOpen(false);
  };

  const handleActiveTempleChange = (event) => {
    const rawValue = String(event.target.value || '').trim();
    if (!rawValue) {
      setActiveTempleState(null);
      setActiveTempleId(null);
      emitActiveTempleChanged(null);
      if (location.pathname === '/dashboard') {
        navigate('/platform/operations');
      }
      return;
    }

    const nextTempleId = Number.parseInt(rawValue, 10);
    if (!Number.isInteger(nextTempleId) || nextTempleId <= 0) {
      return;
    }

    setActiveTempleState(nextTempleId);
    const selected = visibleTemples.find((temple) => Number(temple.id) === Number(nextTempleId));
    setActiveTempleId(nextTempleId, selected?.tenant_id);
    emitActiveTempleChanged(nextTempleId, selected?.tenant_id);
  };

  const visibleTemples = useMemo(() => temples, [temples]);

  const selectedTemple = activeTempleId
    ? visibleTemples.find((temple) => Number(temple.id) === Number(activeTempleId))
    : null;
  const showTempleSwitcher = false;
  const currentTempleLabel = selectedTemple
    ? (selectedTemple.name || selectedTemple.trust_name || t('layout.defaultTenant'))
    : (isPlatformSuperAdmin ? t('layout.platformAdminConsole') : (moduleConfig?.name || moduleConfig?.trust_name || t('layout.defaultTenant')));

  const drawer = (
    <Box sx={{ height: '100%', overflowY: 'auto' }}>
      <Toolbar />
      <Divider />
      {showTempleSwitcher && (
        <>
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>
              {t('layout.activeTenant')}
            </Typography>
            <FormControl fullWidth size="small" sx={{ mt: 0.7 }}>
              <Select
                value={activeTempleId ? String(activeTempleId) : ''}
                onChange={handleActiveTempleChange}
                displayEmpty
                renderValue={(value) => {
                  if (!value) {
                    return t('layout.platformConsole');
                  }
                  const matchedTemple = visibleTemples.find((temple) => String(temple.id) === String(value));
                  return matchedTemple?.name || matchedTemple?.trust_name || `Temple ${value}`;
                }}
              >
                <MenuItem value="">{t('layout.platformConsole')}</MenuItem>
                {visibleTemples.map((temple) => (
                  <MenuItem key={temple.id} value={String(temple.id)}>
                    {temple.name || temple.trust_name || `Temple ${temple.id}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Divider />
        </>
      )}
      <List>
        {visibleMenuItems.filter((item) => item.id === 'dashboard').map((item) => {
          const isSelected = location.pathname === item.path || (!activeTempleId && isPlatformSuperAdmin && location.pathname === '/platform/operations');
          return (
            <ListItem key={item.id} disablePadding>
              <ListItemButton
                selected={isSelected}
                onClick={() => navigateTo(item.path)}
                sx={{ '&.Mui-selected': { bgcolor: '#FFF3E0', borderLeft: '4px solid #FF9933', '&:hover': { bgcolor: '#FFF3E0' } } }}
              >
                <ListItemIcon sx={{ color: isSelected ? '#FF9933' : 'inherit' }}>{item.icon}</ListItemIcon>
                <ListItemText primary={t(item.labelKey, { defaultValue: item.defaultLabel })} />
              </ListItemButton>
            </ListItem>
          );
        })}

        {showSevaSection && (
          <>
            <ListItem disablePadding>
              <ListItemButton onClick={() => setSevasOpen((prev) => !prev)}>
                <ListItemIcon><TempleHinduIcon /></ListItemIcon>
                <ListItemText primary={t('layout.nav.sevas.section', { defaultValue: 'Sevas' })} />
                {sevasOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
            </ListItem>
            <Collapse in={sevasOpen} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {visibleSevaMenuItems.map((item) => (
                  <ListItem key={item.id} disablePadding>
                    <ListItemButton
                      selected={location.pathname === item.path}
                      onClick={() => navigateTo(item.path)}
                      sx={{ pl: 4, '&.Mui-selected': { bgcolor: '#FFF3E0', borderLeft: '4px solid #FF9933', '&:hover': { bgcolor: '#FFF3E0' } } }}
                    >
                      <ListItemIcon sx={{ color: location.pathname === item.path ? '#FF9933' : 'inherit' }}>{item.icon}</ListItemIcon>
                      <ListItemText primary={t(item.labelKey, { defaultValue: item.defaultLabel })} />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Collapse>
            <Divider />
          </>
        )}

        {visibleMenuItems.filter((item) => item.id !== 'dashboard').map((item) => (
          <ListItem key={item.id} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => navigateTo(item.path)}
              sx={{ '&.Mui-selected': { bgcolor: '#FFF3E0', borderLeft: '4px solid #FF9933', '&:hover': { bgcolor: '#FFF3E0' } } }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? '#FF9933' : 'inherit' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={t(item.labelKey, { defaultValue: item.defaultLabel })} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      {showAccountingSection && (
        <>
          <List>
            <ListItem disablePadding>
              <ListItemButton onClick={() => setAccountingOpen((prev) => !prev)}>
                <ListItemIcon><AccountBalanceWalletIcon /></ListItemIcon>
                <ListItemText primary={t('layout.nav.accounting.section', { defaultValue: 'Accounting' })} />
                {accountingOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
            </ListItem>
            <Collapse in={accountingOpen} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {accountingMenuItems.map((item) => (
                  <ListItem key={item.id} disablePadding>
                    <ListItemButton
                      selected={location.pathname === item.path}
                      onClick={() => navigateTo(item.path)}
                      sx={{ pl: 4, '&.Mui-selected': { bgcolor: '#FFF3E0', borderLeft: '4px solid #FF9933', '&:hover': { bgcolor: '#FFF3E0' } } }}
                    >
                      <ListItemIcon sx={{ color: location.pathname === item.path ? '#FF9933' : 'inherit' }}>{item.icon}</ListItemIcon>
                      <ListItemText primary={t(item.labelKey, { defaultValue: item.defaultLabel })} />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </List>
          <Divider />
        </>
      )}
      {/* Version Footer */}
      <Box sx={{ mt: 'auto', pt: 2, px: 2, borderTop: '1px solid #eee' }}>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ textAlign: 'center', fontWeight: 500 }}>
          MandirMitra v1.2.0
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ textAlign: 'center', fontSize: '0.7rem' }}>
          Stable Release Â· April 2026
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ width: '100%', ml: 0, bgcolor: '#FF9933', zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.2, sm: 1 }, px: { xs: 1, sm: 2 }, minHeight: { xs: 56, sm: 72 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.4, sm: 1 }, width: { xs: 'auto', sm: drawerWidth }, minWidth: 0, pr: { xs: 0.4, sm: 1 }, flexShrink: 0 }}>
            <IconButton color="inherit" aria-label="open drawer" edge="start" onClick={handleDrawerToggle} sx={{ mr: 0.5, display: { sm: 'none' } }}>
              <MenuIcon />
            </IconButton>
            <Box component="img" src="/branding/mandirmitra_logo1.jpg" alt="MandirMitra Logo" sx={{ height: { xs: 30, sm: 52 }, width: '100%', maxWidth: { xs: 34, sm: 230 }, objectFit: 'contain' }} />
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1, minWidth: 0, pl: { xs: 0, sm: 1 }, overflow: 'hidden' }}>
            <Box sx={{ minWidth: 0, overflow: 'hidden' }}>
              <Typography variant="body2" sx={{ fontWeight: 700, color: '#fff', fontSize: { xs: '0.78rem', sm: '1rem' }, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', lineHeight: 1.1 }}>
                {currentTempleLabel}
              </Typography>
              <Typography variant="caption" sx={{ display: { xs: 'none', md: 'block' }, color: 'rgba(255,255,255,0.95)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedTemple ? t('layout.templeSubtitle') : t('layout.platformSubtitle')}
              </Typography>
              {showTempleSwitcher && (
                <FormControl variant="standard" size="small" sx={{ display: { xs: 'none', md: 'block' }, mt: 0.5, minWidth: { sm: 220, md: 260 }, '& .MuiInputBase-root': { color: '#fff', fontSize: 14, fontWeight: 600 }, '& .MuiSvgIcon-root': { color: '#fff' }, '& .MuiInput-underline:before': { borderBottomColor: 'rgba(255,255,255,0.55)' }, '& .MuiInput-underline:hover:not(.Mui-disabled):before': { borderBottomColor: '#fff' }, '& .MuiInput-underline:after': { borderBottomColor: '#fff' } }}>
                  <Select
                    value={activeTempleId ? String(activeTempleId) : ''}
                    onChange={handleActiveTempleChange}
                    disableUnderline
                    displayEmpty
                    renderValue={(value) => {
                      if (!value) {
                        return t('layout.platformConsole');
                      }
                      const matchedTemple = visibleTemples.find((temple) => String(temple.id) === String(value));
                      return matchedTemple?.name || matchedTemple?.trust_name || `Temple ${value}`;
                    }}
                  >
                    <MenuItem value="">{t('layout.platformConsole')}</MenuItem>
                    {visibleTemples.map((temple) => (
                      <MenuItem key={temple.id} value={String(temple.id)}>
                        {temple.name || temple.trust_name || `Temple ${temple.id}`}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.2, sm: 0.8 }, ml: 'auto', flexShrink: 0 }}>
            <FormControl
              size="small"
              sx={{
                minWidth: { xs: 72, sm: 96 },
                mr: { xs: 0.2, sm: 0.4 },
                '& .MuiOutlinedInput-root': {
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: { xs: 12, sm: 13 },
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.7)' },
                  '&:hover fieldset': { borderColor: '#fff' },
                  '&.Mui-focused fieldset': { borderColor: '#fff' },
                },
                '& .MuiSvgIcon-root': { color: '#fff' },
              }}
            >
              <Select
                value={i18n.resolvedLanguage || i18n.language || 'en'}
                onChange={handleLanguageChange}
                size="small"
                displayEmpty
                inputProps={{ 'aria-label': t('layout.language') }}
              >
                {LANGUAGE_OPTIONS.map((language) => (
                  <MenuItem key={language.code} value={language.code}>
                    {t(language.labelKey, { defaultValue: language.defaultLabel })}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <IconButton
              color="inherit"
              onClick={handleGoToDashboard}
              size="small"
              aria-label="dashboard"
              sx={{ display: { xs: 'inline-flex', sm: 'none' } }}
            >
              <DashboardIcon fontSize="small" />
            </IconButton>
            <AppInstallButton />
            <Button
              color="inherit"
              startIcon={<DashboardIcon />}
              onClick={handleGoToDashboard}
              sx={{ display: { xs: 'none', sm: 'inline-flex' }, textTransform: 'none', fontWeight: 700, minWidth: 0, px: { sm: 1.2 } }}
            >
              {t('layout.dashboard')}
            </Button>
            <Button color="inherit" onClick={handleProfileClick} sx={{ display: { xs: 'none', md: 'inline-flex' }, textTransform: 'none', fontWeight: 700, minWidth: 0, px: { md: 1.2 } }}>
              {displayName}
            </Button>
            <IconButton color="inherit" onClick={handleProfileClick} size="small" aria-label="profile">
              <Avatar sx={{ width: 32, height: 32, bgcolor: '#138808' }}>{displayName?.[0]?.toUpperCase() || 'U'}</Avatar>
            </IconButton>
            <IconButton
              color="inherit"
              onClick={handleLogout}
              size="small"
              aria-label="logout"
              sx={{ display: { xs: 'inline-flex', sm: 'none' } }}
            >
              <LogoutIcon fontSize="small" />
            </IconButton>
            <Button color="inherit" startIcon={<LogoutIcon />} onClick={handleLogout} sx={{ display: { xs: 'none', sm: 'inline-flex' }, textTransform: 'none', fontWeight: 700, px: { sm: 1.2 } }}>
              {t('layout.logout')}
            </Button>
          </Box>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer variant="temporary" open={mobileOpen} onClose={handleDrawerToggle} ModalProps={{ keepMounted: true }} sx={{ display: { xs: 'block', sm: 'none' }, '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }}>
          {drawer}
        </Drawer>
        <Drawer variant="permanent" sx={{ display: { xs: 'none', sm: 'block' }, '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth } }} open>
          {drawer}
        </Drawer>
      </Box>
      <Box component="main" sx={{ flexGrow: 1, p: { xs: 1.5, sm: 3 }, width: { sm: `calc(100% - ${drawerWidth}px)` }, bgcolor: '#f5f5f5', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Toolbar />
        <Box sx={{ flex: 1 }}>
          {children}
        </Box>
        {/* Footer */}
        <Box sx={{ mt: 4, pt: 2, borderTop: '1px solid #ddd', textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            Powered by Sanmitra Tech Â· {' '}
            <Button
              size="small"
              onClick={() => navigate('/settings/release-notes')}
              sx={{
                p: 0,
                textTransform: 'none',
                color: '#FF9933',
                fontSize: '0.75rem',
                '&:hover': { textDecoration: 'underline' }
              }}
            >
              Release Notes & Version History
            </Button>
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}

export default Layout;



