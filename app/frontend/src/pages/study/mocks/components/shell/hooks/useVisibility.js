import { useEffect, useState } from 'react';

export default function useVisibility() {
  const [isHidden, setIsHidden] = useState(false);
  useEffect(() => {
    if (typeof document === 'undefined') return undefined;
    const onVisibilityChange = () => setIsHidden(document.visibilityState === 'hidden');
    document.addEventListener('visibilitychange', onVisibilityChange);
    onVisibilityChange();
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);
  return isHidden;
}
