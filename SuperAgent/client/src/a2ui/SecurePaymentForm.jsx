import { useState } from "react";
import { savePaymentMethod } from "../utils/api";
import { useChatContext } from "../contexts/ChatContext";

/**
 * Secure payment form shown inside the payment A2UI surface (spec: guided-checkout).
 *
 * Card and bank details stay in this component's state: they are never written to
 * the A2UI data model, a chat message or an SSE event. On submit they go only to
 * POST /api/payment-methods (tokenized and saved by the payment service), the
 * fields are cleared, and the chat sends "I've added my Visa ending 1111. Please
 * use it to pay for my order." so the payment agent charges the saved method.
 */
const EMPTY_CARD = { number: "", expiry: "", cvv: "" };
const EMPTY_BANK = { routing: "", account: "", accountType: "checking" };

const inputClass =
  "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100";
const labelClass = "mb-1 block text-xs font-medium text-slate-500";

function digits(value) {
  return String(value || "").replace(/\D/g, "");
}

function formatCardNumber(value) {
  return digits(value).slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 ");
}

function luhnValid(number) {
  const d = digits(number);
  if (d.length < 13 || d.length > 19) return false;
  let sum = 0;
  for (let i = 0; i < d.length; i += 1) {
    let n = Number(d[d.length - 1 - i]);
    if (i % 2 === 1) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
  }
  return sum % 10 === 0;
}

function parseExpiry(value) {
  const match = String(value || "").match(/^\s*(\d{1,2})\s*\/\s*(\d{2}|\d{4})\s*$/);
  if (!match) return null;
  const month = Number(match[1]);
  const year = Number(match[2].length === 2 ? `20${match[2]}` : match[2]);
  if (month < 1 || month > 12) return null;
  const now = new Date();
  if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) return null;
  return { month, year };
}

function methodName(method) {
  if (method.payment_type === "ach") {
    return `${method.account_type || "bank"} account ending ${method.last_four}`;
  }
  const brand = method.card_brand
    ? method.card_brand.charAt(0).toUpperCase() + method.card_brand.slice(1)
    : "card";
  return `${brand === "Amex" ? "American Express" : brand} ending ${method.last_four}`;
}

export default function SecurePaymentForm({ amount, title }) {
  const { sendMessage, isStreaming } = useChatContext();
  const [kind, setKind] = useState("card");
  const [card, setCard] = useState(EMPTY_CARD);
  const [bank, setBank] = useState(EMPTY_BANK);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);

  function validate() {
    if (kind === "card") {
      if (!luhnValid(card.number)) return "Check the card number.";
      if (!parseExpiry(card.expiry)) return "Enter a valid expiry date (MM/YY).";
      if (!/^\d{3,4}$/.test(card.cvv)) return "Enter the 3 or 4 digit security code.";
      return "";
    }
    if (!/^\d{9}$/.test(digits(bank.routing))) return "The routing number has 9 digits.";
    if (digits(bank.account).length < 4) return "Check the account number.";
    return "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (busy || saved) return;
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setError("");
    setBusy(true);
    const expiry = parseExpiry(card.expiry);
    const details =
      kind === "card"
        ? {
            payment_type: "credit_card",
            card_number: digits(card.number),
            expiry_month: expiry.month,
            expiry_year: expiry.year,
            cvv: card.cvv,
          }
        : {
            payment_type: "ach",
            routing_number: digits(bank.routing),
            account_number: digits(bank.account),
            account_type: bank.accountType,
          };
    const result = await savePaymentMethod(details);
    setBusy(false);
    // Never keep the details around after a submit, successful or not.
    setCard(EMPTY_CARD);
    setBank((prev) => ({ ...EMPTY_BANK, accountType: prev.accountType }));
    if (!result.ok) {
      setError(result.error);
      return;
    }
    const name = methodName(result.method);
    setSaved(name);
    sendMessage(`I've added my ${name}. Please use it to pay for my order.`);
  }

  if (saved) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
        {saved.charAt(0).toUpperCase() + saved.slice(1)} saved securely to your account.
      </div>
    );
  }

  const tabClass = (active) =>
    `flex-1 rounded-lg px-3 py-1.5 text-xs font-medium ${
      active ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
    }`;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" autoComplete="on" noValidate>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-800">{title || "Add a payment method"}</p>
        <span className="flex items-center gap-1 text-[11px] text-slate-400">
          <span aria-hidden="true">🔒</span> Secure, never shared with the assistant
        </span>
      </div>
      <div className="flex gap-1 rounded-xl bg-slate-100 p-1" role="tablist">
        <button type="button" role="tab" aria-selected={kind === "card"} className={tabClass(kind === "card")} onClick={() => { setKind("card"); setError(""); }}>
          Card
        </button>
        <button type="button" role="tab" aria-selected={kind === "ach"} className={tabClass(kind === "ach")} onClick={() => { setKind("ach"); setError(""); }}>
          Bank account (ACH)
        </button>
      </div>

      {kind === "card" ? (
        <div className="grid grid-cols-4 gap-2">
          <label className="col-span-4">
            <span className={labelClass}>Card number</span>
            <input className={inputClass} inputMode="numeric" autoComplete="cc-number" placeholder="1234 5678 9012 3456"
              value={card.number} onChange={(e) => setCard({ ...card, number: formatCardNumber(e.target.value) })} />
          </label>
          <label className="col-span-2">
            <span className={labelClass}>Expiry</span>
            <input className={inputClass} inputMode="numeric" autoComplete="cc-exp" placeholder="MM/YY"
              value={card.expiry} onChange={(e) => setCard({ ...card, expiry: e.target.value.slice(0, 7) })} />
          </label>
          <label className="col-span-2">
            <span className={labelClass}>Security code</span>
            <input className={inputClass} type="password" inputMode="numeric" autoComplete="cc-csc" placeholder="CVC"
              value={card.cvv} onChange={(e) => setCard({ ...card, cvv: digits(e.target.value).slice(0, 4) })} />
          </label>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <label>
            <span className={labelClass}>Routing number</span>
            <input className={inputClass} inputMode="numeric" autoComplete="off" placeholder="9 digits"
              value={bank.routing} onChange={(e) => setBank({ ...bank, routing: digits(e.target.value).slice(0, 9) })} />
          </label>
          <label>
            <span className={labelClass}>Account number</span>
            <input className={inputClass} type="password" inputMode="numeric" autoComplete="off" placeholder="Account number"
              value={bank.account} onChange={(e) => setBank({ ...bank, account: digits(e.target.value).slice(0, 17) })} />
          </label>
          <label className="col-span-2">
            <span className={labelClass}>Account type</span>
            <select className={inputClass} value={bank.accountType} onChange={(e) => setBank({ ...bank, accountType: e.target.value })}>
              <option value="checking">Checking</option>
              <option value="savings">Savings</option>
            </select>
          </label>
        </div>
      )}

      {error && <p role="alert" className="text-xs text-red-600">{error}</p>}

      <button type="submit" disabled={busy || isStreaming}
        className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60">
        {busy ? "Saving…" : amount ? `Save and pay ${amount}` : "Save payment method"}
      </button>
    </form>
  );
}
