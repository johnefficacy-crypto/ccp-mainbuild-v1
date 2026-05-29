import { useEffect } from 'react';

export default function useCopyPasteSuppression({ ref, blockCopy, blockPaste, blockContextMenu, onViolation }) {
  useEffect(() => {
    const node = ref?.current;
    if (!node) return undefined;

    const handle = (eventName, type) => (e) => {
      e.preventDefault();
      onViolation?.(type, { eventName });
    };

    const handlers = [];
    if (blockCopy) handlers.push(['copy', handle('copy', 'copy_blocked')]);
    if (blockPaste) handlers.push(['paste', handle('paste', 'paste_blocked')]);
    if (blockContextMenu) handlers.push(['contextmenu', handle('contextmenu', 'context_menu_blocked')]);

    handlers.forEach(([evt, fn]) => node.addEventListener(evt, fn));
    return () => handlers.forEach(([evt, fn]) => node.removeEventListener(evt, fn));
  }, [ref, blockCopy, blockPaste, blockContextMenu, onViolation]);
}
