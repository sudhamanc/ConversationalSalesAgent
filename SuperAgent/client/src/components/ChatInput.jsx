import React, { useState, useRef, useEffect } from "react";
import { findPlaceholder, hasPlaceholder } from "../utils/placeholders";

export default function ChatInput({
  onSend,
  disabled,
  onClear,
  hasMessages,
  prefillRequest = null,
}) {
  const [text, setText] = useState("");
  const inputRef = useRef(null);
  const selectAfterPrefill = useRef(false);
  const needsFilling = hasPlaceholder(text);

  // Select the [placeholder] at or after `from` so typing replaces it.
  const selectPlaceholder = (value, from = 0) => {
    const input = inputRef.current;
    if (!input) return false;
    const range = findPlaceholder(value, from);
    input.focus();
    if (!range) return false;
    input.setSelectionRange(range.start, range.end);
    return true;
  };

  useEffect(() => {
    const textToPrefill = prefillRequest?.text;
    if (!textToPrefill) return;
    selectAfterPrefill.current = true;
    setText(textToPrefill);
  }, [prefillRequest]);

  useEffect(() => {
    if (!selectAfterPrefill.current) return;
    selectAfterPrefill.current = false;
    if (!selectPlaceholder(text)) {
      inputRef.current?.setSelectionRange(text.length, text.length);
    }
  }, [text]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    if (needsFilling) {
      selectPlaceholder(text, inputRef.current?.selectionEnd ?? 0);
      return;
    }
    onSend(text);
    setText("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    // Tab / Enter move through unfilled [placeholders] of a suggestion template.
    if (needsFilling && (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey))) {
      e.preventDefault();
      selectPlaceholder(text, e.currentTarget.selectionEnd);
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-slate-200 px-4 py-3 bg-white"
    >
      <div className="flex items-end gap-2">
        {/* Clear button */}
        {hasMessages && (
          <button
            type="button"
            onClick={onClear}
            className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
            title="Clear chat"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        )}

        {/* Text input */}
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2.5 text-sm
                     focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed
                     placeholder:text-slate-400 max-h-[120px]"
        />

        {/* Send button */}
        <button
          type="submit"
          disabled={disabled || !text.trim() || needsFilling}
          className="p-2.5 rounded-xl bg-primary-600 text-white hover:bg-primary-700
                     disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 19V5m0 0l-7 7m7-7l7 7"
            />
          </svg>
        </button>
      </div>
      {needsFilling ? (
        <p className="text-xs text-amber-600 mt-1.5 text-center">
          Fill in the [bracketed] parts &middot; Tab moves to the next one
        </p>
      ) : (
        <p className="text-xs text-slate-400 mt-1.5 text-center">
          Press Enter to send &middot; Shift+Enter for new line
        </p>
      )}
    </form>
  );
}
