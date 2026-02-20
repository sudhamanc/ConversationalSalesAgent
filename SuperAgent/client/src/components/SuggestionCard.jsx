import React from "react";

export default function SuggestionCard({ suggestions, onSelect, disabled = false }) {
  if (!Array.isArray(suggestions) || suggestions.length === 0) return null;

  return (
    <div className="ml-10 mt-2 rounded-xl border border-slate-200 bg-white p-3">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Suggested Next Steps
      </p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <button
            key={`${suggestion.text}-${index}`}
            type="button"
            disabled={disabled}
            onClick={() => onSelect?.(suggestion.text)}
            className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {suggestion.text}
          </button>
        ))}
      </div>
    </div>
  );
}
