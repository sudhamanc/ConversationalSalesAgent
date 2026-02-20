import React from "react";
import { formatCurrency } from "../utils/responseFormatters";

export default function QuoteCard({ quote }) {
  const items = Array.isArray(quote?.items) ? quote.items : [];
  const discountBreakdown = Array.isArray(quote?.discount_breakdown) ? quote.discount_breakdown : [];
  const monthlyTotal =
    typeof quote?.monthly_total === "number" ? quote.monthly_total : quote?.total_price;
  const yearlyTotal =
    typeof quote?.yearly_total === "number"
      ? quote.yearly_total
      : typeof monthlyTotal === "number"
      ? Number((monthlyTotal * 12).toFixed(2))
      : null;

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Quote</p>
          <p className="text-base font-semibold text-slate-900">{quote.offer_id}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Term</p>
          <p className="text-sm font-medium text-slate-800">{quote.term_months || "-"} months</p>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={`${item.product_id}-${item.quantity}`} className="rounded-xl bg-slate-50 p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">{item.product_name || item.product_id}</p>
                <p className="text-xs text-slate-500">{item.product_id} · Qty {item.quantity ?? 1}</p>
              </div>
              <p className="text-sm font-semibold text-slate-900">{formatCurrency(item.final_price)}</p>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600">
              <p>Unit: {formatCurrency(item?.price_points?.unit_price ?? item?.unit_price)}</p>
              <p>Extended: {formatCurrency(item?.price_points?.extended_price ?? item?.extended_price)}</p>
              <p>Discount: {formatCurrency(item.discount)}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Savings Summary - itemized discount breakdown */}
      {discountBreakdown.length > 0 && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700 mb-2">
            Your Savings
          </p>
          <div className="space-y-1.5">
            {discountBreakdown.map((d) => (
              <div key={d.type} className="flex items-center justify-between text-sm">
                <span className="text-emerald-800 flex items-center gap-1.5">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  {d.label ?? d.type}
                  {d.rate_display && <span className="text-xs text-emerald-600">({d.rate_display})</span>}
                </span>
                <span className="font-medium text-emerald-900">-{formatCurrency(d.amount)}</span>
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between border-t border-emerald-200 pt-2 text-sm font-semibold text-emerald-900">
            <span>Total Savings</span>
            <span>-{formatCurrency(quote.total_discount)}</span>
          </div>
        </div>
      )}

      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
        <div className="flex items-center justify-between text-slate-700">
          <span>Subtotal</span>
          <span>{formatCurrency(quote.subtotal)}</span>
        </div>
        {/* Fallback: show single total discount if no breakdown available */}
        {discountBreakdown.length === 0 && (
          <div className="mt-1 flex items-center justify-between text-slate-700">
            <span>Total Discount</span>
            <span>-{formatCurrency(quote.total_discount)}</span>
          </div>
        )}
        <div className="mt-2 flex items-center justify-between border-t border-slate-200 pt-2 text-base font-semibold text-slate-900">
          <span>Monthly Total</span>
          <span>{formatCurrency(monthlyTotal)}</span>
        </div>
        <div className="mt-2 flex items-center justify-between border-t border-slate-200 pt-2 text-base font-semibold text-slate-900">
          <span>Yearly Total</span>
          <span>{formatCurrency(yearlyTotal)}</span>
        </div>
      </div>
    </div>
  );
}
