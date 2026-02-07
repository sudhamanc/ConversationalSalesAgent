import { useState, useCallback, useRef } from "react";
import { streamChat, resetSession } from "../utils/api";

/**
 * Custom hook encapsulating chat state and SSE streaming logic.
 *
 * Conversation history is managed server-side by the ADK session service.
 * The client only tracks messages for display purposes.
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(false);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isStreaming) return;

      const userMsg = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      abortRef.current = false;

      // Placeholder for assistant response
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      await streamChat(
        text,
        // onToken
        (token) => {
          if (abortRef.current) return;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
              };
            }
            return updated;
          });
        },
        // onDone
        () => setIsStreaming(false),
        // onError
        (err) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: `Error: ${err}`,
              };
            }
            return updated;
          });
          setIsStreaming(false);
        }
      );
    },
    [isStreaming]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setIsStreaming(false);
    abortRef.current = true;
    // Reset the server session so a fresh ADK session is created next time
    resetSession();
  }, []);

  return { messages, isStreaming, sendMessage, clearChat };
}
