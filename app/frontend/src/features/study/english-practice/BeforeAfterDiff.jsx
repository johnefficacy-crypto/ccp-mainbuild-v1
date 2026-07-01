/**
 * Word-level before/after diff for English practice rewrites.
 *
 * @param {Object} props
 * @param {string} props.before - The previous answer.
 * @param {string} props.after - The rewritten answer.
 * @returns {JSX.Element}
 */
export default function BeforeAfterDiff({ before, after }) {
  const beforeTokens = tokenize(before);
  const afterTokens = tokenize(after);
  const lcs = longestCommonSubsequence(beforeTokens, afterTokens);

  const removedFlags = markKept(beforeTokens, lcs);
  const addedFlags = markKept(afterTokens, lcs);

  return (
    <div
      data-testid="before-after-diff"
      className="grid gap-3 sm:grid-cols-2"
    >
      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Previous
        </div>
        <p className="text-sm leading-relaxed text-slate-700">
          {beforeTokens.map((word, i) => (
            <span
              key={`b-${i}`}
              className={removedFlags[i] ? undefined : "line-through text-rose-600"}
            >
              {word}
              {i < beforeTokens.length - 1 ? " " : ""}
            </span>
          ))}
        </p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Rewrite
        </div>
        <p className="text-sm leading-relaxed text-slate-700">
          {afterTokens.map((word, i) => (
            <span
              key={`a-${i}`}
              className={
                addedFlags[i]
                  ? undefined
                  : "bg-emerald-100 text-emerald-800 rounded px-0.5"
              }
            >
              {word}
              {i < afterTokens.length - 1 ? " " : ""}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}

/**
 * Split a string into non-empty whitespace-delimited tokens.
 * @param {string} value
 * @returns {string[]}
 */
function tokenize(value) {
  return (value || "").split(/\s+/).filter(Boolean);
}

/**
 * Compute the longest common subsequence of two token arrays.
 * @param {string[]} a
 * @param {string[]} b
 * @returns {string[]}
 */
function longestCommonSubsequence(a, b) {
  const n = a.length;
  const m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      if (a[i] === b[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }
  const result = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      result.push(a[i]);
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      i += 1;
    } else {
      j += 1;
    }
  }
  return result;
}

/**
 * Flag which tokens are part of the common subsequence (kept/unchanged).
 * @param {string[]} tokens
 * @param {string[]} lcs
 * @returns {boolean[]} true where token is unchanged
 */
function markKept(tokens, lcs) {
  const flags = new Array(tokens.length).fill(false);
  let k = 0;
  for (let i = 0; i < tokens.length; i += 1) {
    if (k < lcs.length && tokens[i] === lcs[k]) {
      flags[i] = true;
      k += 1;
    }
  }
  return flags;
}
