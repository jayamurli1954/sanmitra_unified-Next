import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  Switch,
  Typography,
  Chip,
} from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';

function RolePermissionMatrix({ currentUser }) {
  const { showSuccess, showError } = useNotification();
  const [loading, setLoading] = useState(true);
  const [savingRoleKey, setSavingRoleKey] = useState('');
  const [config, setConfig] = useState({ modules: [], actions: [], roles: [], policy_notice: '' });

  const canManageMatrix = ['admin', 'super_admin', 'temple_manager'].includes(currentUser.role) || Boolean(currentUser.is_superuser);

  useEffect(() => {
    if (!canManageMatrix) {
      setLoading(false);
      return;
    }

    const fetchConfig = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/v1/role-permissions');
        setConfig(response.data || { modules: [], actions: [], roles: [], policy_notice: '' });
      } catch (error) {
        showError(error?.response?.data?.detail || 'Failed to load role permissions');
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, [canManageMatrix, showError]);

  if (!canManageMatrix) {
    return null;
  }

  const handleRoleFieldChange = (roleKey, field, value) => {
    setConfig((prev) => ({
      ...prev,
      roles: prev.roles.map((role) => {
        if (role.role_key !== roleKey) {
          return role;
        }
        return { ...role, [field]: value };
      }),
    }));
  };

  const handlePermissionChange = (roleKey, section, permissionKey, checked) => {
    setConfig((prev) => ({
      ...prev,
      roles: prev.roles.map((role) => {
        if (role.role_key !== roleKey) {
          return role;
        }
        return {
          ...role,
          [section]: {
            ...(role[section] || {}),
            [permissionKey]: checked,
          },
        };
      }),
    }));
  };

  const handleSaveRole = async (role) => {
    try {
      setSavingRoleKey(role.role_key);
      const response = await api.put(`/api/v1/role-permissions/${role.role_key}`, {
        is_enabled: Boolean(role.is_enabled),
        module_permissions: role.module_permissions || {},
        action_permissions: role.action_permissions || {},
      });
      const updatedRole = response.data?.role;
      setConfig((prev) => ({
        ...prev,
        roles: prev.roles.map((item) => (item.role_key === role.role_key ? updatedRole : item)),
      }));
      showSuccess(`${role.display_name} permissions saved`);
    } catch (error) {
      showError(error?.response?.data?.detail || 'Failed to save role permissions');
    } finally {
      setSavingRoleKey('');
    }
  };

  return (
    <Grid item xs={12}>
      <Card sx={{ borderLeft: '5px solid #1565C0' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <SecurityIcon color="primary" />
            <Typography variant="h6" color="primary">
              Configurable Role Permission Matrix
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            These are business-role templates for President, Secretary, Treasurer, Counter Clerk, Accounts Clerk, and an optional Priest / Temple Operator fallback. Each role remains mapped to the current legacy system roles underneath so existing workflows continue to run.
          </Typography>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <Alert severity="warning" sx={{ mb: 3 }}>
                {config.policy_notice || 'Accounting transactions should never be deleted or cancelled in-place. Use reversal with reason and approval to preserve a proper audit trail.'}
              </Alert>
              <Grid container spacing={3}>
                {(config.roles || []).map((role) => (
                  <Grid item xs={12} key={role.role_key}>
                    <Card variant="outlined" sx={{ bgcolor: role.is_enabled ? '#fff' : '#fafafa' }}>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', mb: 2 }}>
                          <Box>
                            <Typography variant="h6" sx={{ fontWeight: 700 }}>
                              {role.display_name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {role.description}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                              <Chip size="small" label={`System Role: ${role.mapped_system_role}`} color="secondary" variant="outlined" />
                              <Chip size="small" label={role.is_enabled ? 'Enabled' : 'Disabled'} color={role.is_enabled ? 'success' : 'default'} variant="outlined" />
                            </Box>
                          </Box>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={Boolean(role.is_enabled)}
                                onChange={(e) => handleRoleFieldChange(role.role_key, 'is_enabled', e.target.checked)}
                              />
                            }
                            label="Enable Role"
                          />
                        </Box>

                        <Grid container spacing={3}>
                          <Grid item xs={12} md={4}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                              Sidebar / Module Access
                            </Typography>
                            {(config.modules || []).map((item) => (
                              <FormControlLabel
                                key={`${role.role_key}-${item.key}`}
                                control={
                                  <Checkbox
                                    checked={Boolean(role.module_permissions?.[item.key])}
                                    onChange={(e) => handlePermissionChange(role.role_key, 'module_permissions', item.key, e.target.checked)}
                                  />
                                }
                                label={item.label}
                              />
                            ))}
                          </Grid>

                          <Grid item xs={12} md={8}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                              Action Permissions
                            </Typography>
                            <Grid container spacing={0.5}>
                              {(config.actions || []).map((item) => (
                                <Grid item xs={12} sm={6} key={`${role.role_key}-${item.key}`}>
                                  <FormControlLabel
                                    control={
                                      <Checkbox
                                        checked={Boolean(role.action_permissions?.[item.key])}
                                        onChange={(e) => handlePermissionChange(role.role_key, 'action_permissions', item.key, e.target.checked)}
                                      />
                                    }
                                    label={item.label}
                                  />
                                </Grid>
                              ))}
                            </Grid>
                          </Grid>
                        </Grid>

                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                          <Button
                            variant="contained"
                            onClick={() => handleSaveRole(role)}
                            disabled={savingRoleKey === role.role_key}
                            sx={{ bgcolor: '#1565C0', color: '#FFFFFF', fontWeight: 700, '&:hover': { bgcolor: '#0D47A1' } }}
                          >
                            {savingRoleKey === role.role_key ? 'Saving...' : `Save ${role.display_name}`}
                          </Button>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </>
          )}
        </CardContent>
      </Card>
    </Grid>
  );
}

export default RolePermissionMatrix;

