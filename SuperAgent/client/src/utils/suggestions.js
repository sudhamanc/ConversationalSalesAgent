import {
  parseOfferQuote,
  parseProductAgentMessage,
  parseServiceabilityMessage,
} from "./responseFormatters";

function dedupeSuggestions(list) {
  const seen = new Set();
  return list.filter((item) => {
    const key = item.text.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 3);
}

// Client fallback, used only when the gateway sends no `suggestions` event.
// Every chip is a first-person message the CUSTOMER sends (it pre-fills the
// input); [placeholders] are filled in before sending. Mirrors the gateway's
// SuperAgent/server/api/suggestion_playbook.py.

const chips = (...texts) => texts.map((text) => ({ text }));

function fromGreeting() {
  return chips(
    "We're [company name], located at [street, city, state ZIP]",
    "I need business internet for my office",
    "What plans do you offer for small businesses?",
  );
}

function fromDiscovery(content) {
  const lower = content.toLowerCase();
  if (lower.includes("email") || lower.includes("phone")) {
    return chips(
      "You can reach me at [email] or [phone]",
      "Check service at our address",
      "Show me plans for my business",
    );
  }
  if (lower.includes("address") || lower.includes("zip code")) {
    return chips(
      "Our address is [street, city, state ZIP]",
      "We have [number] employees and need [internet/voice/both]",
      "What plans do you offer for small businesses?",
    );
  }
  return chips(
    "Check service at our address",
    "We have [number] employees and need [internet/voice/both]",
    "Show me plans for my business",
  );
}

function fromServiceability(content) {
  const parsed = parseServiceabilityMessage(content);
  const productIds = parsed?.products?.map((item) => item.id).filter(Boolean) || [];
  const notServiceable = /not (currently )?(serviceable|available)/i.test(content);

  if (productIds.length || !notServiceable) {
    return chips(
      "Show me the plans available at my address",
      "Which plan fits [number] employees?",
      "Quote me [plan] on a [12/24/36]-month term",
    );
  }

  return chips(
    "Check a different address: [street, city, state ZIP]",
    "What options do I have at this location?",
    "Let me know when service reaches my area",
  );
}

function fromProduct(content) {
  const parsed = parseProductAgentMessage(content);
  const productIds = parsed?.products?.map((item) => item.productId).filter(Boolean) || [];

  if (productIds.length) {
    return chips(
      "Quote me these plans on a [12/24/36]-month term",
      "Compare the top two options for me",
      "Which of these fits [number] employees?",
    );
  }

  return chips(
    "Get me a quote for these plans",
    "Compare these options for me",
    "Which option is best for a small business?",
  );
}

function fromOffer(content) {
  const quote = parseOfferQuote(content);
  const hasQuote = Boolean(quote?.offer_id);

  return chips(
    hasQuote ? "I'd like to go ahead with this quote" : "I'd like to place my order",
    "Requote this on a [12/24/36]-month term",
    "Remove [product] and requote",
  );
}

function fromOrder() {
  return chips(
    "Schedule my installation for [date]",
    "What installation dates are available?",
    "Show my order details",
  );
}

function fromPayment(content) {
  if (/card|payment details|cvv/i.test(content) && !/payment (was )?(successful|completed|approved)/i.test(content)) {
    return chips(
      "My card is [card number], exp [MM/YY], CVV [CVV]",
      "What payment methods do you accept?",
      "Show my order total",
    );
  }
  return chips(
    "Simulate my install day",
    "Email me the payment receipt",
    "Show my order status",
  );
}

function fromFulfillment() {
  return chips(
    "[date] in the [morning/afternoon] works for me",
    "Simulate my install day",
    "Show my installation status",
  );
}

function fromComms() {
  return chips(
    "Show me the messages you've sent me",
    "Resend my latest confirmation",
    "Email me a status update on my order",
  );
}

function fromFaq() {
  return chips(
    "Is there an early-termination fee?",
    "How long does installation take?",
    "Do you provide 24/7 support?",
  );
}

function genericSuggestions(content) {
  const lower = (content || "").toLowerCase();

  if (lower.includes("quote") || lower.includes("offer")) {
    return chips(
      "I'd like to go ahead with this quote",
      "Requote this on a [12/24/36]-month term",
      "What contract terms do you offer?",
    );
  }

  if (lower.includes("serviceable")) {
    return chips(
      "Show me the plans available at my address",
      "Get me a quote for this location",
      "Check a different address: [street, city, state ZIP]",
    );
  }

  return chips(
    "What plans do you offer for small businesses?",
    "Check service at [street, city, state ZIP]",
    "How long does installation take?",
  );
}

export function getSuggestionsForMessage({ author, content }) {
  if (!author || !content || !content.trim()) return [];

  let suggestions;
  switch (author) {
    case "greeting_agent":
      suggestions = fromGreeting();
      break;
    case "discovery_agent":
      suggestions = fromDiscovery(content);
      break;
    case "serviceability_agent":
      suggestions = fromServiceability(content);
      break;
    case "product_agent":
      suggestions = fromProduct(content);
      break;
    case "offer_management_agent":
      suggestions = fromOffer(content);
      break;
    case "order_agent":
      suggestions = fromOrder();
      break;
    case "payment_agent":
      suggestions = fromPayment(content);
      break;
    case "service_fulfillment_agent":
      suggestions = fromFulfillment();
      break;
    case "customer_communication_agent":
      suggestions = fromComms();
      break;
    case "faq_agent":
      suggestions = fromFaq();
      break;
    default:
      suggestions = genericSuggestions(content);
      break;
  }

  return dedupeSuggestions(suggestions || []);
}
