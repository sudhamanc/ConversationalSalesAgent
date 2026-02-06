import React from "react";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Avatar for assistant */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary-100 flex-shrink-0 flex items-center justify-center mr-2 mt-1">
          <span className="text-primary-700 text-xs font-bold">SA</span>
        </div>
      )}

      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-primary-600 text-white rounded-br-md"
            : "bg-slate-100 text-slate-800 rounded-bl-md"
        }`}
      >
        {message.content}
      </div>

      {/* Avatar for user */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-200 flex-shrink-0 flex items-center justify-center ml-2 mt-1">
          <span className="text-slate-600 text-xs font-bold">U</span>
        </div>
      )}
    </div>
  );
}
