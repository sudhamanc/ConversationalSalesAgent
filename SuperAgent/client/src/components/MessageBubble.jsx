import React from "react";
import { getAgentInfo } from "../utils/agentLabels";
import QuoteCard from "./QuoteCard";
import ServiceabilityCard from "./ServiceabilityCard";
import ProductDetailsCard from "./ProductDetailsCard";
import SuggestionCard from "./SuggestionCard";
import {
  parseOfferQuote,
  parseProductAgentMessage,
  parseServiceabilityMessage,
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

function renderFormattedText(content) {
  const lines = (content || "").split("\n");

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

  const quote = !isUser ? parseOfferQuote(message.content) : null;
  const serviceabilityDetails =
    !isUser && !quote ? parseServiceabilityMessage(message.content) : null;
  const productDetails =
    !isUser && !quote && !serviceabilityDetails
      ? parseProductAgentMessage(message.content)
      : null;

  const shouldRenderQuoteCard = Boolean(quote);
  const shouldRenderServiceabilityCard = Boolean(serviceabilityDetails);
  const shouldRenderProductCard = Boolean(productDetails);
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
              shouldRenderProductCard
                ? assistantCardClass
                : "max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-slate-100 text-slate-800 rounded-bl-md"
            }
          >
            {shouldRenderQuoteCard ? (
              <QuoteCard quote={quote} />
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
