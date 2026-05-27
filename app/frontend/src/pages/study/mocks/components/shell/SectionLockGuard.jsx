import React from 'react';
export default function SectionLockGuard({ locked, children, onBlocked }) {
  if (!locked) return children;
  return <div aria-label="Section locked" onClick={(e)=>{e.preventDefault(); onBlocked?.();}}>{children}</div>;
}
