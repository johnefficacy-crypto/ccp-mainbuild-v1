import React, { useEffect, useRef } from 'react';
import useServerCountdown from './hooks/useServerCountdown';

export default function SectionTimer({ expiresAt, onExpire, warnThresholds = [300,60,10], onWarn }) {
  const remaining = useServerCountdown(expiresAt);
  const expired = useRef(false);
  const warned = useRef(new Set());
  useEffect(() => { if (remaining <= 0 && !expired.current) { expired.current = true; onExpire?.(); }}, [remaining, onExpire]);
  useEffect(() => { warnThresholds.forEach((t)=>{ if (remaining <= t && !warned.current.has(t)) { warned.current.add(t); onWarn?.(t);} }); }, [remaining, warnThresholds, onWarn]);
  return <div aria-label="Section timer">{remaining}s</div>;
}
