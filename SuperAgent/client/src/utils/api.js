/**
 * API client for the SuperAgent backend.
 *
 * Handles session creation and SSE streaming for chat.
 * Conversation history is managed server-side by the ADK session service,
 * so the client only sends the current message.
 */

const API_BASE = "/api";

let _token = null;
let _sessionId = null;

/**
 * Create a new session and store the token.
 */
export async function createSession() {
  const res = await fetch(`${API_BASE}/session`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  const data = await res.json();
  _token = data.token;
  _sessionId = data.session_id;
  return data;
}

/**
 * Get the current session token, creating a session if needed.
 */
export async function getToken() {
  if (!_token) await createSession();
  return _token;
}

/**
 * Reset the stored session so the next request creates a fresh one.
 * Called when the user clears the chat.
 */
export function resetSession() {
  _token = null;
  _sessionId = null;
}

/**
 * Send a chat message and stream the response via SSE.
 *
 * @param {string} message - User message text.
 * @param {function} onToken - Called with (tokenString, authorString) for each streamed token.
 * @param {function} onDone  - Called when streaming completes.
 * @param {function} onError - Called on error with error message.
 * @param {function} [onCartUpdate] - Called with cart data when a cart_update event arrives.
 * @param {function} [onSuggestions] - Called with (suggestionsArray, authorString) for LLM suggestion events.
 */
export async function streamChat(
  message,
  onToken,
  onDone,
  onError,
  onCartUpdate,
  onSuggestions
) {
  const token = await getToken();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ message }),
    });

    if (res.status === 401) {
      // Session expired – create a new one and retry once
      await createSession();
      return streamChat(message, onToken, onDone, onError, onCartUpdate, onSuggestions);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;

        try {
          const payload = JSON.parse(jsonStr);
          if (payload.type === "token") {
            onToken(payload.content, payload.author);
          } else if (payload.type === "cart_update") {
            onCartUpdate?.(payload.data);
          } else if (payload.type === "suggestions") {
            onSuggestions?.(payload.data, payload.author);
          } else if (payload.type === "done") {
            onDone();
            return;
          } else if (payload.type === "error") {
            onError(payload.content);
            return;
          }
        } catch (e) {
          console.error("Failed to parse SSE event:", jsonStr, e);
        }
      }
    }

    onDone();
  } catch (err) {
    onError(err.message || "Network error");
  }
}
