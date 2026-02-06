import { useState, useCallback, useRef } from "react";
import { streamChat } from "../utils/api";

/**
 * Custom hook encapsulating chat state and streaming logic.
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

      // Build history from current messages (before this new message)
      const history = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Placeholder for assistant response
      const assistantIdx = messages.length + 1;
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      await streamChat(
        text,
        history,
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
    [messages, isStreaming]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setIsStreaming(false);
    abortRef.current = true;
  }, []);

  return { messages, isStreaming, sendMessage, clearChat };
}
