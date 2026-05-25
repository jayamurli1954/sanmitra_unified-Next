const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

// Keep CRA production builds from failing on pre-existing lint warnings in CI.
process.env.CI = 'false';
process.env.NODE_OPTIONS = `${process.env.NODE_OPTIONS || ''} --no-deprecation`.trim();

const repoRoot = path.resolve(__dirname, '..');
const buildDir = path.join(repoRoot, 'build');

function copyStaticDir(name) {
  const source = path.join(repoRoot, name);
  const destination = path.join(buildDir, name);
  if (!fs.existsSync(source)) {
    return;
  }
  fs.rmSync(destination, { recursive: true, force: true });
  fs.cpSync(source, destination, { recursive: true });
}

const buildResult = spawnSync(
  process.execPath,
  [require.resolve('react-scripts/scripts/build')],
  {
    cwd: repoRoot,
    env: process.env,
    stdio: 'inherit',
  },
);

if (buildResult.status !== 0) {
  process.exit(buildResult.status || 1);
}

copyStaticDir('assets');
copyStaticDir('shared');
copyStaticDir('mitrabooks-erp');
