module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['react', 'react-hooks'],
  settings: {
    react: {
      version: 'detect',
    },
  },
  rules: {
    // Allow console.log for debugging (can be cleaned up later)
    'no-console': 'off',
    
    // Warn about unused vars, but don't block compilation
    'no-unused-vars': ['warn', { 
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_',
      ignoreRestSiblings: true,
      caughtErrors: 'none'
    }],
    
    // React rules
    'react/prop-types': 'off', // Not using prop-types
    'react/react-in-jsx-scope': 'off', // Not needed in React 17+
    'react/no-unescaped-entities': 'off', // Allow quotes/apostrophes in JSX
    
    // React hooks - keep rules-of-hooks as error (critical)
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn', // Warn about missing dependencies
    
    // Other rules
    'no-debugger': 'warn', // Warn instead of error
    'no-case-declarations': 'off', // Allow case declarations
  },
};
