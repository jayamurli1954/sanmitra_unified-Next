/**
 * Panchang infographic card (English / ಕನ್ನಡ / संस्कृतम्) drawn on a canvas so it
 * can be shared to WhatsApp as an image.
 *
 * Framework-free: used by the React Panchang page and the vanilla MandirMitra
 * workspace. `buildPanchangInfographicModel` is pure (no DOM) and holds every
 * word that appears on the card, so the text can be reviewed and unit-tested.
 */
import {
  PANCHANG_I18N,
  formatClock,
  limbEndLabel,
  masaParts,
  timeRange,
  triParts,
} from './panchang-whatsapp-message.js';

export const INFOGRAPHIC_LABELS = {
  title: { en: 'Panchang', kn: 'ಪಂಚಾಂಗ', sa: 'पञ्चाङ्गम्' },
  columns: { en: 'English', kn: 'ಕನ್ನಡ', sa: 'संस्कृतम्' },
  festival: { en: 'Festival', kn: 'ಹಬ್ಬ', sa: 'उत्सवः' },
  samvatsara: { en: 'Samvatsara', kn: 'ಸಂವತ್ಸರ', sa: 'संवत्सरः' },
  ayana: { en: 'Ayana', kn: 'ಅಯನ', sa: 'अयनम्' },
  masa: { en: 'Masa', kn: 'ಮಾಸ', sa: 'मासः' },
  vara: { en: 'Vara', kn: 'ವಾರ', sa: 'वासरः' },
  tithi: { en: 'Tithi', kn: 'ತಿಥಿ', sa: 'तिथिः' },
  nakshatra: { en: 'Nakshatra', kn: 'ನಕ್ಷತ್ರ', sa: 'नक्षत्रम्' },
  yoga: { en: 'Yoga', kn: 'ಯೋಗ', sa: 'योगः' },
  karana: { en: 'Karana', kn: 'ಕರಣ', sa: 'करणम्' },
  inauspicious: { en: 'Inauspicious', kn: 'ಅಶುಭ ಕಾಲ', sa: 'अशुभकालः' },
  auspicious: { en: 'Auspicious', kn: 'ಶುಭ ಕಾಲ', sa: 'शुभकालः' },
  rahu: { en: 'Rahu Kala', kn: 'ರಾಹುಕಾಲ' },
  yamaganda: { en: 'Yamaganda', kn: 'ಯಮಗಂಡ' },
  gulika: { en: 'Gulika Kala', kn: 'ಗುಳಿಕಕಾಲ' },
  durMuhurta: { en: 'Dur Muhurta', kn: 'ದುರ್ಮುಹೂರ್ತ' },
  varjyam: { en: 'Varjyam', kn: 'ವರ್ಜ್ಯ' },
  abhijit: { en: 'Abhijit Muhurta', kn: 'ಅಭಿಜಿತ್ ಮುಹೂರ್ತ' },
  brahma: { en: 'Brahma Muhurta', kn: 'ಬ್ರಾಹ್ಮೀ ಮುಹೂರ್ತ' },
  amrita: { en: 'Amrita Kala', kn: 'ಅಮೃತಕಾಲ' },
  sunrise: { en: 'Sunrise', kn: 'ಸೂರ್ಯೋದಯ' },
  sunset: { en: 'Sunset', kn: 'ಸೂರ್ಯಾಸ್ತ' },
};

const L = INFOGRAPHIC_LABELS;
const DASH = '—';

function cleanTime(value) {
  const text = timeRange(value);
  return text && text !== DASH ? text : '';
}

function cleanClock(value) {
  const text = formatClock(value);
  return text && text !== DASH ? text : '';
}

function festivalParts(data) {
  const fromSpecial = (data.south_india_special || [])
    .filter((item) => item && item.type === 'festival' && item.english)
    .map((item) => ({
      en: item.english,
      kn: item.kannada || item.english,
      sa: item.sanskrit || item.english,
    }));
  if (fromSpecial.length) return fromSpecial;
  return (data.festivals || [])
    .map((fest) => fest?.name || fest?.title)
    .filter(Boolean)
    .map((name) => ({ en: name, kn: name, sa: name }));
}

/**
 * Everything the card shows, as plain data.
 * @param {object} data Panchang API response for one day
 */
export function buildPanchangInfographicModel(data) {
  if (!data) return null;

  const gregorian = data.date?.gregorian || {};
  const hindu = data.date?.hindu || {};
  const panchang = data.panchang || {};
  const tithi = panchang.tithi || {};
  const nakshatra = panchang.nakshatra || {};
  const yoga = panchang.yoga || {};
  const karana = panchang.karana || {};
  const vara = panchang.vara || {};
  const kaala = data.inauspicious_times || data.kaala || {};
  const good = data.auspicious_times || data.muhurat || {};
  const extraBad = data.additional_inauspicious_times || {};
  const sunMoon = data.sun_moon || {};
  const I = PANCHANG_I18N;

  const samvatsaraName = hindu.samvatsara_name || data.samvatsara?.name || hindu.samvatsara?.name || '';
  const masaName = hindu.month || hindu.lunar_month || hindu.lunar_month_purnimanta || '';
  const ayanaName = typeof data.ayana === 'string' ? data.ayana : data.ayana?.name || '';
  const varaName = vara.name || gregorian.day || gregorian.day_of_week || '';
  const paksha = tithi.paksha || hindu.paksha || '';

  let tithiValue = triParts(tithi.name, I.tithi);
  if (tithiValue && paksha) {
    const p = triParts(paksha, I.paksha);
    tithiValue = {
      en: `${p.en} ${tithiValue.en}`,
      kn: `${p.kn} ${tithiValue.kn}`,
      sa: `${p.sa} ${tithiValue.sa}`,
    };
  }
  let nakshatraValue = triParts(nakshatra.name, I.nakshatra);
  if (nakshatraValue && nakshatra.pada) {
    nakshatraValue = { ...nakshatraValue, en: `${nakshatraValue.en} (Pada ${nakshatra.pada})` };
  }

  const till = (limb) => limbEndLabel(limb, gregorian.date);
  const rows = [
    { key: 'samvatsara', label: L.samvatsara, value: triParts(samvatsaraName, I.samvatsara), till: '' },
    { key: 'ayana', label: L.ayana, value: triParts(ayanaName, I.ayana), till: '' },
    { key: 'masa', label: L.masa, value: masaParts(masaName), till: '' },
    { key: 'vara', label: L.vara, value: triParts(varaName, I.vara), till: '' },
    { key: 'tithi', label: L.tithi, value: tithiValue, till: till(tithi) },
    { key: 'nakshatra', label: L.nakshatra, value: nakshatraValue, till: till(nakshatra) },
    { key: 'yoga', label: L.yoga, value: triParts(yoga.name, I.yoga), till: till(yoga) },
    { key: 'karana', label: L.karana, value: triParts(karana.current || karana.name, I.karana), till: till(karana) },
  ].filter((row) => row.value);

  const timing = (label, value) => ({ label, time: value });
  const inauspicious = [
    timing(L.rahu, cleanTime(kaala.rahu_kaal || kaala.rahu)),
    timing(L.yamaganda, cleanTime(kaala.yamaganda)),
    timing(L.gulika, cleanTime(kaala.gulika)),
    timing(L.durMuhurta, cleanTime(extraBad.dur_muhurta || kaala.dur_muhurta)),
    timing(L.varjyam, cleanTime(extraBad.varjyam || kaala.varjyam)),
  ].filter((item) => item.time);
  const auspicious = [
    timing(L.abhijit, cleanTime(good.abhijit_muhurat || good.abhijit)),
    timing(L.brahma, cleanTime(good.brahma_muhurat || good.brahma)),
    timing(L.amrita, cleanTime(good.amrita_kalam || kaala.amrita)),
    timing(L.sunrise, cleanClock(sunMoon.sunrise)),
    timing(L.sunset, cleanClock(sunMoon.sunset)),
  ].filter((item) => item.time);

  return {
    title: L.title,
    city: data.location?.city || '',
    dateLabel: gregorian.formatted || gregorian.date || '',
    isoDate: gregorian.date || '',
    festivals: festivalParts(data).slice(0, 3),
    rows,
    inauspicious,
    auspicious,
    footer: 'MandirMitra · SanMitra Tech',
    disclaimer: 'For guidance only — confirm with temple tradition before muhurta use.',
  };
}

export function panchangInfographicFileName(model) {
  return `panchang-${model?.isoDate || 'today'}.png`;
}

// ---------------------------------------------------------------------------
// Canvas rendering
// ---------------------------------------------------------------------------

const WIDTH = 1080;
const FONT = '"Noto Sans","Noto Sans Kannada","Noto Sans Devanagari","Nirmala UI","Kohinoor Devanagari","Kannada Sangam MN",system-ui,sans-serif';
const C = {
  paper: '#FBF4E1',
  paperAlt: '#F5EACB',
  maroon: '#7A1F1F',
  maroonDark: '#5A1414',
  gold: '#C9972B',
  goldSoft: '#E8CF8E',
  ink: '#3A2410',
  inkSoft: '#6B5338',
  saffron: '#E07B1A',
  saffronSoft: '#FDE9C9',
  red: '#B3261E',
  redSoft: '#FBE4E1',
  green: '#2E7D32',
  greenSoft: '#E3F1E0',
  white: '#FFFFFF',
};
const ROW_ICONS = {
  samvatsara: { color: '#E07B1A', shape: 'calendar' },
  ayana: { color: '#EF9A1A', shape: 'sun' },
  masa: { color: '#3F6FB5', shape: 'moon' },
  vara: { color: '#2A9D8F', shape: 'sun' },
  tithi: { color: '#4A5FC1', shape: 'half' },
  nakshatra: { color: '#3C9A4B', shape: 'star' },
  yoga: { color: '#E07B1A', shape: 'knot' },
  karana: { color: '#C0562B', shape: 'diamond' },
};

function setFont(ctx, size, weight = 400) {
  ctx.font = `${weight} ${size}px ${FONT}`;
}

/** Draw one line, shrinking the font until it fits `maxWidth`. */
function fitText(ctx, text, x, y, maxWidth, size, weight, color, align = 'left', minSize = 16) {
  let s = size;
  setFont(ctx, s, weight);
  while (s > minSize && ctx.measureText(text).width > maxWidth) {
    s -= 1;
    setFont(ctx, s, weight);
  }
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.fillText(text, x, y);
  ctx.textAlign = 'left';
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawIcon(ctx, cx, cy, r, { color, shape }) {
  ctx.save();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = C.white;
  ctx.strokeStyle = C.white;
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  const u = r * 0.5;
  if (shape === 'sun') {
    ctx.beginPath();
    ctx.arc(cx, cy, u * 0.55, 0, Math.PI * 2);
    ctx.fill();
    for (let i = 0; i < 8; i += 1) {
      const a = (Math.PI / 4) * i;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * u * 0.85, cy + Math.sin(a) * u * 0.85);
      ctx.lineTo(cx + Math.cos(a) * u * 1.25, cy + Math.sin(a) * u * 1.25);
      ctx.stroke();
    }
  } else if (shape === 'moon') {
    ctx.beginPath();
    ctx.arc(cx, cy, u, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx + u * 0.45, cy - u * 0.2, u * 0.85, 0, Math.PI * 2);
    ctx.fill();
  } else if (shape === 'half') {
    ctx.beginPath();
    ctx.arc(cx, cy, u, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, u, -Math.PI / 2, Math.PI / 2);
    ctx.fill();
  } else if (shape === 'star') {
    ctx.beginPath();
    for (let i = 0; i < 10; i += 1) {
      const a = -Math.PI / 2 + (Math.PI / 5) * i;
      const rad = i % 2 === 0 ? u * 1.15 : u * 0.5;
      ctx.lineTo(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad);
    }
    ctx.closePath();
    ctx.fill();
  } else if (shape === 'knot') {
    ctx.beginPath();
    ctx.arc(cx - u * 0.4, cy, u * 0.65, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx + u * 0.4, cy, u * 0.65, 0, Math.PI * 2);
    ctx.stroke();
  } else if (shape === 'diamond') {
    ctx.beginPath();
    ctx.moveTo(cx, cy - u * 1.1);
    ctx.lineTo(cx + u * 0.85, cy);
    ctx.lineTo(cx, cy + u * 1.1);
    ctx.lineTo(cx - u * 0.85, cy);
    ctx.closePath();
    ctx.fill();
  } else {
    // calendar
    roundRect(ctx, cx - u, cy - u * 0.8, u * 2, u * 1.8, 4);
    ctx.fill();
    ctx.fillStyle = color;
    ctx.fillRect(cx - u * 0.7, cy - u * 0.25, u * 1.4, 3);
    ctx.fillRect(cx - u * 0.7, cy + u * 0.3, u * 1.4, 3);
  }
  ctx.restore();
}

const LAYOUT = {
  margin: 36,
  header: 216,
  festivalHead: 52,
  festivalItem: 92,
  tableHead: 54,
  row: 86,
  panelHead: 64,
  panelItem: 70,
  footer: 96,
  gap: 22,
};

function measureHeight(model) {
  const festivals = model.festivals.length
    ? LAYOUT.festivalHead + LAYOUT.festivalItem * model.festivals.length + 18 + LAYOUT.gap
    : 0;
  const panelItems = Math.max(model.inauspicious.length, model.auspicious.length, 1);
  return (
    LAYOUT.margin
    + LAYOUT.header + LAYOUT.gap
    + festivals
    + LAYOUT.tableHead + LAYOUT.row * model.rows.length + LAYOUT.gap
    + LAYOUT.panelHead + LAYOUT.panelItem * panelItems + 16
    + LAYOUT.footer
    + LAYOUT.margin
  );
}

function drawPanel(ctx, x, y, w, h, title, items, color, soft) {
  ctx.fillStyle = soft;
  roundRect(ctx, x, y, w, h, 18);
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.save();
  roundRect(ctx, x, y, w, h, 18);
  ctx.clip();
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w, LAYOUT.panelHead);
  ctx.restore();
  fitText(ctx, `${title.en}  ·  ${title.kn}  ·  ${title.sa}`, x + w / 2, y + 42, w - 32, 27, 700, C.white, 'center');

  items.forEach((item, index) => {
    const top = y + LAYOUT.panelHead + LAYOUT.panelItem * index;
    if (index > 0) {
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.18;
      ctx.fillRect(x + 20, top, w - 40, 1.5);
      ctx.globalAlpha = 1;
    }
    fitText(ctx, `${item.label.en}  ·  ${item.label.kn}`, x + 22, top + 30, w - 44, 22, 500, C.inkSoft);
    fitText(ctx, item.time, x + 22, top + 60, w - 44, 27, 700, color);
  });
}

/**
 * Draw the card. Returns the canvas (created when not supplied).
 * Call `ensurePanchangFonts()` first so Kannada / Devanagari web fonts are ready.
 */
export function renderPanchangInfographic(model, canvas) {
  const target = canvas || document.createElement('canvas');
  const height = measureHeight(model);
  target.width = WIDTH;
  target.height = height;
  const ctx = target.getContext('2d');
  if (!ctx) return target;
  ctx.textBaseline = 'alphabetic';

  // Paper and frame
  ctx.fillStyle = C.paper;
  ctx.fillRect(0, 0, WIDTH, height);
  ctx.strokeStyle = C.gold;
  ctx.lineWidth = 6;
  roundRect(ctx, 14, 14, WIDTH - 28, height - 28, 26);
  ctx.stroke();
  ctx.lineWidth = 2;
  roundRect(ctx, 24, 24, WIDTH - 48, height - 48, 20);
  ctx.stroke();

  const m = LAYOUT.margin;
  const inner = WIDTH - m * 2;
  let y = m;

  // Header
  const grad = ctx.createLinearGradient(0, y, 0, y + LAYOUT.header);
  grad.addColorStop(0, C.maroon);
  grad.addColorStop(1, C.maroonDark);
  ctx.fillStyle = grad;
  roundRect(ctx, m, y, inner, LAYOUT.header, 18);
  ctx.fill();
  ctx.fillStyle = C.gold;
  ctx.fillRect(m + 60, y + LAYOUT.header - 62, inner - 120, 2);
  fitText(ctx, `${model.title.kn}  ·  ${model.title.sa}`, WIDTH / 2, y + 74, inner - 80, 58, 700, C.goldSoft, 'center');
  fitText(ctx, model.title.en.toUpperCase(), WIDTH / 2, y + 128, inner - 80, 32, 600, C.white, 'center');
  const place = [model.city, model.dateLabel].filter(Boolean).join('  ·  ');
  fitText(ctx, place, WIDTH / 2, y + LAYOUT.header - 22, inner - 80, 28, 500, C.goldSoft, 'center');
  y += LAYOUT.header + LAYOUT.gap;

  // Festival banner
  if (model.festivals.length) {
    const h = LAYOUT.festivalHead + LAYOUT.festivalItem * model.festivals.length + 18;
    ctx.fillStyle = C.saffronSoft;
    roundRect(ctx, m, y, inner, h, 18);
    ctx.fill();
    ctx.strokeStyle = C.saffron;
    ctx.lineWidth = 2.5;
    ctx.stroke();
    const head = INFOGRAPHIC_LABELS.festival;
    fitText(ctx, `${head.en}  ·  ${head.kn}  ·  ${head.sa}`, WIDTH / 2, y + 38, inner - 60, 24, 700, C.saffron, 'center');
    model.festivals.forEach((fest, index) => {
      const top = y + LAYOUT.festivalHead + LAYOUT.festivalItem * index;
      fitText(ctx, fest.en, WIDTH / 2, top + 36, inner - 60, 38, 700, C.maroon, 'center');
      const local = [fest.kn, fest.sa].filter((value) => value && value !== fest.en).join('  ·  ');
      if (local) fitText(ctx, local, WIDTH / 2, top + 78, inner - 60, 32, 600, C.ink, 'center');
    });
    y += h + LAYOUT.gap;
  }

  // Limb table
  const colLabel = m + 92;
  const cols = [
    { x: m + 288, w: 232 },
    { x: m + 536, w: 222 },
    { x: m + 774, w: inner - 774 - 16 },
  ];
  ctx.fillStyle = C.gold;
  roundRect(ctx, m, y, inner, LAYOUT.tableHead - 8, 12);
  ctx.fill();
  const columns = INFOGRAPHIC_LABELS.columns;
  [columns.en, columns.kn, columns.sa].forEach((text, index) => {
    fitText(ctx, text, cols[index].x, y + 32, cols[index].w, 24, 700, C.maroonDark);
  });
  y += LAYOUT.tableHead;

  model.rows.forEach((row, index) => {
    const top = y + LAYOUT.row * index;
    if (index % 2 === 0) {
      ctx.fillStyle = C.paperAlt;
      roundRect(ctx, m, top, inner, LAYOUT.row - 6, 12);
      ctx.fill();
    }
    const mid = top + (LAYOUT.row - 6) / 2;
    drawIcon(ctx, m + 46, mid, 28, ROW_ICONS[row.key] || ROW_ICONS.samvatsara);
    fitText(ctx, row.label.en, colLabel, mid - 2, 186, 28, 700, C.maroon);
    fitText(ctx, `${row.label.kn} · ${row.label.sa}`, colLabel, mid + 26, 186, 21, 500, C.inkSoft);
    const baseline = row.till ? mid - 2 : mid + 10;
    fitText(ctx, row.value.en, cols[0].x, baseline, cols[0].w, 28, 600, C.ink);
    if (row.till) fitText(ctx, `till ${row.till}`, cols[0].x, mid + 26, cols[0].w, 22, 500, C.inkSoft);
    fitText(ctx, row.value.kn, cols[1].x, mid + 10, cols[1].w, 30, 600, C.ink);
    fitText(ctx, row.value.sa, cols[2].x, mid + 10, cols[2].w, 30, 600, C.ink);
  });
  y += LAYOUT.row * model.rows.length + LAYOUT.gap;

  // Timing panels
  const panelItems = Math.max(model.inauspicious.length, model.auspicious.length, 1);
  const panelH = LAYOUT.panelHead + LAYOUT.panelItem * panelItems + 16;
  const panelW = (inner - 20) / 2;
  drawPanel(ctx, m, y, panelW, panelH, INFOGRAPHIC_LABELS.inauspicious, model.inauspicious, C.red, C.redSoft);
  drawPanel(ctx, m + panelW + 20, y, panelW, panelH, INFOGRAPHIC_LABELS.auspicious, model.auspicious, C.green, C.greenSoft);
  y += panelH;

  // Footer
  fitText(ctx, model.footer, WIDTH / 2, y + 48, inner, 26, 700, C.maroon, 'center');
  fitText(ctx, model.disclaimer, WIDTH / 2, y + 80, inner - 40, 19, 400, C.inkSoft, 'center');

  return target;
}

/** Wait for the Kannada / Devanagari web fonts (best effort, never throws). */
export async function ensurePanchangFonts() {
  if (typeof document === 'undefined' || !document.fonts?.load) return;
  const samples = [
    ['"Noto Sans Kannada"', 'ಪಂಚಾಂಗ'],
    ['"Noto Sans Devanagari"', 'पञ्चाङ्गम्'],
    ['"Noto Sans"', 'Panchang'],
  ];
  const loads = [];
  samples.forEach(([family, text]) => {
    [400, 500, 600, 700].forEach((weight) => {
      loads.push(document.fonts.load(`${weight} 32px ${family}`, text));
    });
  });
  const timeout = new Promise((resolve) => { setTimeout(resolve, 2500); });
  try {
    await Promise.race([Promise.all(loads), timeout]);
  } catch (err) {
    // System fonts still cover both scripts on Windows, Android, iOS and macOS.
  }
}

export function canvasToPngBlob(canvas) {
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/png');
  });
}

/**
 * Render the card for an API payload; resolves to { canvas, model, file } or
 * null. The PNG `file` is prepared up front so a share button can hand it to
 * the browser immediately, while the click still counts as a user gesture.
 */
export async function createPanchangInfographic(data) {
  const model = buildPanchangInfographicModel(data);
  if (!model || !model.rows.length) return null;
  await ensurePanchangFonts();
  const canvas = renderPanchangInfographic(model);
  let file = null;
  try {
    const blob = await canvasToPngBlob(canvas);
    if (blob) file = new File([blob], panchangInfographicFileName(model), { type: 'image/png' });
  } catch (err) {
    file = null;
  }
  return { canvas, model, file };
}

export const WHATSAPP_WEB_URL = 'https://web.whatsapp.com/';

export function downloadPanchangInfographic(file) {
  const url = URL.createObjectURL(file);
  const link = document.createElement('a');
  link.href = url;
  link.download = file.name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Send the card image to WhatsApp.
 *
 * WhatsApp has no link that attaches an image, so:
 * - where the browser can share files (phones, and desktop browsers with a
 *   share sheet) the system share sheet opens with the image - pick WhatsApp;
 * - otherwise the image is copied to the clipboard and WhatsApp Web opens, so
 *   it only needs to be pasted into the chat;
 * - if the clipboard is not available either, the image is downloaded and
 *   WhatsApp Web opens so it can be attached.
 *
 * @returns {Promise<'shared'|'cancelled'|'copied'|'downloaded'|'unavailable'>}
 */
export async function sharePanchangInfographicToWhatsApp(file) {
  if (!file) return 'unavailable';
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: 'Panchang' });
      return 'shared';
    } catch (err) {
      if (err?.name === 'AbortError') return 'cancelled';
    }
  }
  let outcome = 'copied';
  try {
    // Copy before opening the new tab: the clipboard needs this page focused.
    await navigator.clipboard.write([new window.ClipboardItem({ 'image/png': file })]);
  } catch (err) {
    downloadPanchangInfographic(file);
    outcome = 'downloaded';
  }
  window.open(WHATSAPP_WEB_URL, '_blank', 'noopener,noreferrer');
  return outcome;
}

export const WHATSAPP_SHARE_MESSAGES = {
  shared: '',
  cancelled: '',
  copied: 'Image copied. WhatsApp is opening — open a chat and paste (Ctrl+V).',
  downloaded: 'Image downloaded. WhatsApp is opening — attach the downloaded image in a chat.',
  unavailable: 'The image is not ready yet — try again in a moment.',
};
