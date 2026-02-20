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

function fromGreeting() {
  return [
    { text: "I need business internet for my location" },
    { text: "I want to check serviceability for my address" },
    { text: "Show business product options for my company" },
  ];
}

function fromDiscovery(content) {
  const lower = content.toLowerCase();
  if (lower.includes("full address") || lower.includes("zip code")) {
    return [
      { text: "My company address is [Street, City, State, ZIP]" },
      { text: "Use our registered company address for this request" },
      { text: "Check serviceability for our business address" },
    ];
  }

  return [
    { text: "Check serviceability for our location" },
    { text: "Show product options for our business" },
    { text: "Give me pricing after serviceability check" },
  ];
}

function fromServiceability(content) {
  const parsed = parseServiceabilityMessage(content);
  const productIds = parsed?.products?.map((item) => item.id).filter(Boolean) || [];

  if (productIds.length) {
    return dedupeSuggestions([
      { text: "Show technical specs for the recommended products" },
      { text: "Compare the top two recommended options" },
      { text: "Generate a quote for the selected products" },
    ]);
  }

  return [
    { text: "Show available products at this location" },
    { text: "Check a different address" },
    { text: "Connect me to pricing options" },
  ];
}

function fromProduct(content) {
  const parsed = parseProductAgentMessage(content);
  const productIds = parsed?.products?.map((item) => item.productId).filter(Boolean) || [];

  if (productIds.length) {
    return dedupeSuggestions([
      { text: "Generate a quote for these products" },
      { text: "Compare the best two product options" },
      { text: "Show term discounts for 24 months" },
    ]);
  }

  return [
    { text: "Get a quote for these products" },
    { text: "Compare these product options" },
    { text: "Which option is best for a small business?" },
  ];
}

function fromOffer(content) {
  const quote = parseOfferQuote(content);
  const hasQuote = Boolean(quote?.offer_id);

  return dedupeSuggestions([
    hasQuote ? { text: "Proceed with this quote" } : { text: "Proceed to order creation" },
    { text: "Recalculate this quote for a 24-month term" },
    { text: "Remove one product and requote" },
  ]);
}

function fromOrder() {
  return [
    { text: "Process payment for this order" },
    { text: "Show my order summary" },
    { text: "What are the next steps after order creation?" },
  ];
}

function fromPayment() {
  return [
    { text: "Schedule installation" },
    { text: "Send payment confirmation" },
    { text: "Show payment status" },
  ];
}

function fromFulfillment() {
  return [
    { text: "Send installation confirmation to customer" },
    { text: "Show activation status" },
    { text: "Reschedule installation" },
  ];
}

function fromComms() {
  return [
    { text: "Show notification history" },
    { text: "Resend the latest confirmation" },
    { text: "Send a status update to the customer" },
  ];
}

function fromFaq() {
  return [
    { text: "Show me your cancellation policy" },
    { text: "How long does installation take?" },
    { text: "Do you provide 24/7 support?" },
  ];
}

function genericSuggestions(content) {
  const lower = (content || "").toLowerCase();

  if (lower.includes("quote") || lower.includes("offer")) {
    return [
      { text: "Proceed with this quote" },
      { text: "Adjust products and requote" },
      { text: "Show me contract term options" },
    ];
  }

  if (lower.includes("serviceable")) {
    return [
      { text: "Show available product specs" },
      { text: "Get a quote for this location" },
      { text: "Check another address" },
    ];
  }

  return [
    { text: "Continue" },
    { text: "Show me next best step" },
    { text: "Give me a summary" },
  ];
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
      suggestions = fromPayment();
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
