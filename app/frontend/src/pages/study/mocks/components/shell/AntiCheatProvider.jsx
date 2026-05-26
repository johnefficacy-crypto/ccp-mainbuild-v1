import React, { createContext, useEffect, useMemo, useRef, useState } from 'react';
import useFullscreen from './hooks/useFullscreen';
import useVisibility from './hooks/useVisibility';
import useCopyPasteSuppression from './hooks/useCopyPasteSuppression';

export const AntiCheatContext = createContext({});

export default function AntiCheatProvider({ children, enforceFullscreen=false, blockCopy=false, blockPaste=false, blockContextMenu=false, onViolation }) {
  const areaRef = useRef(null);
  const hidden = useVisibility();
  const { isFullscreen, denied } = useFullscreen(enforceFullscreen);
  const [warn, setWarn] = useState('');
  const fsExitEmitted = useRef(false);

  useCopyPasteSuppression({ ref: areaRef, blockCopy, blockPaste, blockContextMenu, onViolation });

  useEffect(() => { if (hidden) onViolation?.('tab_blurred', { hidden: true }); }, [hidden, onViolation]);
  useEffect(() => {
    if (enforceFullscreen && !isFullscreen && !fsExitEmitted.current) {
      fsExitEmitted.current = true;
      setWarn('Fullscreen exited. Please return to exam mode.');
      onViolation?.('tab_blurred', { fullscreen: false, denied });
    }
  }, [enforceFullscreen, isFullscreen, denied, onViolation]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const onResize = () => {
      const delta = Math.abs(window.outerWidth - window.innerWidth) + Math.abs(window.outerHeight - window.innerHeight);
      if (delta > 320) onViolation?.('devtools_detected', { delta });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [onViolation]);

  const value = useMemo(() => ({ hidden, isFullscreen, denied }), [hidden, isFullscreen, denied]);
  return <AntiCheatContext.Provider value={value}><div ref={areaRef}>{warn && <div aria-label="Anti-cheat warning">{warn}</div>}{children}</div></AntiCheatContext.Provider>;
}
