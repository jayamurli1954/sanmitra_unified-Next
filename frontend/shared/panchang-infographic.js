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
    footer: 'www.mandirmitra.sanmitratech.in',
    website: 'www.mandirmitra.sanmitratech.in',
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
  footer: 124,
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
export const PANCHANG_LOGOS = {
  mandirmitra: 'data:image/png;base64,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',
  sanmitra: 'data:image/png;base64,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',
};

let cachedLogos = null;

export async function ensurePanchangLogos() {
  if (cachedLogos) return cachedLogos;
  if (typeof Image === 'undefined') return null;
  const load = (src) =>
    new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
  try {
    const [mandir, sanmitra] = await Promise.all([
      load(PANCHANG_LOGOS.mandirmitra),
      load(PANCHANG_LOGOS.sanmitra),
    ]);
    cachedLogos = { mandir, sanmitra };
  } catch (err) {
    cachedLogos = null;
  }
  return cachedLogos;
}

export function renderPanchangInfographic(model, canvas, logos = cachedLogos) {
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

  // Footer with MandirMitra logo (left), SanMitra logo (right), and website + disclaimer in between
  const logoH = 92;
  const logoY = y + Math.round((LAYOUT.footer - logoH) / 2);
  let leftEdge = m + 16;
  let rightEdge = WIDTH - m - 16;

  if (logos?.mandir) {
    const mmW = Math.round(logoH * (logos.mandir.width / logos.mandir.height));
    ctx.drawImage(logos.mandir, m + 16, logoY, mmW, logoH);
    leftEdge = m + 16 + mmW + 20;
  }
  if (logos?.sanmitra) {
    const smW = Math.round(logoH * (logos.sanmitra.width / logos.sanmitra.height));
    ctx.drawImage(logos.sanmitra, WIDTH - m - 16 - smW, logoY, smW, logoH);
    rightEdge = WIDTH - m - 16 - smW - 20;
  }

  const centerMaxW = Math.max(rightEdge - leftEdge, inner - 280);
  fitText(ctx, model.website || model.footer, WIDTH / 2, y + 54, centerMaxW, 26, 700, C.maroon, 'center');
  fitText(ctx, model.disclaimer, WIDTH / 2, y + 88, centerMaxW, 19, 400, C.inkSoft, 'center');

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
  await Promise.all([ensurePanchangFonts(), ensurePanchangLogos()]);
  const canvas = renderPanchangInfographic(model, undefined, cachedLogos);
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
