import { useEffect, useRef, useState } from 'react';

export default function useFullscreen(enabled = false) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [denied, setDenied] = useState(false);
  const requestedRef = useRef(false);

  useEffect(() => {
    if (typeof document === 'undefined') return undefined;

    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', onChange);
    onChange();

    async function requestFs() {
      if (!enabled || requestedRef.current || typeof document.documentElement?.requestFullscreen !== 'function') return;
      requestedRef.current = true;
      try { await document.documentElement.requestFullscreen(); } catch { setDenied(true); }
    }

    requestFs();
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, [enabled]);

  return { isFullscreen, denied };
}
