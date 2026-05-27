export const ACCURACY_STOPS = [
  { min: 0, max: 39, color: 'var(--color-danger, #b91c1c)', label: 'Low' },
  { min: 40, max: 69, color: 'var(--color-warning, #b45309)', label: 'Medium' },
  { min: 70, max: 100, color: 'var(--color-success, #166534)', label: 'High' },
];

export function accuracyColor(value = 0) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  return ACCURACY_STOPS.find((s) => v >= s.min && v <= s.max)?.color ?? ACCURACY_STOPS[0].color;
}

export function masteryTone(value = 0) {
  if (value >= 70) return 'var(--color-success, #166534)';
  if (value >= 40) return 'var(--color-warning, #b45309)';
  return 'var(--color-danger, #b91c1c)';
}
