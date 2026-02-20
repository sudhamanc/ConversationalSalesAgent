import React from "react";

export default function CartItem({ item }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="flex justify-between items-start">
        <div className="min-w-0 flex-1 mr-2">
          <p className="text-sm font-medium text-slate-800 truncate">
            {item.service_type}
          </p>
          {item.quantity > 1 && (
            <p className="text-xs text-slate-500 mt-0.5">
              Qty: {item.quantity} &times; ${item.price?.toFixed(2)}
            </p>
          )}
        </div>
        <p className="text-sm font-semibold text-slate-900 flex-shrink-0">
          ${item.subtotal?.toFixed(2)}/mo
        </p>
      </div>
      {item.quantity <= 1 && (
        <p className="text-xs text-slate-400 mt-1">
          ${item.price?.toFixed(2)}/mo
        </p>
      )}
    </div>
  );
}
