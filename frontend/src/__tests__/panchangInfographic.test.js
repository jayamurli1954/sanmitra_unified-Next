import {
  buildPanchangInfographicModel,
  panchangInfographicFileName,
} from '../utils/panchangInfographic';
import { limbEndLabel, masaParts } from '../utils/panchangWhatsAppMessage';

describe('panchangInfographic model', () => {
  const sample = {
    date: {
      gregorian: { date: '2026-11-10', day: 'Tuesday', formatted: 'Tuesday, 10 November, 2026' },
      hindu: { month: 'Kartika', paksha: 'Shukla', samvatsara_name: 'Parabhava' },
    },
    location: { city: 'Bengaluru' },
    ayana: 'Dakshinayana',
    sun_moon: { sunrise: '06:17:47', sunset: '17:51:10' },
    panchang: {
      tithi: {
        name: 'Dwitiya',
        paksha: 'Shukla',
        end_time: '2026-11-11 15:53:20',
        end_time_formatted: '03:53 PM',
      },
      nakshatra: {
        name: 'Anuradha',
        pada: 2,
        end_time: '2026-11-10 21:10:00',
        end_time_formatted: '09:10 PM',
      },
      yoga: { name: 'Shobhana', end_time: '2026-11-10 18:05:00', end_time_formatted: '06:05 PM' },
      karana: { current: 'Balava', end_time_formatted: '02:00 PM' },
      vara: { name: 'Tuesday', sanskrit: 'मङ्गलवासरः' },
    },
    inauspicious_times: {
      rahu_kaal: { start: '14:58:00', end: '16:24:00' },
      yamaganda: { start: '09:11:00', end: '10:38:00' },
      gulika: { start: '12:04:00', end: '13:31:00' },
    },
    additional_inauspicious_times: {
      dur_muhurta: [{ start: '08:36:00', end: '09:22:00' }],
    },
    auspicious_times: {
      abhijit_muhurat: { start: '11:41:00', end: '12:27:00' },
      brahma_muhurat: { start: '04:41:00', end: '05:29:00' },
    },
    festivals: [{ name: 'Bali Padyami' }],
    south_india_special: [
      {
        type: 'festival',
        english: 'Bali Padyami (Bali Pratipada)',
        kannada: 'ಬಲಿ ಪಾಡ್ಯಮಿ',
        sanskrit: 'बलिप्रतिपदा',
      },
      { type: 'note', english: 'Some note', kannada: 'x', sanskrit: 'y' },
    ],
  };

  it('puts the day festival on the card in three languages', () => {
    const model = buildPanchangInfographicModel(sample);
    expect(model.festivals).toEqual([
      { en: 'Bali Padyami (Bali Pratipada)', kn: 'ಬಲಿ ಪಾಡ್ಯಮಿ', sa: 'बलिप्रतिपदा' },
    ]);
  });

  it('builds trilingual limb rows', () => {
    const model = buildPanchangInfographicModel(sample);
    const byKey = Object.fromEntries(model.rows.map((row) => [row.key, row]));
    expect(model.rows.map((row) => row.key)).toEqual([
      'samvatsara', 'ayana', 'masa', 'vara', 'tithi', 'nakshatra', 'yoga', 'karana',
    ]);
    expect(byKey.samvatsara.value).toEqual({ en: 'Parabhava', kn: 'ಪರಾಭವ', sa: 'पराभव' });
    expect(byKey.masa.value).toEqual({ en: 'Kartika', kn: 'ಕಾರ್ತಿಕ', sa: 'कार्तिक' });
    expect(byKey.vara.value).toEqual({ en: 'Tuesday', kn: 'ಮಂಗಳವಾರ', sa: 'मङ्गलवासरः' });
    expect(byKey.tithi.value).toEqual({
      en: 'Shukla Dwitiya',
      kn: 'ಶುಕ್ಲ ದ್ವಿತೀಯ',
      sa: 'शुक्ल द्वितीया',
    });
    expect(byKey.nakshatra.value.en).toBe('Anuradha (Pada 2)');
    // Tithi ends tomorrow: the date is shown so it is not read as today.
    expect(byKey.tithi.till).toBe('3:53 PM, 11 Nov');
    expect(byKey.nakshatra.till).toBe('9:10 PM');
  });

  it('lists timings and drops the ones the API did not send', () => {
    const model = buildPanchangInfographicModel(sample);
    expect(model.inauspicious.map((item) => item.label.en)).toEqual([
      'Rahu Kala', 'Yamaganda', 'Gulika Kala', 'Dur Muhurta',
    ]);
    expect(model.inauspicious[0].time).toBe('2:58 PM – 4:24 PM');
    expect(model.auspicious.map((item) => item.label.en)).toEqual([
      'Abhijit Muhurta', 'Brahma Muhurta', 'Sunrise', 'Sunset',
    ]);
    expect(panchangInfographicFileName(model)).toBe('panchang-2026-11-10.png');
  });

  it('handles an Adhika month and same-day limb ends', () => {
    expect(masaParts('Adhika Jyeshtha')).toEqual({
      en: 'Adhika Jyeshtha',
      kn: 'ಅಧಿಕ ಜ್ಯೇಷ್ಠ',
      sa: 'अधिक ज्येष्ठ',
    });
    expect(limbEndLabel({ end_time_formatted: '02:00 PM', end_time: '2026-11-10 14:00:00' }, '2026-11-10'))
      .toBe('2:00 PM');
    expect(buildPanchangInfographicModel(null)).toBeNull();
  });

  it('includes MandirMitra URL and disclaimer in footer model', () => {
    const model = buildPanchangInfographicModel(sample);
    expect(model.footer).toBe('www.mandirmitra.sanmitratech.in');
    expect(model.website).toBe('www.mandirmitra.sanmitratech.in');
    expect(model.disclaimer).toBe('For guidance only — confirm with temple tradition before muhurta use.');
  });
});
