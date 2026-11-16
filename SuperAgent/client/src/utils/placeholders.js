// Fill-in suggestion templates use [bracketed placeholders], e.g.
// "You can reach me at [email] or [phone]". The input selects each one in turn
// and blocks sending until none remain.

const PLACEHOLDER_RE = /\[[^[\]]+\]/g;

/** Next placeholder at or after `from` (wrapping to the start), as {start, end}, or null. */
export function findPlaceholder(text, from = 0) {
  if (!text) return null;
  const matches = [...text.matchAll(PLACEHOLDER_RE)];
  if (matches.length === 0) return null;
  const next = matches.find((m) => m.index >= from) || matches[0];
  return { start: next.index, end: next.index + next[0].length };
}

export function hasPlaceholder(text) {
  return findPlaceholder(text) !== null;
}
