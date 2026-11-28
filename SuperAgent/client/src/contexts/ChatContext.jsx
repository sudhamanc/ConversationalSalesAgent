import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { streamChat, resetSession, getToken, sendFeedback } from "../utils/api";
import { getAgentInfo } from "../utils/agentLabels";
import { useGenerativeUIFunction } from "@copilotkit/react-core/v2/generative-ui";
import { salesUI } from "../a2ui/salesUI";
import { buttonLabel, closedEntry, isLocked } from "../a2ui/actedSurface";

const ChatContext = createContext(null);

/**
 * Copies the turn's trace id and feedback token (from the `done` event, present
 * only when tracing is on) onto the last assistant message.
 */
function withTraceInfo(messages, done) {
  if (!done || !done.trace_id || !done.feedback_token) return messages;
  const updated = [...messages];
  const last = updated[updated.length - 1];
  if (last && last.role === "assistant") {
    updated[updated.length - 1] = {
      ...last,
      traceId: done.trace_id,
      feedbackToken: done.feedback_token,
    };
  }
  return updated;
}

/**
 * Truncates text to maxLen characters, adding ellipsis if needed.
 */
function truncate(text, maxLen = 100) {
  if (!text || text.length <= maxLen) return text || "";
  return text.slice(0, maxLen).trimEnd() + "…";
}

/**
 * Extracts a summary from an agent response — first sentence or first N chars.
 */
function summarize(text, maxLen = 120) {
  if (!text) return "";
  // Strip markdown bold/italic markers for cleaner summary
  const clean = text.replace(/\*{1,2}([^*]+)\*{1,2}/g, "$1");
  const firstLine = clean.split("\n").find((l) => l.trim()) || clean;
  const periodIdx = firstLine.indexOf(".");
  if (periodIdx > 0 && periodIdx < maxLen) {
    return firstLine.slice(0, periodIdx + 1);
  }
  return truncate(firstLine, maxLen);
}

export function ChatProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const messagesRef = useRef(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);
  const [journeySteps, setJourneySteps] = useState([]);
  const [cart, setCart] = useState(null);
  const [activities, setActivities] = useState({
    customer: null,
    quote: null,
    order: null,
    scheduling: null,
    payment: null,
    fulfillment: [],
    notifications: [],
  });
  const [isStreaming, setIsStreaming] = useState(false);
  // What the running turn is doing (SSE `progress`): {stage, agent?, since}; null when idle.
  const [progress, setProgress] = useState(null);
  // The A2UI button click that started the running turn: {surface, button, label}.
  const pendingActionRef = useRef(null);
  // A card click made while a reply was still streaming: {message, surface, button, label}.
  // Sent as soon as that reply ends (spec: generative-ui, surface actions).
  const queuedActionRef = useRef(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const abortRef = useRef(false);
  const stepCountRef = useRef(0);
  // Track current turn's active agent and accumulated text per agent
  const currentAuthorRef = useRef(null);
  const agentContentRef = useRef("");

  /**
   * Appends `{button, label, status}` to the action history of A2UI surface
   * `surfaceId` (spec: generative-ui, acted surfaces show completion).
   */
  const recordSurfaceAction = useCallback((surfaceId, entry) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (!Array.isArray(msg.a2uiSurfaces) || !msg.a2uiSurfaces.some((s) => s.surface_id === surfaceId)) return msg;
        return {
          ...msg,
          a2uiSurfaces: msg.a2uiSurfaces.map((s) =>
            s.surface_id === surfaceId ? { ...s, actions: [...(s.actions || []), entry] } : s
          ),
        };
      })
    );
  }, []);

  /**
   * Closes every open surface of `kinds` whose step was completed without a click
   * on it, e.g. the cart once the order exists (spec: generative-ui, completed
   * steps close their surfaces). Surfaces that already show a choice keep it.
   */
  const closeSurfaces = useCallback((kinds, label) => {
    setMessages((prev) =>
      prev.map((msg) => {
        if (!Array.isArray(msg.a2uiSurfaces)) return msg;
        let changed = false;
        const surfaces = msg.a2uiSurfaces.map((s) => {
          if (!kinds.includes(s.kind) || isLocked(s.actions)) return s;
          changed = true;
          return { ...s, actions: [...(s.actions || []), closedEntry(label)] };
        });
        return changed ? { ...msg, a2uiSurfaces: surfaces } : msg;
      })
    );
  }, []);

  /** Marks the click that started this turn as done or failed. */
  const settlePendingAction = useCallback(
    (status) => {
      const action = pendingActionRef.current;
      pendingActionRef.current = null;
      if (action) recordSurfaceAction(action.surface, { button: action.button, label: action.label, status });
    },
    [recordSurfaceAction]
  );

  /**
   * Finalizes the current streaming journey step with a summary from accumulated content.
   */
  const finalizeCurrentStep = useCallback(() => {
    const content = agentContentRef.current;
    setJourneySteps((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last && last.status === "streaming") {
        updated[updated.length - 1] = {
          ...last,
          agentSummary: summarize(content),
          status: "complete",
        };
      }
      return updated;
    });
  }, []);

  /**
   * Creates a new journey step for a new agent mid-stream.
   */
  const startNewAgentStep = useCallback((author, userText) => {
    const info = getAgentInfo(author);
    stepCountRef.current += 1;
    const stepNum = stepCountRef.current;
    agentContentRef.current = "";
    setJourneySteps((prev) => [
      ...prev,
      {
        stepNumber: stepNum,
        userMessage: truncate(userText, 80),
        agentSummary: "",
        agent: author,
        agentLabel: info.label,
        status: "streaming",
      },
    ]);
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isStreaming) return;

      // Add user message
      const userMsg = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setProgress({ stage: "routing", since: Date.now() });
      abortRef.current = false;
      currentAuthorRef.current = null;
      agentContentRef.current = "";

      // Create initial journey step (will be assigned an agent when first token arrives)
      stepCountRef.current += 1;
      const stepNum = stepCountRef.current;
      setJourneySteps((prev) => [
        ...prev,
        {
          stepNumber: stepNum,
          userMessage: truncate(text, 80),
          agentSummary: "",
          agent: null,
          agentLabel: "",
          status: "streaming",
        },
      ]);

      // Placeholder for assistant response
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", author: null, suggestions: [] },
      ]);

      // Keep a local copy of user text for step labels
      const userText = text;

      await streamChat(
        text,
        // onToken — detects agent switches mid-stream
        (token, author) => {
          if (abortRef.current) return;

          const effectiveAuthor =
            author && author !== "super_sales_agent" ? author : null;

          if (effectiveAuthor) {
            if (!currentAuthorRef.current) {
              // First real agent — assign to the already-created step
              currentAuthorRef.current = effectiveAuthor;
              const info = getAgentInfo(effectiveAuthor);
              setJourneySteps((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.status === "streaming") {
                  updated[updated.length - 1] = {
                    ...last,
                    agent: effectiveAuthor,
                    agentLabel: info.label,
                  };
                }
                return updated;
              });
            } else if (effectiveAuthor !== currentAuthorRef.current) {
              // Agent changed mid-stream — finalize previous step, start new one
              finalizeCurrentStep();
              currentAuthorRef.current = effectiveAuthor;
              startNewAgentStep(effectiveAuthor, userText);
            }
          }

          // Accumulate content for the current agent's summary
          agentContentRef.current += token;

          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
                author: currentAuthorRef.current || author || last.author,
              };
            }
            return updated;
          });
        },
        // onDone — finalize the last active step
        (done) => {
          setMessages((prev) => withTraceInfo(prev, done));
          setIsStreaming(false);
          setProgress(null);
          settlePendingAction("done");
          finalizeCurrentStep();
        },
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
          setProgress(null);
          settlePendingAction("failed");

          // Mark step as complete with error
          setJourneySteps((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.status === "streaming") {
              updated[updated.length - 1] = {
                ...last,
                agentSummary: "Error occurred",
                status: "complete",
              };
            }
            return updated;
          });
        },
        // onCartUpdate
        (cartData) => {
          if (cartData) {
            setCart(cartData);
          }
        },
        // onSuggestions
        (suggestions, author) => {
          if (!Array.isArray(suggestions) || suggestions.length === 0) return;

          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                author: last.author || author || last.author,
                suggestions,
              };
            }
            return updated;
          });
        },
        // onActivityUpdate
        (event) => {
          if (!event || !event.category || !event.data) return;
          if (event.category === "order" && event.tool === "create_order" && event.data.success && event.data.order_id) {
            closeSurfaces(["cart", "quote", "contact"], "Order placed");
          } else if (event.category === "scheduling" && event.tool === "schedule_installation" && event.data.success) {
            closeSurfaces(["scheduling"], "Installation booked");
          }
          setActivities((prev) => {
            const next = { ...prev };
            if (event.category === "customer") {
              next.customer = event.data;
            } else if (event.category === "notification" && event.data.status_update) {
              // Delivery status of a queued email: update its entry in place.
              const id = event.data.notification_id;
              if (!id || !prev.notifications.some((n) => n.notification_id === id)) return prev;
              next.notifications = prev.notifications.map((n) =>
                n.notification_id === id ? { ...n, status: event.data.status } : n
              );
            } else if (event.category === "notification") {
              next.notifications = [...prev.notifications, { tool: event.tool, ...event.data, _ts: Date.now() }];
            } else if (event.category === "fulfillment") {
              next.fulfillment = [...prev.fulfillment, { tool: event.tool, ...event.data, _ts: Date.now() }];
            } else if (event.category === "quote") {
              next.quote = event.data;
            } else if (event.category === "order") {
              next.order = { ...prev.order, ...event.data, tool: event.tool };
            } else if (event.category === "scheduling") {
              next.scheduling = event.data;
            } else if (event.category === "payment") {
              next.payment = { ...event.data, tool: event.tool, _ts: Date.now() };
            }
            return next;
          });
        },
        // onStructuredCard — attach card data to the current assistant message
        (event) => {
          if (!event || !event.card_type || !event.data) return;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                structuredCard: { type: event.card_type, data: event.data },
              };
            }
            return updated;
          });
        },
        // onA2UI — append an A2UI surface (spec: generative-ui) to the current assistant message
        (event) => {
          if (!event || !event.surface_id || !Array.isArray(event.operations)) return;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              const surfaces = (last.a2uiSurfaces || []).filter((s) => s.surface_id !== event.surface_id);
              updated[updated.length - 1] = {
                ...last,
                a2uiSurfaces: [...surfaces, { surface_id: event.surface_id, kind: event.kind, tool: event.tool, operations: event.operations }],
              };
            }
            return updated;
          });
        },
        // onProgress — which step the turn is on (SSE `progress`)
        (event) => {
          if (!event || !event.stage) return;
          setProgress({ stage: event.stage, agent: event.agent, since: Date.now() });
        }
      );
    },
    [isStreaming, finalizeCurrentStep, startNewAgentStep, settlePendingAction, closeSurfaces]
  );

  // A2UI Buttons call sendChatMessage({message, surface, button}): the click is the
  // customer's next message, and the card shows the choice (pending → done/failed).
  // A card can arrive before its turn ends (e.g. the contact card, then a handoff):
  // a click in that window locks the card now and is sent when the reply ends.
  useGenerativeUIFunction(salesUI, "sendChatMessage", ({ message, surface, button }) => {
    if (queuedActionRef.current) return { sent: false, reason: "Another choice is waiting to be sent" };
    let action = null;
    if (surface && button) {
      const owner = messagesRef.current.find((m) => m.a2uiSurfaces?.some((s) => s.surface_id === surface));
      const target = owner?.a2uiSurfaces.find((s) => s.surface_id === surface);
      if (target && isLocked(target.actions)) return { sent: false, reason: "This card was already used" };
      if (target) action = { surface, button, label: buttonLabel(target.operations, button) };
    }
    if (action) recordSurfaceAction(action.surface, { button: action.button, label: action.label, status: "pending" });
    if (isStreaming) {
      queuedActionRef.current = { message, action };
      return { sent: true, queued: true };
    }
    pendingActionRef.current = action;
    sendMessage(message);
    return { sent: true };
  });

  // Send a click queued during the previous reply once that reply has ended.
  useEffect(() => {
    if (isStreaming || !queuedActionRef.current) return;
    const { message, action } = queuedActionRef.current;
    queuedActionRef.current = null;
    pendingActionRef.current = action;
    sendMessage(message);
  }, [isStreaming, sendMessage]);

  /**
   * Thumbs up/down on the assistant message at `index`. Optimistic; reverts
   * when the server does not record the vote.
   */
  const submitFeedback = useCallback(async (index, value) => {
    // Read from the ref: state updaters run lazily, so they cannot hand back the message.
    const target = messagesRef.current[index];
    if (!target || target.role !== "assistant" || !target.traceId || target.feedbackPending) return;
    setMessages((prev) => {
      if (prev[index]?.traceId !== target.traceId) return prev;
      const updated = [...prev];
      updated[index] = { ...prev[index], feedback: value, feedbackPending: true };
      return updated;
    });
    const ok = await sendFeedback(target.traceId, target.feedbackToken, value);
    setMessages((prev) => {
      const msg = prev[index];
      if (!msg || msg.traceId !== target.traceId) return prev;
      const updated = [...prev];
      updated[index] = { ...msg, feedback: ok ? value : target.feedback || null, feedbackPending: false };
      return updated;
    });
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setJourneySteps([]);
    setCart(null);
    setActivities({ customer: null, quote: null, order: null, scheduling: null, payment: null, fulfillment: [], notifications: [] });
    setIsStreaming(false);
    setProgress(null);
    pendingActionRef.current = null;
    queuedActionRef.current = null;
    abortRef.current = true;
    stepCountRef.current = 0;
    currentAuthorRef.current = null;
    agentContentRef.current = "";
    resetSession();
  }, []);

  // --- Automatic welcome message on session start ---
  useEffect(() => {
    let cancelled = false;

    async function initWelcome() {
      // Pre-create the session eagerly
      await getToken();

      if (cancelled) return;
      setIsStreaming(true);
      setProgress({ stage: "routing", since: Date.now() });
      currentAuthorRef.current = null;
      agentContentRef.current = "";

      // Create a journey step for the greeting
      stepCountRef.current += 1;
      const stepNum = stepCountRef.current;
      setJourneySteps((prev) => [
        ...prev,
        {
          stepNumber: stepNum,
          userMessage: "Session started",
          agentSummary: "",
          agent: null,
          agentLabel: "",
          status: "streaming",
        },
      ]);

      // Add placeholder assistant message (no user bubble)
      setMessages([{ role: "assistant", content: "", author: null, suggestions: [] }]);

      await streamChat(
        "hi",
        // onToken
        (token, author) => {
          if (cancelled) return;

          const effectiveAuthor =
            author && author !== "super_sales_agent" ? author : null;

          if (effectiveAuthor && !currentAuthorRef.current) {
            currentAuthorRef.current = effectiveAuthor;
            const info = getAgentInfo(effectiveAuthor);
            setJourneySteps((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.status === "streaming") {
                updated[updated.length - 1] = {
                  ...last,
                  agent: effectiveAuthor,
                  agentLabel: info.label,
                };
              }
              return updated;
            });
          }

          agentContentRef.current += token;

          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
                author: currentAuthorRef.current || author || last.author,
              };
            }
            return updated;
          });
        },
        // onDone
        (done) => {
          if (cancelled) return;
          setMessages((prev) => withTraceInfo(prev, done));
          setIsStreaming(false);
          setProgress(null);
          finalizeCurrentStep();
        },
        // onError — silently fail; customer can still type
        () => {
          if (cancelled) return;
          setIsStreaming(false);
          setProgress(null);
          // Remove the empty placeholder if nothing came through
          setMessages((prev) => (prev.length === 1 && !prev[0].content ? [] : prev));
          setJourneySteps((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.status === "streaming") {
              updated[updated.length - 1] = { ...last, status: "complete", agentSummary: "" };
            }
            return updated;
          });
        },
        // onCartUpdate
        null,
        // onSuggestions
        (suggestions, author) => {
          if (!Array.isArray(suggestions) || suggestions.length === 0) return;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = { ...last, suggestions };
            }
            return updated;
          });
        },
        // onActivityUpdate
        null,
        // onStructuredCard
        null,
        // onA2UI
        null,
        // onProgress
        (event) => {
          if (cancelled || !event || !event.stage) return;
          setProgress({ stage: event.stage, agent: event.agent, since: Date.now() });
        }
      );
    }

    initWelcome();

    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ChatContext.Provider
      value={{
        messages,
        isStreaming,
        progress,
        sendMessage,
        clearChat,
        submitFeedback,
        journeySteps,
        cart,
        activities,
        isSidebarOpen,
        setIsSidebarOpen,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used within ChatProvider");
  return ctx;
}
