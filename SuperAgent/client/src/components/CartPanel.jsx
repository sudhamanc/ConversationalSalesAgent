import React from "react";
import { useChatContext } from "../contexts/ChatContext";
import CartItem from "./CartItem";

export default function CartPanel() {
  const { cart } = useChatContext();

  // Don't render if no cart or empty
  if (!cart || !cart.items || cart.items.length === 0) return null;

  return (
    <div
      id="cart-panel"
      className="w-80 flex-shrink-0 bg-white flex flex-col overflow-hidden border-l border-slate-200"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 flex items-center gap-2">
        <svg
          className="w-5 h-5 text-primary-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"
          />
        </svg>
        <h2 className="text-sm font-semibold text-slate-700">Shopping Cart</h2>
        <span className="ml-auto bg-primary-100 text-primary-700 text-xs font-medium px-2 py-0.5 rounded-full">
          {cart.items.length}
        </span>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-3">
        {cart.items.map((item, i) => (
          <CartItem key={`${item.service_type}-${i}`} item={item} />
        ))}
      </div>

      {/* Total */}
      <div className="border-t border-slate-200 px-4 py-3">
        {cart.discount_amount > 0 && (
          <div className="flex justify-between items-baseline mb-1">
            <span className="text-xs text-green-600">Discount</span>
            <span className="text-xs font-medium text-green-600">
              -${cart.discount_amount.toFixed(2)}
            </span>
          </div>
        )}
        <div className="flex justify-between items-baseline">
          <span className="text-sm font-medium text-slate-600">
            Monthly Total
          </span>
          <span className="text-lg font-bold text-slate-900">
            ${cart.total_amount?.toFixed(2)}/mo
          </span>
        </div>
      </div>
    </div>
  );
}
