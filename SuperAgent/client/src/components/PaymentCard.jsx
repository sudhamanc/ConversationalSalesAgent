import React from "react";
import { formatCurrency } from "../utils/responseFormatters";

export default function PaymentCard({ payment }) {
  const amount = typeof payment?.amount === "number" ? payment.amount : null;

  return (
    <div className="w-full rounded-2xl border border-emerald-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
        <span className="text-lg">✅</span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
            Payment Confirmed
          </p>
          <p className="text-base font-semibold text-slate-900">
            {amount !== null ? `${formatCurrency(amount)}/mo` : "—"}
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-2 text-sm text-slate-700">
        <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
          <span className="text-slate-500">Payment Method</span>
          <span className="font-medium text-slate-800">{payment.payment_method || "—"}</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
          <span className="text-slate-500">Transaction ID</span>
          <span className="font-mono text-xs font-medium text-slate-800">
            {payment.transaction_id || "—"}
          </span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2">
          <span className="text-slate-500">Status</span>
          <span className="font-semibold text-emerald-700">{payment.status || "—"}</span>
        </div>
      </div>

      <p className="mt-3 text-xs text-slate-400 text-center">
        Finalizing your order now…
      </p>
    </div>
  );
}
