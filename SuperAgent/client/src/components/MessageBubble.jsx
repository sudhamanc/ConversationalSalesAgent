import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getAgentInfo } from "../utils/agentLabels";
import QuoteCard from "./QuoteCard";
import ServiceabilityCard from "./ServiceabilityCard";
import ProductDetailsCard from "./ProductDetailsCard";
import PaymentCard from "./PaymentCard";
import OrderCard from "./OrderCard";
import SuggestionCard from "./SuggestionCard";
import {
  parseOfferQuote,
  parseProductAgentMessage,
  parseServiceabilityMessage,
  parsePaymentConfirmation,
  parseOrderConfirmation,
} from "../utils/responseFormatters";
import { getSuggestionsForMessage } from "../utils/suggestions";

function renderInlineFormatting(text) {
  const segments = text.split(/(\*\*[^*]+\*\*)/g);
  return segments.map((segment, index) => {
    const boldMatch = segment.match(/^\*\*([^*]+)\*\*$/);
    if (boldMatch) {
      return (
        <strong key={`bold-${index}`} className="font-semibold text-slate-900">
          {boldMatch[1]}
        </strong>
      );
    }
    return <React.Fragment key={`txt-${index}`}>{segment}</React.Fragment>;
  });
}

function hasMarkdownTable(text) {
  // Detects pipe-delimited markdown tables (header + separator + data rows)
  return /\|.+\|[\s\S]*\|[-: |]+\|/.test(text || "");
}

function hasRichMarkdown(text) {
  if (!text) return false;
  // Headings (### ), horizontal rules (---), tables, or multi-line lists with bold formatting
  return /^#{1,6}\s/m.test(text) || /^-{3,}$/m.test(text) || hasMarkdownTable(text) || (/\*\*[^*]+\*\*/m.test(text) && /^[\-*•]\s/m.test(text));
}

const markdownComponents = {
  h1: ({ children }) => <h1 className="text-lg font-bold text-slate-900 mt-3 mb-1">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold text-slate-900 mt-3 mb-1">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold text-slate-800 mt-2 mb-1">{children}</h3>,
  hr: () => <hr className="my-2 border-slate-200" />,
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full text-xs border-collapse border border-slate-300 rounded-lg">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-primary-50">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-semibold text-slate-700 border border-slate-300">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 text-slate-600 border border-slate-300">{children}</td>
  ),
  tr: ({ children }) => (
    <tr className="even:bg-slate-50">{children}</tr>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  ul: ({ children }) => <ul className="list-disc pl-4 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="text-slate-700">{children}</li>,
  p: ({ children }) => <div className="mb-1">{children}</div>,
};

function renderFormattedText(content) {
  // Use react-markdown when content contains markdown tables or complex formatting
  if (hasRichMarkdown(content)) {
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    );
  }

  // Normalize inline bullet separators (• Item1 • Item2) to line-start bullets
  const normalized = (content || "").replace(/(?<!\n)\s*•\s+/g, "\n• ");
  const lines = normalized.split("\n");

  return lines.map((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      return <div key={`line-${index}`} className="h-2" />;
    }

    if (/^[•\-*]\s+/.test(trimmed)) {
      const bulletText = trimmed.replace(/^[•\-*]\s+/, "");
      return (
        <div key={`line-${index}`} className="flex items-start gap-2">
          <span className="mt-1 text-slate-400">•</span>
          <span>{renderInlineFormatting(bulletText)}</span>
        </div>
      );
    }

    return <div key={`line-${index}`}>{renderInlineFormatting(line)}</div>;
  });
}

export default function MessageBubble({ message, onSuggestionPick, suggestionsDisabled = false }) {
  const isUser = message.role === "user";
  const agentInfo =
    !isUser && message.author ? getAgentInfo(message.author) : null;

  const quote = !isUser ? (message.structuredCard?.type === "quote" ? message.structuredCard.data : parseOfferQuote(message.content)) : null;
  // Order/payment detection runs before product to avoid false positives from numbered lists
  const orderConfirmation =
    !isUser && !quote ? parseOrderConfirmation(message.content) : null;
  const paymentConfirmation =
    !isUser && !quote && !orderConfirmation
      ? parsePaymentConfirmation(message.content)
      : null;
  const serviceabilityDetails =
    !isUser && !quote && !orderConfirmation && !paymentConfirmation
      ? parseServiceabilityMessage(message.content)
      : null;
  // Gate product parsing by author — prevents offer/discovery prose with numbered
  // lists or product IDs from being misclassified as a ProductDetailsCard.
  const productDetails =
    !isUser && !quote && !orderConfirmation && !paymentConfirmation && !serviceabilityDetails
    && message.author === "product_agent"
      ? parseProductAgentMessage(message.content)
      : null;

  const shouldRenderQuoteCard = Boolean(quote);
  const shouldRenderServiceabilityCard = Boolean(serviceabilityDetails);
  const shouldRenderProductCard = Boolean(productDetails);
  const shouldRenderPaymentCard = Boolean(paymentConfirmation);
  const shouldRenderOrderCard = Boolean(orderConfirmation);
  const assistantCardClass =
    "max-w-[90%] px-1 py-1 rounded-2xl text-sm leading-relaxed";
  const dynamicSuggestions =
    !isUser && Array.isArray(message.suggestions) ? message.suggestions : [];
  const fallbackSuggestions =
    !isUser && message.author
      ? getSuggestionsForMessage({
          author: message.author,
          content: message.content,
        })
      : [];
  const suggestions = dynamicSuggestions.length > 0 ? dynamicSuggestions : fallbackSuggestions;

  return (
    <div>
      <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        {/* Avatar for assistant */}
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-primary-100 flex-shrink-0 flex items-center justify-center mr-2 mt-1">
            <span className="text-primary-700 text-xs font-bold">SA</span>
          </div>
        )}

        {isUser ? (
          <div className="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-primary-600 text-white rounded-br-md">
            {message.content}
          </div>
        ) : (
          <div
            className={
              shouldRenderQuoteCard ||
              shouldRenderServiceabilityCard ||
              shouldRenderProductCard ||
              shouldRenderPaymentCard ||
              shouldRenderOrderCard
                ? assistantCardClass
                : "max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-slate-100 text-slate-800 rounded-bl-md"
            }
          >
            {shouldRenderQuoteCard ? (
              <QuoteCard quote={quote} />
            ) : shouldRenderOrderCard ? (
              <OrderCard order={orderConfirmation} />
            ) : shouldRenderPaymentCard ? (
              <PaymentCard payment={paymentConfirmation} />
            ) : shouldRenderServiceabilityCard ? (
              <ServiceabilityCard details={serviceabilityDetails} />
            ) : shouldRenderProductCard ? (
              <ProductDetailsCard payload={productDetails} />
            ) : (
              renderFormattedText(message.content)
            )}
          </div>
        )}

        {/* Avatar for user */}
        {isUser && (
          <div className="w-8 h-8 rounded-full bg-slate-200 flex-shrink-0 flex items-center justify-center ml-2 mt-1">
            <span className="text-slate-600 text-xs font-bold">U</span>
          </div>
        )}
      </div>

      {/* Agent label below assistant messages */}
      {agentInfo && message.content && (
        <p className="text-[10px] text-slate-400 mt-1 ml-10">
          via{" "}
          <span className={`font-medium ${agentInfo.badgeText}`}>
            {agentInfo.label}
          </span>
        </p>
      )}

      {!isUser && message.content && suggestions.length > 0 && (
        <SuggestionCard
          suggestions={suggestions}
          onSelect={onSuggestionPick}
          disabled={suggestionsDisabled}
        />
      )}
    </div>
  );
}
