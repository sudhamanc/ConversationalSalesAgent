import React from "react";
import { formatCurrency } from "../utils/responseFormatters";

function Row({ label, value, mono = false }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg bg-slate-50 px-3 py-2">
      <span className="text-slate-500 shrink-0">{label}</span>
      <span className={`font-medium text-slate-800 text-right ${mono ? "font-mono text-xs" : ""}`}>
        {value}
      </span>
    </div>
  );
}

export default function OrderCard({ order }) {
  const monthlyTotal =
    typeof order?.monthly_total === "number" ? order.monthly_total : null;
  const whatsNext = Array.isArray(order?.whats_next) ? order.whats_next : [];

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
        <span className="text-lg">✅</span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Order Confirmed
          </p>
          <p className="text-base font-semibold text-slate-900">{order.order_id || "—"}</p>
        </div>
      </div>

      {/* Order details */}
      <div className="mt-3 space-y-2 text-sm">
        <Row label="Customer" value={order.customer} />
        <Row label="Service" value={order.service} />
        <Row label="Address" value={order.address} />
        <Row label="Installation Date" value={order.installation_date} />
        {monthlyTotal !== null && (
          <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
            <span className="text-slate-500">Monthly Total</span>
            <span className="font-semibold text-slate-900">{formatCurrency(monthlyTotal)}/mo</span>
          </div>
        )}
        <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2">
          <span className="text-slate-500">Payment</span>
          <span className="font-semibold text-emerald-700">✅ {order.payment_status || "Paid"}</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-blue-50 px-3 py-2">
          <span className="text-slate-500">Order Status</span>
          <span className="font-semibold text-blue-700">{order.order_status || "Confirmed"}</span>
        </div>
      </div>

      {/* Email confirmation */}
      {order.contact_email && (
        <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          📧 Confirmation sent to{" "}
          <span className="font-medium text-slate-700">{order.contact_email}</span>
        </div>
      )}

      {/* What's next */}
      {whatsNext.length > 0 && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
            What&apos;s Next?
          </p>
          <div className="space-y-1">
            {whatsNext.map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-slate-600">
                <span className="text-slate-300">›</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
