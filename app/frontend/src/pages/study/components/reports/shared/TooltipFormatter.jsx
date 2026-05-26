export function formatPct(value) {
  return `${Math.round(Number(value) || 0)}%`;
}

export function formatTimeSeconds(seconds) {
  const s = Number(seconds) || 0;
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${m}m ${r}s`;
}
