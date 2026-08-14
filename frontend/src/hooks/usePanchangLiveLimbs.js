import { useEffect, useRef, useState } from 'react';
import {
  formatCountdown,
  formatTransitionTime,
  getNextTithiName,
  isPanchangLimbEnded,
  localISODate,
  parsePanchangDateTime,
  resolveLivePanchangLimbs,
} from '../utils/panchangTime';

export default function usePanchangLiveLimbs({ data, compact = false, selectedDate, onLimbExpired }) {
  const [timeLeft, setTimeLeft] = useState({});
  const refreshRequestedRef = useRef(false);
  const isLiveToday = !selectedDate || selectedDate === localISODate();
  const liveLimbs = resolveLivePanchangLimbs(data, { isLiveToday });

  useEffect(() => {
    if (!data || compact) return undefined;

    const updateCountdown = () => {
      const now = new Date();
      const calculations = {};
      let limbExpired = false;

      if (data.panchang?.tithi?.end_time) {
        const tithi = data.panchang.tithi;
        const tithiEnd = parsePanchangDateTime(tithi.end_time);
        const diff = tithiEnd ? tithiEnd - now : 0;
        const endTime = formatTransitionTime(tithi.end_time, tithi.end_time_formatted);
        const nextTithi = getNextTithiName(tithi);

        if (tithiEnd && diff > 0) {
          calculations.tithi = `Ends ${endTime} -> ${nextTithi} (${formatCountdown(diff)})`;
          calculations.tithiEnded = false;
        } else {
          calculations.tithi = `Changed ${endTime}; ${nextTithi} active now`;
          calculations.tithiEnded = true;
          if (isLiveToday) limbExpired = true;
        }
      }

      if (data.panchang?.nakshatra?.end_time) {
        const nakshatra = data.panchang.nakshatra;
        const nakshatraEnd = parsePanchangDateTime(nakshatra.end_time);
        const diff = nakshatraEnd ? nakshatraEnd - now : 0;
        const endTime = formatTransitionTime(nakshatra.end_time, nakshatra.end_time_formatted);
        const nextNakshatra = nakshatra.next_nakshatra || 'next nakshatra';

        if (nakshatraEnd && diff > 0) {
          calculations.nakshatra = `Ends ${endTime} -> ${nextNakshatra} (${formatCountdown(diff)})`;
          calculations.nakshatraEnded = false;
        } else {
          calculations.nakshatra = `Changed ${endTime} -> ${nextNakshatra} now`;
          calculations.nakshatraEnded = true;
          if (isLiveToday) limbExpired = true;
        }
      }

      setTimeLeft(calculations);

      if (limbExpired && onLimbExpired && !refreshRequestedRef.current) {
        refreshRequestedRef.current = true;
        onLimbExpired();
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [data, compact, isLiveToday, onLimbExpired]);

  useEffect(() => {
    const nakEnded = isPanchangLimbEnded(data?.panchang?.nakshatra?.end_time);
    const tithiEnded = isPanchangLimbEnded(data?.panchang?.tithi?.end_time);
    if (isLiveToday && (nakEnded || tithiEnded)) {
      return;
    }
    refreshRequestedRef.current = false;
  }, [
    isLiveToday,
    data?.calculation_metadata?.generated_at,
    data?.panchang?.nakshatra?.name,
    data?.panchang?.nakshatra?.end_time,
    data?.panchang?.tithi?.full_name,
    data?.panchang?.tithi?.end_time,
  ]);

  return { timeLeft, isLiveToday, ...liveLimbs };
}
