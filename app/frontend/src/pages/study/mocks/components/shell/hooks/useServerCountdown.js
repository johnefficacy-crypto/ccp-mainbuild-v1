import { useEffect, useMemo, useRef, useState } from 'react';
import { emitAttemptEvent } from '../attemptEventBus';

const tickMs = 1000;

export default function useServerCountdown(expiresAt) {
  const expiresMs = useMemo(() => Date.parse(expiresAt || ''), [expiresAt]);
  const [remainingSec, setRemainingSec] = useState(() => {
    if (!Number.isFinite(expiresMs)) return 0;
    return Math.max(0, Math.ceil((expiresMs - Date.now()) / 1000));
  });
  const driftRef = useRef(false);

  useEffect(() => {
    if (!Number.isFinite(expiresMs)) {
      setRemainingSec(0);
      return undefined;
    }

    let timerId;
    let lastTick = Date.now();

    const compute = () => {
      const now = Date.now();
      const jumpedMs = now - lastTick;
      if (jumpedMs > tickMs + 2000 && !driftRef.current) {
        driftRef.current = true;
        emitAttemptEvent('attempt.timer_drift', { jumpedMs });
      }
      lastTick = now;
      setRemainingSec(Math.max(0, Math.ceil((expiresMs - now) / 1000)));
    };

    compute();
    timerId = setInterval(compute, tickMs);
    return () => clearInterval(timerId);
  }, [expiresMs]);

  return remainingSec;
}
