import { describe, it, expect } from 'vitest';
import { detectLeadingOrdinal, stripLeadingOrdinal, cleanWhitespace } from './ordinal';

describe('detectLeadingOrdinal', () => {
  it('detects period separator', () => {
    expect(detectLeadingOrdinal('1. What is the capital?')).toBe(1);
  });

  it('detects paren separator', () => {
    expect(detectLeadingOrdinal('2) Which of the following?')).toBe(2);
  });

  it('detects colon separator', () => {
    expect(detectLeadingOrdinal('3: Consider the statement')).toBe(3);
  });

  it('detects space separator', () => {
    expect(detectLeadingOrdinal('4 Who was the first?')).toBe(4);
  });

  it('handles leading whitespace', () => {
    expect(detectLeadingOrdinal('  5. With leading spaces')).toBe(5);
  });

  it('returns null when no ordinal', () => {
    expect(detectLeadingOrdinal('Which of the following is correct?')).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(detectLeadingOrdinal('')).toBeNull();
  });

  it('detects multi-digit ordinals', () => {
    expect(detectLeadingOrdinal('25. What happened?')).toBe(25);
  });
});

describe('stripLeadingOrdinal', () => {
  it('strips period separator', () => {
    expect(stripLeadingOrdinal('1. What is the capital?')).toBe('What is the capital?');
  });

  it('strips paren separator', () => {
    expect(stripLeadingOrdinal('2) Which of the following?')).toBe('Which of the following?');
  });

  it('is a no-op when no ordinal', () => {
    expect(stripLeadingOrdinal('Which of the following?')).toBe('Which of the following?');
  });

  it('strips leading whitespace before ordinal', () => {
    expect(stripLeadingOrdinal('  3. Some question')).toBe('Some question');
  });

  it('strips trailing whitespace after separator', () => {
    expect(stripLeadingOrdinal('4.   Extra spaces after')).toBe('Extra spaces after');
  });
});

describe('cleanWhitespace', () => {
  it('collapses multiple spaces into one', () => {
    expect(cleanWhitespace('Hello   world')).toBe('Hello world');
  });

  it('collapses tabs into a single space', () => {
    expect(cleanWhitespace('Hello\t\tworld')).toBe('Hello world');
  });

  it('trims leading and trailing whitespace', () => {
    expect(cleanWhitespace('  hello world  ')).toBe('hello world');
  });

  it('collapses mixed spaces and tabs', () => {
    expect(cleanWhitespace('a \t b')).toBe('a b');
  });

  it('is a no-op for already clean text', () => {
    expect(cleanWhitespace('clean text')).toBe('clean text');
  });
});
