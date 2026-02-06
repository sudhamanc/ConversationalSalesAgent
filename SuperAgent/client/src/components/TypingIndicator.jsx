import React from "react";

export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="w-8 h-8 rounded-full bg-primary-100 flex-shrink-0 flex items-center justify-center mr-2 mt-1">
        <span className="text-primary-700 text-xs font-bold">SA</span>
      </div>
      <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
        <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full inline-block" />
        <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full inline-block" />
        <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full inline-block" />
      </div>
    </div>
  );
}
