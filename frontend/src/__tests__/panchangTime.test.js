import { liveLimbName, localISODate, parsePanchangDateTime } from '../utils/panchangTime';

describe('panchangTime', () => {
  it('formats the local civil date without using UTC', () => {
    const date = new Date(2026, 7, 14, 10, 0, 0);
    expect(localISODate(date)).toBe('2026-08-14');
  });

  it('parses naive backend timestamps as Asia/Kolkata', () => {
    const parsed = parsePanchangDateTime('2026-08-14 04:38:00');
    expect(parsed).toBeInstanceOf(Date);
    expect(parsed.toISOString()).toBe('2026-08-13T23:08:00.000Z');
  });

  it('switches to the next nakshatra after the end time on today\'s view', () => {
    const limb = {
      name: 'Magha',
      end_time: '2026-08-14 04:38:00',
      next_nakshatra: 'Purva Phalguni',
    };
    const now = new Date('2026-08-14T04:30:00+05:30');
    expect(liveLimbName(limb, limb.next_nakshatra, { isLiveToday: true, now })).toBe('Magha');

    const later = new Date('2026-08-14T10:00:00+05:30');
    expect(liveLimbName(limb, limb.next_nakshatra, { isLiveToday: true, now: later })).toBe('Purva Phalguni');
    expect(liveLimbName(limb, limb.next_nakshatra, { isLiveToday: false, now: later })).toBe('Magha');
  });
});
