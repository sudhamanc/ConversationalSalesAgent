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

const CLIENT_ID_KEY = "csa_uid";

/**
 * Stable anonymous browser id (UUID v4). Lets the server keep user-scoped
 * state and long-term memory across sessions. Falls back to a per-page id
 * when storage is unavailable (private mode, blocked site data).
 */
function getClientId() {
  try {
    let id = window.localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      window.localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

/**
 * Create a new session and store the token.
 */
export async function createSession() {
  const res = await fetch(`${API_BASE}/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: getClientId() }),
  });
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
 * Current session token without creating a session (null when none exists).
 * Used by the remote-logging shim, which must never create sessions itself.
 */
export function getCurrentToken() {
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
 * @param {function} onDone  - Called when streaming completes, with the `done` payload
 *                             ({type, trace_id?, feedback_token?}) when the server sent one.
 * @param {function} onError - Called on error with error message.
 * @param {function} [onCartUpdate] - Called with cart data when a cart_update event arrives.
 * @param {function} [onSuggestions] - Called with (suggestionsArray, authorString) for LLM suggestion events.
 * @param {function} [onActivityUpdate] - Called with {category, tool, data} for activity panel events.
 * @param {function} [onStructuredCard] - Called with {card_type, data} for inline structured cards in chat.
 */
export async function streamChat(
  message,
  onToken,
  onDone,
  onError,
  onCartUpdate,
  onSuggestions,
  onActivityUpdate,
  onStructuredCard
) {
  const token = await getToken();
  console.info("[chat] send", { length: (message || "").length });

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
      return streamChat(message, onToken, onDone, onError, onCartUpdate, onSuggestions, onActivityUpdate, onStructuredCard);
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
          } else if (payload.type === "activity_update") {
            onActivityUpdate?.(payload);
          } else if (payload.type === "structured_card") {
            onStructuredCard?.(payload);
          } else if (payload.type === "suggestions") {
            onSuggestions?.(payload.data, payload.author);
          } else if (payload.type === "done") {
            console.info("[chat] done");
            // With tracing on, done carries {trace_id, feedback_token} for sendFeedback().
            onDone(payload);
            return;
          } else if (payload.type === "error") {
            console.error("[chat] error", payload.content);
            onError(payload.content);
            return;
          }
        } catch (e) {
          console.error("Failed to parse SSE event:", jsonStr, e);
        }
      }
    }

    console.info("[chat] done");
    onDone();
  } catch (err) {
    console.error("[chat] network error", err);
    onError(err.message || "Network error");
  }
}

/**
 * Record a thumbs up/down on an assistant reply (Langfuse score on the turn's trace).
 *
 * @param {string} traceId - `trace_id` from the turn's `done` event.
 * @param {string} feedbackToken - `feedback_token` from the same `done` event.
 * @param {"up"|"down"} value - The vote.
 * @returns {Promise<boolean>} true when the server recorded the vote (204).
 */
export async function sendFeedback(traceId, feedbackToken, value) {
  const token = getCurrentToken();
  if (!token || !traceId || !feedbackToken) return false;
  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ trace_id: traceId, feedback_token: feedbackToken, value }),
    });
    if (!res.ok) console.warn("[feedback] not recorded", res.status);
    return res.status === 204;
  } catch (err) {
    console.warn("[feedback] network error", err);
    return false;
  }
}
