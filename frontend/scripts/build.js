const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { build: viteBuild } = require('vite');

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
  fs.cpSync(source, destination, {
    recursive: true,
    filter: (sourcePath) => {
      const basename = path.basename(sourcePath);
      return basename !== '.vercel' && basename !== '.git';
    },
  });
}

function copyStaticFile(name) {
  const source = path.join(repoRoot, name);
  const destination = path.join(buildDir, name);
  if (!fs.existsSync(source)) {
    return;
  }
  fs.copyFileSync(source, destination);
}

function publishMitraBooksLandingIndex() {
  const mitraDir = path.join(buildDir, 'mitrabooks-erp');
  const appShell = path.join(mitraDir, 'index.html');
  const landingShell = path.join(mitraDir, 'landing.html');
  if (!fs.existsSync(appShell) || !fs.existsSync(landingShell)) {
    return;
  }
  fs.copyFileSync(landingShell, appShell);
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

async function run() {
  try {
    await viteBuild({
      configFile: path.join(repoRoot, 'gruhamitra/vite.config.js'),
      logLevel: 'info',
    });
  } catch (error) {
    console.error(error);
    process.exit(1);
  }

  copyStaticDir('assets');
  copyStaticDir('shared');
  copyStaticDir('legalmitra');
  copyStaticDir('mitrabooks-erp');
  publishMitraBooksLandingIndex();
  copyStaticFile('service-worker.js');
  copyStaticFile('sw-register.js');
}

run();
