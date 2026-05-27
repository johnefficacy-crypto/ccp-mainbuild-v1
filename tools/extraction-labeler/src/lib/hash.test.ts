import { describe, it, expect } from 'vitest';
import { normalizeQuestionText, sha256Hex } from './hash';

describe('normalizeQuestionText', () => {
  it('strips leading Q. numbering', () => {
    expect(normalizeQuestionText('Q. Which of the following is correct?')).toBe(
      'which of the following is correct?',
    );
  });

  it('strips leading N. numbering', () => {
    expect(normalizeQuestionText('N. What is the capital of India?')).toBe(
      'what is the capital of india?',
    );
  });

  it('collapses whitespace', () => {
    expect(
      normalizeQuestionText('Which  of   the   following  statements?'),
    ).toBe('which of the following statements?');
  });

  it('folds to lowercase', () => {
    expect(normalizeQuestionText('Consider The Following Statement')).toBe(
      'consider the following statement',
    );
  });

  it('preserves internal ? and .', () => {
    const result = normalizeQuestionText(
      'Is statement A correct? Consider: yes or no.',
    );
    expect(result).toContain('?');
    expect(result).toContain('.');
  });

  it('strips commas, colons, parentheses and similar punctuation', () => {
    const result = normalizeQuestionText('Hello, world! (test) [abc]: done');
    expect(result).not.toContain(',');
    expect(result).not.toContain('!');
    expect(result).not.toContain('(');
    expect(result).not.toContain(')');
    expect(result).not.toContain('[');
    expect(result).not.toContain(']');
    expect(result).not.toContain(':');
  });
});

describe('sha256Hex', () => {
  it('returns a 64-character lowercase hex string', async () => {
    const hash = await sha256Hex('test input');
    expect(hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('is deterministic for the same input', async () => {
    const h1 = await sha256Hex('same text');
    const h2 = await sha256Hex('same text');
    expect(h1).toBe(h2);
  });

  it('produces different hashes for different inputs', async () => {
    const h1 = await sha256Hex('text a');
    const h2 = await sha256Hex('text b');
    expect(h1).not.toBe(h2);
  });

  it('matches known SHA-256 of empty string', async () => {
    const hash = await sha256Hex('');
    expect(hash).toBe(
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    );
  });
});
