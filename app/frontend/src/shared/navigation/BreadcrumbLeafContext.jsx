import React, { createContext, useContext, useEffect, useState } from "react";

const BreadcrumbLeafContext = createContext(null);

export function BreadcrumbLeafProvider({ children }) {
  const [leaf, setLeaf] = useState(null);
  return (
    <BreadcrumbLeafContext.Provider value={{ leaf, setLeaf }}>
      {children}
    </BreadcrumbLeafContext.Provider>
  );
}

/**
 * Call from a child page when its own data is loaded and the leaf label
 * should be the actual name rather than the static fallback.
 * Resets to null on unmount so stale labels don't bleed across routes.
 */
export function useBreadcrumbLeaf(label) {
  const ctx = useContext(BreadcrumbLeafContext);
  useEffect(() => {
    if (!ctx) return;
    ctx.setLeaf(label || null);
    return () => ctx.setLeaf(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [label]);
}

export function useBreadcrumbLeafValue() {
  const ctx = useContext(BreadcrumbLeafContext);
  return ctx?.leaf ?? null;
}
