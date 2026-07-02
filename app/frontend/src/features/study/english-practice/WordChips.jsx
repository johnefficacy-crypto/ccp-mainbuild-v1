import React, { useMemo } from "react";
import { normalizeToken, usedRequiredWords } from "./requiredWords";

/**
 * Required-word chips with used-state styling and a `words_used: N/total`
 * counter (EWP-3 required-word exercise contract). Live, compose-time only —
 * the authoritative coverage verdict is the server check (§4.7a).
 *
 * @param {object} props
 * @param {string[]} props.requiredWords - the prompt's required words.
 * @param {string} props.text - the current draft text.
 * @returns {JSX.Element|null}
 */
export default function WordChips({ requiredWords, text }) {
  const words = useMemo(
    () => (Array.isArray(requiredWords) ? requiredWords : []),
    [requiredWords],
  );
  const usedSet = useMemo(() => {
    const used = usedRequiredWords(text, words);
    return new Set(used.map(normalizeToken));
  }, [text, words]);

  if (words.length === 0) return null;

  return (
    <div className="mt-2" data-testid="word-chips">
      <div className="flex flex-wrap items-center gap-1.5">
        {words.map((word) => {
          const isUsed = usedSet.has(normalizeToken(word));
          return (
            <span
              key={word}
              data-testid={`word-chip${isUsed ? "-used" : ""}`}
              aria-label={`${word}${isUsed ? " (used)" : " (not yet used)"}`}
              className={
                isUsed
                  ? "rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 line-through"
                  : "rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
              }
            >
              {word}
            </span>
          );
        })}
      </div>
      <p className="mt-1 text-xs text-slate-500" data-testid="words-used">
        words used: {usedSet.size}/{words.length}
      </p>
    </div>
  );
}
