import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import visitorsService from '../services/visitorsService';
import { QRCodeSVG } from 'qrcode.react';

const PublicPassScreen = () => {
  const { visitorId } = useParams();
  const [pass, setPass] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPass = async () => {
      try {
        const data = await visitorsService.getPublicPass(visitorId);
        setPass(data);
      } catch (err) {
        console.error('Error loading pass:', err);
        setError(err.response?.data?.detail || 'Gate pass not found or expired.');
      } finally {
        setLoading(false);
      }
    };
    fetchPass();
  }, [visitorId]);

  const formatExpirationTime = (isoString) => {
    if (!isoString) return '';
    try {
      return new Date(isoString).toLocaleString([], {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return '';
    }
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '600', color: '#333' }}>
          Retrieving Gate Pass...
        </div>
      </div>
    );
  }

  if (error || !pass) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        padding: '20px'
      }}>
        <div style={{
          background: 'white',
          padding: '32px',
          borderRadius: '16px',
          boxShadow: '0 8px 30px rgba(0,0,0,0.1)',
          maxWidth: '400px',
          textAlign: 'center',
          border: '1px solid #fee2e2'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <h2 style={{ color: '#dc2626', margin: '0 0 12px 0' }}>Access Denied</h2>
          <p style={{ color: '#666', fontSize: '15px', lineHeight: '1.6', margin: 0 }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      padding: '24px'
    }}>
      <div style={{
        background: 'white',
        borderRadius: '24px',
        boxShadow: '0 12px 40px rgba(0,0,0,0.25)',
        width: '100%',
        maxWidth: '420px',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.2)'
      }}>
        {/* Pass Header */}
        <div style={{
          background: 'linear-gradient(90deg, #007AFF 0%, #0056b3 100%)',
          padding: '24px 20px',
          textAlign: 'center',
          color: 'white'
        }}>
          <img
            src="/gruhamitra/GruhaMitra_Logo.png"
            alt="GruhaMitra Logo"
            style={{ height: '40px', marginBottom: '8px', filter: 'brightness(0) invert(1)' }}
          />
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '700', letterSpacing: '0.5px' }}>
            GRUHAMITRA GATE PASS
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', opacity: 0.85 }}>
            Verified Resident Invitation
          </p>
        </div>

        {/* Pass Body */}
        <div style={{ padding: '32px 24px', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 6px 0', fontSize: '22px', color: '#111827', fontWeight: '800' }}>
            {pass.visitor_name}
          </h4>
          <div style={{
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '999px',
            background: pass.is_expired ? '#fee2e2' : '#e0f2fe',
            color: pass.is_expired ? '#b91c1c' : '#0369a1',
            fontWeight: '700',
            fontSize: '13px',
            textTransform: 'uppercase',
            marginBottom: '24px'
          }}>
            {pass.is_expired ? 'Expired Invite' : `Guest for Flat ${pass.flat_number}`}
          </div>

          {pass.is_expired ? (
            <div style={{
              background: '#fef2f2',
              border: '2px dashed #f87171',
              padding: '32px 16px',
              borderRadius: '20px',
              marginBottom: '24px',
              color: '#991b1b'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '12px' }}>⏰</div>
              <strong style={{ display: 'block', fontSize: '18px', marginBottom: '4px' }}>Invitation Expired</strong>
              <span style={{ fontSize: '13px', color: '#7f1d1d' }}>
                This pass expired on {formatExpirationTime(pass.expires_at)}. Please request a new invite pass from the resident.
              </span>
            </div>
          ) : (
            <>
              {/* QR Render */}
              <div style={{
                background: '#f8fafc',
                padding: '24px',
                borderRadius: '20px',
                display: 'inline-block',
                boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.05)',
                marginBottom: '24px',
                border: '1px solid #e2e8f0'
              }}>
                <QRCodeSVG value={pass.id} size={180} />
              </div>

              {/* Passcode Display */}
              <div style={{
                display: 'block',
                marginBottom: '24px'
              }}>
                <div style={{
                  background: '#f1f5f9',
                  padding: '12px 24px',
                  borderRadius: '12px',
                  display: 'inline-block'
                }}>
                  <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '1px', marginBottom: '4px' }}>
                    Passcode
                  </div>
                  <div style={{ fontSize: '28px', fontWeight: '800', color: '#0f172a', letterSpacing: '4px' }}>
                    {pass.passcode}
                  </div>
                </div>
              </div>

              {pass.expires_at && (
                <div style={{ fontSize: '13px', color: '#ef4444', fontWeight: '600', marginBottom: '16px' }}>
                  ⏰ Valid until: {formatExpirationTime(pass.expires_at)}
                </div>
              )}

              <p style={{
                fontSize: '13px',
                color: '#64748b',
                lineHeight: '1.6',
                margin: '0 0 8px 0',
                fontWeight: '500'
              }}>
                Please show this QR code or passcode to the security guard at the gate for automated check-in.
              </p>
            </>
          )}
        </div>

        {/* Footer info */}
        <div style={{
          background: '#f8fafc',
          padding: '16px 20px',
          textAlign: 'center',
          fontSize: '11px',
          color: '#94a3b8',
          borderTop: '1px solid #e2e8f0'
        }}>
          Powered by GruhaMitra Gate Operations.
        </div>
      </div>
    </div>
  );
};

export default PublicPassScreen;
