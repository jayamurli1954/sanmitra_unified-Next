const MODULE_CONFIG_CACHE_KEY = 'layout_module_config_cache_v1';

const escapeHtml = (value = '') =>
  String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const readCachedTempleConfig = () => {
  try {
    const raw = localStorage.getItem(MODULE_CONFIG_CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    if (parsed.value && typeof parsed.value === 'object') return parsed.value;
    return parsed;
  } catch (err) {
    return {};
  }
};

export const getReportBranding = () => {
  const temple = readCachedTempleConfig();
  const templeName =
    temple.temple_name ||
    temple.name ||
    temple.trust_name ||
    'Temple';

  const addressParts = [
    temple.address,
    temple.city,
    temple.state,
    temple.pincode,
  ]
    .map((v) => String(v || '').trim())
    .filter(Boolean);

  return {
    templeName,
    addressLine: addressParts.join(', '),
    phone: String(temple.phone || '').trim(),
    email: String(temple.email || '').trim(),
    logoUrl: String(temple.logo_url || temple.logo || '').trim(),
  };
};

export const formatReportPeriod = (period) => {
  if (!period) return '';
  if (typeof period === 'string') {
    return period.trim();
  }
  const from = String(period.from || period.fromDate || '').trim();
  const to = String(period.to || period.toDate || '').trim();
  if (from && to) return `${from} to ${to}`;
  if (from) return from;
  if (to) return to;
  return '';
};

export const buildReportHeaderHtml = ({ title = 'Report', period = '' } = {}) => {
  const branding = getReportBranding();
  const periodText = formatReportPeriod(period);
  const generatedAt = new Date().toLocaleString();
  const logoBlock = branding.logoUrl
    ? `<img src="${escapeHtml(branding.logoUrl)}" alt="Temple Logo" style="max-height:56px;max-width:56px;object-fit:contain;" />`
    : '';

  return `
    <div class="report-header">
      <div class="brand-left">${logoBlock}</div>
      <div class="brand-main">
        <div class="temple-name">${escapeHtml(branding.templeName)}</div>
        ${branding.addressLine ? `<div class="temple-sub">${escapeHtml(branding.addressLine)}</div>` : ''}
        ${(branding.phone || branding.email) ? `<div class="temple-sub">${escapeHtml([branding.phone ? `Phone: ${branding.phone}` : '', branding.email ? `Email: ${branding.email}` : ''].filter(Boolean).join(' | '))}</div>` : ''}
      </div>
      <div class="brand-right"></div>
    </div>
    <div class="report-title">${escapeHtml(title)}</div>
    ${periodText ? `<div class="report-period">Period: ${escapeHtml(periodText)}</div>` : ''}
    <div class="report-generated">Generated: ${escapeHtml(generatedAt)}</div>
  `;
};

export const reportBaseStyles = `
  @page { margin: 12mm; }
  body { font-family: Arial, sans-serif; font-size: 12px; color: #222; }
  .report-header { display: grid; grid-template-columns: 62px 1fr 62px; align-items: center; gap: 8px; border-bottom: 1px solid #bbb; padding-bottom: 6px; margin-bottom: 8px; }
  .temple-name { font-size: 18px; font-weight: 700; text-align: center; }
  .temple-sub { font-size: 11px; color: #444; text-align: center; margin-top: 2px; }
  .report-title { text-align: center; font-size: 15px; font-weight: 700; margin: 8px 0 3px; }
  .report-period, .report-generated { text-align: center; font-size: 11px; color: #555; margin-bottom: 3px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f2f2f2; font-weight: 700; }
  td.num, th.num { text-align: right; }
  .page-footer { margin-top: 8px; font-size: 10px; color: #666; text-align: right; }
  .page-break { page-break-after: always; }
`;

export const tryExtractPeriodFromText = (text = '') => {
  const match = String(text).match(/Period:\s*([^\n\r]+)/i);
  return match ? match[1].trim() : '';
};

