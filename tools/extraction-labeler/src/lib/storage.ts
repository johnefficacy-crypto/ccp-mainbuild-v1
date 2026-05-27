import type { SessionState } from '../types';

const PREFIX = 'labeler:session:';

function key(documentId: string): string {
  return PREFIX + (documentId.trim() || '__unsaved__');
}

export function saveSession(state: SessionState): void {
  try {
    localStorage.setItem(key(state.documentId), JSON.stringify(state));
  } catch {
    // Ignore quota errors
  }
}

export function loadSession(documentId: string): SessionState | null {
  try {
    const raw = localStorage.getItem(key(documentId));
    if (!raw) return null;
    return JSON.parse(raw) as SessionState;
  } catch {
    return null;
  }
}

export function clearSession(documentId: string): void {
  try {
    localStorage.removeItem(key(documentId));
  } catch {
    // Ignore
  }
}
