import React, { createContext, useContext, useState } from 'react';
import { Backdrop, CircularProgress, Typography } from '@mui/material';

const LoadingContext = createContext();

export const useLoading = () => {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error('useLoading must be used within LoadingProvider');
  }
  return context;
};

export const LoadingProvider = ({ children }) => {
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');

  const startLoading = (message = 'Loading...') => {
    setLoadingMessage(message);
    setLoading(true);
  };

  const stopLoading = () => {
    setLoading(false);
    setLoadingMessage('');
  };

  return (
    <LoadingContext.Provider
      value={{
        loading,
        loadingMessage,
        startLoading,
        stopLoading,
      }}
    >
      {children}
      <Backdrop
        sx={{
          color: '#fff',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          flexDirection: 'column',
        }}
        open={loading}
      >
        <CircularProgress color="inherit" />
        {loadingMessage && (
          <Typography variant="h6" sx={{ mt: 2 }}>
            {loadingMessage}
          </Typography>
        )}
      </Backdrop>
    </LoadingContext.Provider>
  );
};




