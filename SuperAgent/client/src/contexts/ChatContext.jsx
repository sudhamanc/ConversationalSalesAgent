import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { streamChat, resetSession, getToken } from "../utils/api";
import { getAgentInfo } from "../utils/agentLabels";

const ChatContext = createContext(null);

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
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const abortRef = useRef(false);
  const stepCountRef = useRef(0);
  // Track current turn's active agent and accumulated text per agent
  const currentAuthorRef = useRef(null);
  const agentContentRef = useRef("");

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
        () => {
          setIsStreaming(false);
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
          setActivities((prev) => {
            const next = { ...prev };
            if (event.category === "customer") {
              next.customer = event.data;
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
        }
      );
    },
    [isStreaming, finalizeCurrentStep, startNewAgentStep]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setJourneySteps([]);
    setCart(null);
    setActivities({ customer: null, quote: null, order: null, scheduling: null, payment: null, fulfillment: [], notifications: [] });
    setIsStreaming(false);
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
        () => {
          if (cancelled) return;
          setIsStreaming(false);
          finalizeCurrentStep();
        },
        // onError — silently fail; customer can still type
        () => {
          if (cancelled) return;
          setIsStreaming(false);
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
        null
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
        sendMessage,
        clearChat,
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
