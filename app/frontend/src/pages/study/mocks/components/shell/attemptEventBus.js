const noop = () => {};

function getGlobalBus() {
  if (typeof window === 'undefined') return null;
  return window.__attemptEventBus || null;
}

export function emitAttemptEvent(type, payload = {}) {
  const bus = getGlobalBus();
  if (!bus) return;
  if (typeof bus.emit === 'function') {
    bus.emit(type, payload);
    return;
  }
  if (typeof bus.enqueue === 'function') {
    bus.enqueue({ type, payload, ts: Date.now() });
  }
}

export const attemptEventBus = {
  emit: emitAttemptEvent,
  enqueue: noop,
};
