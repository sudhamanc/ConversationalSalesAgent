import React from "react";

/**
 * Thumbs up / thumbs down on an assistant reply.
 *
 * Shown only for replies whose turn was traced (the `done` event carried a
 * trace id); the vote is recorded as a Langfuse score on that trace.
 *
 * @param {Object} props
 * @param {"up"|"down"|null} [props.value] - The recorded vote, if any.
 * @param {boolean} [props.pending] - True while the vote is being sent.
 * @param {function} props.onVote - Called with "up" or "down".
 */
export default function FeedbackButtons({ value = null, pending = false, onVote }) {
  const handleUp = () => onVote("up");
  const handleDown = () => onVote("down");
  const base =
    "p-1 rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500";

  return (
    <div className="flex items-center gap-1" role="group" aria-label="Rate this reply">
      <button
        type="button"
        onClick={handleUp}
        disabled={pending}
        aria-label="Helpful"
        aria-pressed={value === "up"}
        title="Helpful"
        className={`${base} ${value === "up" ? "text-primary-600 bg-primary-50" : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"}`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill={value === "up" ? "currentColor" : "none"} stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 11v9H4a1 1 0 01-1-1v-7a1 1 0 011-1h3zm0 0l4-8a2 2 0 012 2v4h5.5a2 2 0 011.97 2.35l-1.2 7A2 2 0 0117.3 20H7" />
        </svg>
      </button>
      <button
        type="button"
        onClick={handleDown}
        disabled={pending}
        aria-label="Not helpful"
        aria-pressed={value === "down"}
        title="Not helpful"
        className={`${base} ${value === "down" ? "text-rose-600 bg-rose-50" : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"}`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill={value === "down" ? "currentColor" : "none"} stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 13V4h3a1 1 0 011 1v7a1 1 0 01-1 1h-3zm0 0l-4 8a2 2 0 01-2-2v-4H5.5a2 2 0 01-1.97-2.35l1.2-7A2 2 0 016.7 4H17" />
        </svg>
      </button>
    </div>
  );
}
