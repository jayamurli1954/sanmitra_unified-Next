// Keep CRA production builds from failing on pre-existing lint warnings in CI.
process.env.CI = 'false';

// CRA 5 pulls react-dev-utils, which still accesses fs.F_OK on newer Node versions.
// Suppress that one upstream deprecation so build and E2E output stays actionable.
const originalEmitWarning = process.emitWarning.bind(process);
process.emitWarning = (warning, ...args) => {
  const warningCode = typeof warning === 'object' && warning ? warning.code : undefined;
  if (warningCode === 'DEP0176' || args.includes('DEP0176')) {
    return;
  }
  return originalEmitWarning(warning, ...args);
};

require('react-scripts/scripts/build');
