/**
 * GruhaMitra Splash Screen
 * Shows logo video after login, before dashboard
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const SplashScreen = () => {
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const [videoEnded, setVideoEnded] = useState(false);

  useEffect(() => {
    // Play video when component mounts
    if (videoRef.current) {
      videoRef.current.play().catch(err => {
        console.warn('Video autoplay failed:', err);
        // If autoplay fails, proceed after a delay
        setTimeout(() => {
          setVideoEnded(true);
        }, 2000);
      });
    }
  }, []);

  useEffect(() => {
    // Navigate to dashboard when video ends
    if (videoEnded) {
      const timer = setTimeout(() => {
        navigate('/dashboard');
      }, 500); // Small delay for smooth transition
      return () => clearTimeout(timer);
    }
  }, [videoEnded, navigate]);

  const handleVideoEnd = () => {
    setVideoEnded(true);
  };

  const handleSkip = () => {
    setVideoEnded(true);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #FFF7EC 0%, #FFFFFF 100%)',
      position: 'relative',
    }}>
      {/* Logo Video */}
      <div style={{
        width: '100%',
        maxWidth: '400px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}>
        <video
          ref={videoRef}
          onEnded={handleVideoEnd}
          preload="metadata"
          style={{
            width: '100%',
            height: 'auto',
            maxWidth: '400px',
            borderRadius: '12px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
          }}
          muted
          playsInline
        >
          <source src="/gruhamitra/GruhaMitra_Logo.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </div>

      {/* Skip Button (appears after 1 second) */}
      <button
        onClick={handleSkip}
        style={{
          position: 'absolute',
          bottom: '40px',
          padding: '10px 24px',
          background: 'rgba(122, 62, 12, 0.1)',
          color: 'var(--gm-deep-brown)',
          border: '2px solid var(--gm-orange)',
          borderRadius: '8px',
          cursor: 'pointer',
          fontSize: '14px',
          fontWeight: '600',
          transition: 'all 0.3s',
          opacity: videoEnded ? 0 : 1,
        }}
        onMouseEnter={(e) => {
          e.target.style.background = 'var(--gm-orange)';
          e.target.style.color = 'white';
        }}
        onMouseLeave={(e) => {
          e.target.style.background = 'rgba(122, 62, 12, 0.1)';
          e.target.style.color = 'var(--gm-deep-brown)';
        }}
      >
        Skip
      </button>
    </div>
  );
};

export default SplashScreen;


