import React from "react";
import { hasPlaceholder } from "../utils/placeholders";

export default function SuggestionCard({ suggestions, onSelect, disabled = false }) {
  if (!Array.isArray(suggestions) || suggestions.length === 0) return null;

  // Normalize: accept both string[] and {text: string}[]
  const items = suggestions
    .map((s) => (typeof s === "string" ? s : s?.text || ""))
    .filter((t) => t.trim().length > 0);

  if (items.length === 0) return null;

  return (
    <div className="ml-10 mt-2 rounded-xl border border-slate-200 bg-white p-3">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Suggested Next Steps
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((text, index) => (
          <button
            key={`${text}-${index}`}
            type="button"
            disabled={disabled}
            onClick={() => onSelect?.(text)}
            title={hasPlaceholder(text) ? "Fill in the [bracketed] parts before sending" : undefined}
            className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {hasPlaceholder(text) && (
              <svg className="h-3 w-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536M9 13l6.232-6.232a2.5 2.5 0 113.536 3.536L12.536 16.5H9V13z" />
              </svg>
            )}
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
