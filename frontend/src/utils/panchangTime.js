/** Local civil date as YYYY-MM-DD (not UTC from toISOString). */
export function localISODate(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Parse panchang datetimes. Backend strings are naive IST. */
export function parsePanchangDateTime(value) {
  if (!value) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  const raw = String(value).trim();
  if (!raw) return null;
  if (/[zZ]$/.test(raw) || /[+-]\d{2}:\d{2}$/.test(raw)) {
    const parsed = new Date(raw);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const iso = raw.includes('T') ? raw : raw.replace(' ', 'T');
  const parsed = new Date(`${iso}+05:30`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function isPanchangLimbEnded(endTime, now = new Date()) {
  const end = parsePanchangDateTime(endTime);
  if (!end) return false;
  return end.getTime() <= now.getTime();
}

export function liveLimbName(limb, nextName, { isLiveToday = false, now = new Date() } = {}) {
  if (!limb) return '';
  const fallback = limb.full_name || limb.name || '';
  if (!isLiveToday || !nextName || !isPanchangLimbEnded(limb.end_time, now)) {
    return fallback;
  }
  return nextName;
}

const TITHI_NAMES = [
  'Pratipada',
  'Dwitiya',
  'Tritiya',
  'Chaturthi',
  'Panchami',
  'Shashthi',
  'Saptami',
  'Ashtami',
  'Navami',
  'Dashami',
  'Ekadashi',
  'Dwadashi',
  'Trayodashi',
  'Chaturdashi',
];

export function getNextTithiName(tithi = {}) {
  const number = Number(tithi.number);
  const paksha = tithi.paksha || '';
  if (!number || number < 1 || number > 15) return 'Next tithi';
  if (number < 14) return `${paksha} ${TITHI_NAMES[number]}`.trim();
  if (number === 14) return paksha === 'Shukla' ? 'Shukla Purnima' : 'Krishna Amavasya';
  return paksha === 'Shukla' ? 'Krishna Pratipada' : 'Shukla Pratipada';
}

export function formatTransitionTime(value, fallback) {
  if (fallback) return fallback;
  const date = parsePanchangDateTime(value);
  if (!date) return '';
  return date.toLocaleTimeString('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

export function formatCountdown(diff) {
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);
  return `${hours}h ${minutes}m ${seconds}s`;
}

export function resolveLivePanchangLimbs(data, { isLiveToday = false } = {}) {
  const tithi = data?.panchang?.tithi;
  const nakshatra = data?.panchang?.nakshatra;
  const nextTithiName = getNextTithiName(tithi || {});
  return {
    tithi,
    nakshatra,
    nextTithiName,
    liveTithiName: liveLimbName(tithi, nextTithiName, { isLiveToday }),
    liveNakshatraName: liveLimbName(nakshatra, nakshatra?.next_nakshatra, { isLiveToday }),
    tithiUntil: formatTransitionTime(tithi?.end_time, tithi?.end_time_formatted),
    nakshatraUntil: formatTransitionTime(nakshatra?.end_time, nakshatra?.end_time_formatted),
    asOfIst: data?.calculation_metadata?.as_of_ist
      ? formatTransitionTime(data.calculation_metadata.as_of_ist)
      : '',
  };
}
