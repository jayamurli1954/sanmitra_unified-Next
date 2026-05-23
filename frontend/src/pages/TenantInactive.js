import React, { useMemo } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Stack,
  Typography,
} from '@mui/material';
import LockPersonIcon from '@mui/icons-material/LockPerson';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate } from 'react-router-dom';
import { clearAuthSession } from '../utils/authStorage';
import { clearTenantInactiveReason, readTenantInactiveReason } from '../utils/tenantInactive';

function TenantInactive() {
  const navigate = useNavigate();
  const message = useMemo(() => readTenantInactiveReason(), []);

  const handleBackToLogin = () => {
    clearTenantInactiveReason();
    clearAuthSession();
    navigate('/login', { replace: true });
  };

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Card elevation={4}>
        <CardContent>
          <Stack spacing={2.5}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <LockPersonIcon color="warning" sx={{ fontSize: 56 }} />
            </Box>

            <Typography variant="h4" align="center" sx={{ fontWeight: 700 }}>
              Account Inactive
            </Typography>

            <Typography variant="body1" align="center" color="text.secondary">
              {message || 'Tenant is inactive'}
            </Typography>

            <Typography variant="body2" align="center" color="text.secondary">
              Your temple or trust account is currently inactive. Contact SanMitra platform support to reactivate access.
            </Typography>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="center" sx={{ pt: 1 }}>
              <Button variant="contained" startIcon={<LogoutIcon />} onClick={handleBackToLogin}>
                Back to Login
              </Button>
              <Button
                variant="outlined"
                startIcon={<SupportAgentIcon />}
                onClick={() => {
                  window.location.href = 'mailto:support@sanmitra.com';
                }}
              >
                Contact Support
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Container>
  );
}

export default TenantInactive;
