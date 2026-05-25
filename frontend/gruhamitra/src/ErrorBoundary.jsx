import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          padding: '20px',
          fontFamily: 'sans-serif',
          backgroundColor: '#f5f5f5'
        }}>
          <h1 style={{ color: '#ff4444', marginBottom: '20px' }}> Something went wrong</h1>
          <p style={{ color: '#666', fontSize: '18px', marginBottom: '20px' }}>
            GruhaMitra encountered an error while loading.
          </p>
          {this.state.error && (
            <div style={{
              background: '#fff',
              padding: '15px',
              borderRadius: '8px',
              maxWidth: '800px',
              marginTop: '20px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}>
              <p style={{ color: '#333', fontSize: '14px', marginBottom: '10px', fontWeight: 'bold' }}>
                Error: {this.state.error.toString()}
              </p>
              {this.state.errorInfo && (
                <details style={{ marginTop: '10px' }}>
                  <summary style={{ cursor: 'pointer', color: '#007AFF', marginBottom: '10px' }}>
                    Stack Trace
                  </summary>
                  <pre style={{
                    color: '#666',
                    fontSize: '11px',
                    textAlign: 'left',
                    overflowX: 'auto',
                    background: '#f5f5f5',
                    padding: '10px',
                    borderRadius: '4px'
                  }}>
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>
          )}
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '20px',
              padding: '12px 24px',
              background: '#007AFF',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;



