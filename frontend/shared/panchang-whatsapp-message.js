/**
 * Compact WhatsApp-ready Panchang card text.
 * Uses the same day's API payload; does not change the full Panchang UI layout.
 */

const TITHI_I18N = {
  Pratipada: { kn: 'ಪ್ರತಿಪದ', sa: 'प्रतिपदा' },
  Dwitiya: { kn: 'ದ್ವಿತೀಯ', sa: 'द्वितीया' },
  Tritiya: { kn: 'ತೃತೀಯ', sa: 'तृतीया' },
  Chaturthi: { kn: 'ಚತುರ್ಥಿ', sa: 'चतुर्थी' },
  Panchami: { kn: 'ಪಂಚಮಿ', sa: 'पञ्चमी' },
  Shashthi: { kn: 'ಷಷ್ಠಿ', sa: 'षष्ठी' },
  Saptami: { kn: 'ಸಪ್ತಮಿ', sa: 'सप्तमी' },
  Ashtami: { kn: 'ಅಷ್ಟಮಿ', sa: 'अष्टमी' },
  Navami: { kn: 'ನವಮಿ', sa: 'नवमी' },
  Dashami: { kn: 'ದಶಮಿ', sa: 'दशमी' },
  Ekadashi: { kn: 'ಏಕಾದಶಿ', sa: 'एकादशी' },
  Dwadashi: { kn: 'ದ್ವಾದಶಿ', sa: 'द्वादशी' },
  Trayodashi: { kn: 'ತ್ರಯೋದಶಿ', sa: 'त्रयोदशी' },
  Chaturdashi: { kn: 'ಚತುರ್ದಶಿ', sa: 'चतुर्दशी' },
  Purnima: { kn: 'ಪೌರ್ಣಿಮಾ', sa: 'पूर्णिमा' },
  Amavasya: { kn: 'ಅಮಾವಾಸ್ಯೆ', sa: 'अमावास्या' },
};

const PAKSHA_I18N = {
  Shukla: { kn: 'ಶುಕ್ಲ', sa: 'शुक्ल' },
  Krishna: { kn: 'ಕೃಷ್ಣ', sa: 'कृष्ण' },
};

const NAKSHATRA_I18N = {
  Ashwini: { kn: 'ಅಶ್ವಿನಿ', sa: 'अश्विनी' },
  Bharani: { kn: 'ಭರಣಿ', sa: 'भरणी' },
  Krittika: { kn: 'ಕೃತ್ತಿಕಾ', sa: 'कृत्तिका' },
  Rohini: { kn: 'ರೋಹಿಣಿ', sa: 'रोहिणी' },
  Mrigashira: { kn: 'ಮೃಗಶಿರ', sa: 'मृगशिरा' },
  Ardra: { kn: 'ಆರ್ದ್ರಾ', sa: 'आर्द्रा' },
  Punarvasu: { kn: 'ಪುನರ್ವಸು', sa: 'पुनर्वसु' },
  Pushya: { kn: 'ಪುಷ್ಯ', sa: 'पुष्य' },
  Ashlesha: { kn: 'ಆಶ್ಲೇಷಾ', sa: 'आश्लेषा' },
  Magha: { kn: 'ಮಘಾ', sa: 'मघा' },
  'Purva Phalguni': { kn: 'ಪೂರ್ವ ಫಲ್ಗುನಿ', sa: 'पूर्व फाल्गुनी' },
  'Uttara Phalguni': { kn: 'ಉತ್ತರ ಫಲ್ಗುನಿ', sa: 'उत्तर फाल्गुनी' },
  Hasta: { kn: 'ಹಸ್ತ', sa: 'हस्त' },
  Chitra: { kn: 'ಚಿತ್ರಾ', sa: 'चित्रा' },
  Swati: { kn: 'ಸ್ವಾತಿ', sa: 'स्वाती' },
  Vishakha: { kn: 'ವಿಶಾಖಾ', sa: 'विशाखा' },
  Anuradha: { kn: 'ಅನುರಾಧಾ', sa: 'अनुराधा' },
  Jyeshtha: { kn: 'ಜ್ಯೇಷ್ಠಾ', sa: 'ज्येष्ठा' },
  Mula: { kn: 'ಮೂಲ', sa: 'मूल' },
  Moola: { kn: 'ಮೂಲ', sa: 'मूल' },
  'Purva Ashadha': { kn: 'ಪೂರ್ವಾಷಾಢಾ', sa: 'पूर्वाषाढा' },
  'Uttara Ashadha': { kn: 'ಉತ್ತರಾಷಾಢಾ', sa: 'उत्तराषाढा' },
  Shravana: { kn: 'ಶ್ರವಣ', sa: 'श्रवण' },
  Dhanishta: { kn: 'ಧನಿಷ್ಠಾ', sa: 'धनिष्ठा' },
  Shatabhisha: { kn: 'ಶತಭಿಷಾ', sa: 'शतभिषा' },
  'Purva Bhadrapada': { kn: 'ಪೂರ್ವ ಭಾದ್ರಪದ', sa: 'पूर्व भाद्रपदा' },
  'Uttara Bhadrapada': { kn: 'ಉತ್ತರ ಭಾದ್ರಪದ', sa: 'उत्तर भाद्रपदा' },
  Revati: { kn: 'ರೇವತಿ', sa: 'रेवती' },
};

const YOGA_I18N = {
  Vishkambha: { kn: 'ವಿಷ್ಕಂಭ', sa: 'विष्कम्भ' },
  Priti: { kn: 'ಪ್ರೀತಿ', sa: 'प्रीति' },
  Ayushman: { kn: 'ಆಯುಷ್ಮಾನ್', sa: 'आयुष्मान्' },
  Saubhagya: { kn: 'ಸೌಭಾಗ್ಯ', sa: 'सौभाग्य' },
  Shobhana: { kn: 'ಶೋಭನ', sa: 'शोभन' },
  Atiganda: { kn: 'ಅತಿಗಂಡ', sa: 'अतिगण्ड' },
  Sukarma: { kn: 'ಸುಕರ್ಮ', sa: 'सुकर्म' },
  Dhriti: { kn: 'ಧೃತಿ', sa: 'धृति' },
  Shoola: { kn: 'ಶೂಲ', sa: 'शूल' },
  Ganda: { kn: 'ಗಂಡ', sa: 'गण्ड' },
  Vriddhi: { kn: 'ವೃದ್ಧಿ', sa: 'वृद्धि' },
  Dhruva: { kn: 'ಧ್ರುವ', sa: 'ध्रुव' },
  Vyaghata: { kn: 'ವ್ಯಾಘಾತ', sa: 'व्याघात' },
  Harshana: { kn: 'ಹರ್ಷಣ', sa: 'हर्षण' },
  Vajra: { kn: 'ವಜ್ರ', sa: 'वज्र' },
  Siddhi: { kn: 'ಸಿದ್ಧಿ', sa: 'सिद्धि' },
  Vyatipata: { kn: 'ವ್ಯತೀಪಾತ', sa: 'व्यतीपात' },
  Variyan: { kn: 'ವರೀಯಾನ್', sa: 'वरीयान्' },
  Parigha: { kn: 'ಪರಿಘ', sa: 'परिघ' },
  Shiva: { kn: 'ಶಿವ', sa: 'शिव' },
  Siddha: { kn: 'ಸಿದ್ಧ', sa: 'सिद्ध' },
  Sadhya: { kn: 'ಸಾಧ್ಯ', sa: 'साध्य' },
  Shubha: { kn: 'ಶುಭ', sa: 'शुभ' },
  Shukla: { kn: 'ಶುಕ್ಲ', sa: 'शुक्ल' },
  Brahma: { kn: 'ಬ್ರಹ್ಮ', sa: 'ब्रह्म' },
  Indra: { kn: 'ಇಂದ್ರ', sa: 'इन्द्र' },
  Vaidhriti: { kn: 'ವೈಧೃತಿ', sa: 'वैधृति' },
};

const KARANA_I18N = {
  Bava: { kn: 'ಬವ', sa: 'बव' },
  Balava: { kn: 'ಬಾಲವ', sa: 'बालव' },
  Kaulava: { kn: 'ಕೌಲವ', sa: 'कौलव' },
  Taitila: { kn: 'ತೈತಿಲ', sa: 'तैतिल' },
  Garaja: { kn: 'ಗರಜ', sa: 'गरज' },
  Vanija: { kn: 'ವಣಿಜ', sa: 'वणिज' },
  Vishti: { kn: 'ವಿಷ್ಟಿ', sa: 'विष्टि' },
  Shakuni: { kn: 'ಶಕುನಿ', sa: 'शकुनि' },
  Chatushpada: { kn: 'ಚತುಷ್ಪಾದ', sa: 'चतुष्पाद' },
  Naga: { kn: 'ನಾಗ', sa: 'नाग' },
  Kimstughna: { kn: 'ಕಿಂಸ್ತುಘ್ನ', sa: 'किंस्तुघ्न' },
};

const VARA_I18N = {
  Sunday: { kn: 'ರವಿವಾರ', sa: 'रविवार' },
  Monday: { kn: 'ಸೋಮವಾರ', sa: 'सोमवार' },
  Tuesday: { kn: 'ಮಂಗಳವಾರ', sa: 'मंगलवार' },
  Wednesday: { kn: 'ಬುಧವಾರ', sa: 'बुधवार' },
  Thursday: { kn: 'ಗುರುವಾರ', sa: 'गुरुवार' },
  Friday: { kn: 'ಶುಕ್ರವಾರ', sa: 'शुक्रवार' },
  Saturday: { kn: 'ಶನಿವಾರ', sa: 'शनिवार' },
};

const AYANA_I18N = {
  Uttarayana: { kn: 'ಉತ್ತರಾಯಣ', sa: 'उत्तरायण' },
  Dakshinayana: { kn: 'ದಕ್ಷಿಣಾಯನ', sa: 'दक्षिणायन' },
};

const MASA_I18N = {
  Chaitra: { kn: 'ಚೈತ್ರ', sa: 'चैत्र' },
  Vaishakha: { kn: 'ವೈಶಾಖ', sa: 'वैशाख' },
  Jyeshtha: { kn: 'ಜ್ಯೇಷ್ಠ', sa: 'ज्येष्ठ' },
  Ashadha: { kn: 'ಆಷಾಢ', sa: 'आषाढ' },
  Shravana: { kn: 'ಶ್ರಾವಣ', sa: 'श्रावण' },
  Bhadrapada: { kn: 'ಭಾದ್ರಪದ', sa: 'भाद्रपद' },
  Ashvina: { kn: 'ಆಶ್ವಿನ', sa: 'आश्विन' },
  Ashwayuja: { kn: 'ಆಶ್ವಯುಜ', sa: 'आश्वयुज' },
  Ashwin: { kn: 'ಆಶ್ವಿನ', sa: 'आश्विन' },
  Kartika: { kn: 'ಕಾರ್ತಿಕ', sa: 'कार्तिक' },
  Margashira: { kn: 'ಮಾರ್ಗಶಿರ', sa: 'मार्गशीर्ष' },
  Margashirsha: { kn: 'ಮಾರ್ಗಶಿರ್ಷ', sa: 'मार्गशीर्ष' },
  Pushya: { kn: 'ಪುಷ್ಯ', sa: 'पुष्य' },
  Pausha: { kn: 'ಪೌಷ', sa: 'पौष' },
  Magha: { kn: 'ಮಾಘ', sa: 'माघ' },
  Phalguna: { kn: 'ಫಾಲ್ಗುಣ', sa: 'फाल्गुन' },
  Phalguni: { kn: 'ಫಾಲ್ಗುಣಿ', sa: 'फाल्गुनी' },
};

const SAMVATSARA_I18N = {
  Prabhava: { kn: 'ಪ್ರಭವ', sa: 'प्रभव' },
  Vibhava: { kn: 'ವಿಭವ', sa: 'विभव' },
  Shukla: { kn: 'ಶುಕ್ಲ', sa: 'शुक्ल' },
  Pramoda: { kn: 'ಪ್ರಮೋದ', sa: 'प्रमोद' },
  Prajapati: { kn: 'ಪ್ರಜಾಪತಿ', sa: 'प्रजापति' },
  Angirasa: { kn: 'ಅಂಗಿರಸ', sa: 'अङ्गिरस' },
  Shrimukha: { kn: 'ಶ್ರೀಮುಖ', sa: 'श्रीमुख' },
  Bhava: { kn: 'ಭವ', sa: 'भव' },
  Yuvan: { kn: 'ಯುವ', sa: 'युवन्' },
  Dhatri: { kn: 'ಧಾತೃ', sa: 'धातृ' },
  Ishvara: { kn: 'ಈಶ್ವರ', sa: 'ईश्वर' },
  Bahudhanya: { kn: 'ಬಹುಧಾನ್ಯ', sa: 'बहुधान्य' },
  Pramathi: { kn: 'ಪ್ರಮಾಥಿ', sa: 'प्रमाथि' },
  Vikrama: { kn: 'ವಿಕ್ರಮ', sa: 'विक्रम' },
  Vrisha: { kn: 'ವೃಷ', sa: 'वृष' },
  Chitrabhanu: { kn: 'ಚಿತ್ರಭಾನು', sa: 'चित्रभानु' },
  Svabhanu: { kn: 'ಸ್ವಭಾನು', sa: 'स्वभानु' },
  Tarana: { kn: 'ತರಣ', sa: 'तरण' },
  Parthiva: { kn: 'ಪಾರ್ಥಿವ', sa: 'पार्थिव' },
  Vyaya: { kn: 'ವ್ಯಯ', sa: 'व्यय' },
  Sarvajit: { kn: 'ಸರ್ವಜಿತ್', sa: 'सर्वजित्' },
  Sarvadharin: { kn: 'ಸರ್ವಧಾರಿ', sa: 'सर्वधारिन्' },
  Virodhin: { kn: 'ವಿರೋಧಿ', sa: 'विरोधिन्' },
  Vikrita: { kn: 'ವಿಕೃತ', sa: 'विकृत' },
  Khara: { kn: 'ಖರ', sa: 'खर' },
  Nandana: { kn: 'ನಂದನ', sa: 'नन्दन' },
  Vijaya: { kn: 'ವಿಜಯ', sa: 'विजय' },
  Jaya: { kn: 'ಜಯ', sa: 'जय' },
  Manmatha: { kn: 'ಮನ್ಮಥ', sa: 'मन्मथ' },
  Durmukha: { kn: 'ದುರ್ಮುಖ', sa: 'दुर्मुख' },
  Hemalamba: { kn: 'ಹೇಮಲಂಬ', sa: 'हेमलम्ब' },
  Vilamba: { kn: 'ವಿಲಂಬ', sa: 'विलम्ब' },
  Vikarin: { kn: 'ವಿಕಾರಿ', sa: 'विकारिन्' },
  Sharvari: { kn: 'ಶರ್ವರಿ', sa: 'शर्वरी' },
  Plava: { kn: 'ಪ್ಲವ', sa: 'प्लव' },
  Shubhakrit: { kn: 'ಶುಭಕೃತ್', sa: 'शुभकृत्' },
  Shobhana: { kn: 'ಶೋಭನ', sa: 'शोभन' },
  Krodhin: { kn: 'ಕ್ರೋಧಿ', sa: 'क्रोधिन्' },
  Vishvavasu: { kn: 'ವಿಶ್ವಾವಸು', sa: 'विश्वावसु' },
  Parabhava: { kn: 'ಪರಾಭವ', sa: 'पराभव' },
  Plavanga: { kn: 'ಪ್ಲವಂಗ', sa: 'प्लवङ्ग' },
  Kilaka: { kn: 'ಕೀಲಕ', sa: 'कीलक' },
  Saumya: { kn: 'ಸೌಮ್ಯ', sa: 'सौम्य' },
  Sadharana: { kn: 'ಸಾಧಾರಣ', sa: 'साधारण' },
  Virodhikrit: { kn: 'ವಿರೋಧಿಕೃತ್', sa: 'विरोधिकृत्' },
  Paridhavi: { kn: 'ಪರಿಧಾವಿ', sa: 'परिधाविन्' },
  Pramadin: { kn: 'ಪ್ರಮಾದಿ', sa: 'प्रमादिन्' },
  Ananda: { kn: 'ಆನಂದ', sa: 'आनन्द' },
  Rakshasa: { kn: 'ರಾಕ್ಷಸ', sa: 'राक्षस' },
  Nala: { kn: 'ನಳ', sa: 'नल' },
  Pingala: { kn: 'ಪಿಂಗಲ', sa: 'पिङ्गल' },
  Kalayukta: { kn: 'ಕಾಲಯುಕ್ತ', sa: 'कालयुक्त' },
  Siddharthi: { kn: 'ಸಿದ್ಧಾರ್ಥಿ', sa: 'सिद्धार्थिन्' },
  Raudra: { kn: 'ರೌದ್ರ', sa: 'रौद्र' },
  Durmathi: { kn: 'ದುರ್ಮತಿ', sa: 'दुर्मति' },
  Dundubhi: { kn: 'ದುಂದುಭಿ', sa: 'दुन्दुभि' },
  Rudhirodgari: { kn: 'ರುಧಿರೋದ್ಗಾರಿ', sa: 'रुधिरोद्गारिन्' },
  Raktaksha: { kn: 'ರಕ್ತಾಕ್ಷ', sa: 'रक्ताक्ष' },
  Krodhana: { kn: 'ಕ್ರೋಧನ', sa: 'क्रोधन' },
  Kshaya: { kn: 'ಕ್ಷಯ', sa: 'क्षय' },
};

function tri(en, map) {
  if (!en) return '—';
  const hit = map[en] || map[String(en).trim()];
  if (!hit) return en;
  return `${en} | ${hit.kn} | ${hit.sa}`;
}

function formatClock(value) {
  if (!value || value === 'N/A') return '—';
  if (typeof value === 'string' && (value.includes('AM') || value.includes('PM'))) {
    return value;
  }
  if (typeof value === 'string' && /^\d{1,2}:\d{2}(:\d{2})?$/.test(value)) {
    const [hRaw, m] = value.split(':');
    let h = parseInt(hRaw, 10);
    const period = h >= 12 ? 'PM' : 'AM';
    const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${display}:${m} ${period}`;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function timeRange(block) {
  if (!block || typeof block !== 'object') return '—';
  if (Array.isArray(block) && block.length) {
    return block
      .map((item) => timeRange(item))
      .filter((item) => item && item !== '—')
      .join(', ') || '—';
  }
  const start = formatClock(block.start || block.start_time || block.start_datetime);
  const end = formatClock(block.end || block.end_time || block.end_datetime);
  if (start !== '—' && end !== '—') return `${start} – ${end}`;
  return start !== '—' ? start : end;
}

function line(label, value) {
  if (!value || value === '—') return null;
  return `${label}: ${value}`;
}

/**
 * Build a vertical WhatsApp-friendly Panchang message from API day payload.
 * @param {object} data Panchang API response for one day
 * @returns {string}
 */
export function formatPanchangWhatsAppMessage(data) {
  if (!data) return '';

  const gregorian = data.date?.gregorian || {};
  const hindu = data.date?.hindu || {};
  const location = data.location || {};
  const panchang = data.panchang || {};
  const tithi = panchang.tithi || {};
  const nakshatra = panchang.nakshatra || {};
  const yoga = panchang.yoga || {};
  const karana = panchang.karana || {};
  const vara = panchang.vara || {};
  const kaala = data.inauspicious_times || data.kaala || {};
  const good = data.auspicious_times || data.muhurat || {};
  const extraBad = data.additional_inauspicious_times || {};
  const samvatsaraName = hindu.samvatsara_name || data.samvatsara?.name || hindu.samvatsara?.name || '';
  const masaName = hindu.month || hindu.lunar_month || hindu.lunar_month_purnimanta || '';
  const ayanaName = typeof data.ayana === 'string' ? data.ayana : data.ayana?.name || '';
  const varaName = vara.name || gregorian.day || gregorian.day_of_week || '';
  const tithiName = tithi.name || '';
  const paksha = tithi.paksha || hindu.paksha || '';
  const tithiTri = tithiName
    ? `${paksha ? `${paksha} ` : ''}${tithiName} | ${paksha ? `${(PAKSHA_I18N[paksha]?.kn || paksha)} ` : ''}${TITHI_I18N[tithiName]?.kn || tithiName} | ${paksha ? `${(PAKSHA_I18N[paksha]?.sa || paksha)} ` : ''}${TITHI_I18N[tithiName]?.sa || tithiName}`
    : '—';
  const karanaName = karana.current || karana.name || '';

  const dateLabel = gregorian.formatted
    || (gregorian.date
      ? new Date(`${gregorian.date}T12:00:00`).toLocaleDateString('en-IN', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
      : 'Today');

  const vishesha = [];
  (data.south_india_special || []).forEach((item) => {
    if (item?.english || item?.text) {
      vishesha.push(item.text || `${item.english} | ${item.kannada || ''} | ${item.sanskrit || ''}`.trim());
    }
  });
  (data.festivals || []).forEach((fest) => {
    const name = fest?.name || fest?.title;
    if (!name) return;
    const already = vishesha.some((row) => String(row).toLowerCase().includes(String(name).toLowerCase()));
    if (!already) vishesha.push(name);
  });
  if (data.special_notes?.summary) {
    vishesha.push(data.special_notes.summary);
  }

  const sections = [
    '🙏 *Today\'s Panchang* | ಇಂದಿನ ಪಂಚಾಂಗ',
    `📍 ${location.city || 'Temple'} · ${dateLabel}`,
    '',
    line('Samvatsara', tri(samvatsaraName, SAMVATSARA_I18N)),
    line('Ayana', tri(ayanaName, AYANA_I18N)),
    line('Masa', tri(masaName, MASA_I18N)),
    line('Vara', vara.sanskrit ? `${varaName} | ${VARA_I18N[varaName]?.kn || varaName} | ${vara.sanskrit}` : tri(varaName, VARA_I18N)),
    '',
    line('Tithi', tithiTri + (tithi.end_time_formatted ? ` (till ${tithi.end_time_formatted})` : '')),
    line('Nakshatra', `${tri(nakshatra.name, NAKSHATRA_I18N)}${nakshatra.pada ? ` · Pada ${nakshatra.pada}` : ''}${nakshatra.end_time_formatted ? ` (till ${nakshatra.end_time_formatted})` : ''}`),
    line('Yoga', `${tri(yoga.name, YOGA_I18N)}${yoga.end_time_formatted ? ` (till ${yoga.end_time_formatted})` : ''}`),
    line('Karana', `${tri(karanaName, KARANA_I18N)}${karana.end_time_formatted ? ` (till ${karana.end_time_formatted})` : ''}`),
    '',
    '*Inauspicious*',
    line('Rahu Kala', timeRange(kaala.rahu_kaal || kaala.rahu)),
    line('Yamaganda', timeRange(kaala.yamaganda)),
    line('Gulika Kala', timeRange(kaala.gulika)),
    line('Dur Muhurta', timeRange(extraBad.dur_muhurta)),
    line('Varjyam', timeRange(extraBad.varjyam)),
    '',
    '*Auspicious*',
    line('Abhijit', timeRange(good.abhijit_muhurat || good.abhijit)),
    line('Brahma Muhurat', timeRange(good.brahma_muhurat || good.brahma)),
    line('Amrita Kalam', timeRange(good.amrita_kalam || kaala.amrita)),
  ].filter(Boolean);

  if (vishesha.length) {
    sections.push('', '*Vara Vishesha*');
    vishesha.slice(0, 4).forEach((item) => sections.push(`• ${item}`));
  }

  sections.push(
    '',
    '_Generated by MandirMitra · SanMitra Tech_',
    '_For guidance only — confirm with temple tradition before muhurta use._',
  );

  return sections.join('\n');
}

export function buildWhatsAppShareUrl(message) {
  return `https://wa.me/?text=${encodeURIComponent(message || '')}`;
}
