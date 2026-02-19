/**
 * Maps agent keys from SSE `event.author` to friendly labels and Tailwind badge classes.
 */

const AGENT_LABELS = {
  discovery_agent: {
    label: "Discovery",
    badgeBg: "bg-blue-100",
    badgeText: "text-blue-700",
  },
  serviceability_agent: {
    label: "Serviceability",
    badgeBg: "bg-green-100",
    badgeText: "text-green-700",
  },
  product_agent: {
    label: "Products",
    badgeBg: "bg-purple-100",
    badgeText: "text-purple-700",
  },
  offer_management_agent: {
    label: "Offers",
    badgeBg: "bg-fuchsia-100",
    badgeText: "text-fuchsia-700",
  },
  order_agent: {
    label: "Order",
    badgeBg: "bg-orange-100",
    badgeText: "text-orange-700",
  },
  payment_agent: {
    label: "Payment",
    badgeBg: "bg-emerald-100",
    badgeText: "text-emerald-700",
  },
  service_fulfillment_agent: {
    label: "Fulfillment",
    badgeBg: "bg-teal-100",
    badgeText: "text-teal-700",
  },
  greeting_agent: {
    label: "Greeting",
    badgeBg: "bg-amber-100",
    badgeText: "text-amber-700",
  },
  faq_agent: {
    label: "FAQ",
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-700",
  },
  customer_communication_agent: {
    label: "Communications",
    badgeBg: "bg-indigo-100",
    badgeText: "text-indigo-700",
  },
  super_sales_agent: {
    label: "SuperAgent",
    badgeBg: "bg-primary-100",
    badgeText: "text-primary-700",
  },
};

const DEFAULT_AGENT = {
  label: "Agent",
  badgeBg: "bg-slate-100",
  badgeText: "text-slate-700",
};

export function getAgentInfo(authorKey) {
  if (!authorKey) return DEFAULT_AGENT;
  return AGENT_LABELS[authorKey] || DEFAULT_AGENT;
}
