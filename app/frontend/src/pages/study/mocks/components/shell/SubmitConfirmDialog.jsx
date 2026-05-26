import React, { useEffect, useRef } from 'react';

export default function SubmitConfirmDialog({ open, summary, onConfirm, onCancel }) {
  const dialogRef = useRef(null);
  useEffect(() => { if (open) dialogRef.current?.focus(); }, [open]);
  if (!open) return null;
  return <div role="dialog" aria-modal="true" aria-label="Submit confirmation" onKeyDown={(e)=>{if(e.key==='Escape') onCancel?.();}}>
    <div tabIndex={-1} ref={dialogRef}>
      <p>Total: {summary.total} | Answered: {summary.answered}</p>
      <button aria-label="Cancel submit" onClick={onCancel}>Cancel</button>
      <button aria-label="Confirm submit" onClick={onConfirm} type="button">Submit attempt</button>
    </div>
  </div>;
}
