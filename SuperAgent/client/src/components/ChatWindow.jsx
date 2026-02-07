import React, { useRef, useEffect } from "react";
import { useChat } from "../hooks/useChat";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import TypingIndicator from "./TypingIndicator";

export default function ChatWindow() {
  const { messages, isStreaming, sendMessage, clearChat } = useChat();
  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-scroll px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-400">
            <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mb-4">
              <svg
                className="w-8 h-8 text-primary-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-500">
              Start a conversation
            </p>
            <p className="text-xs mt-1 max-w-xs">
              Ask about products, check service availability, get pricing, or
              place an order.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {isStreaming &&
          messages.length > 0 &&
          messages[messages.length - 1].content === "" && (
            <TypingIndicator />
          )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        disabled={isStreaming}
        onClear={clearChat}
        hasMessages={messages.length > 0}
      />
    </>
  );
}
