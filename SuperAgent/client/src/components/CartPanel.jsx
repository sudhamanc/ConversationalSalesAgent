import React from "react";
import { useChatContext } from "../contexts/ChatContext";
import CartItem from "./CartItem";

const APP_VERSION = "1.2.0";

function Section({ title, icon, children, badge }) {
  return (
    <div className="border-b border-slate-100 last:border-b-0">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-50">
        <span className="text-sm">{icon}</span>
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">{title}</h3>
        {badge && (
          <span className="ml-auto bg-primary-100 text-primary-700 text-[10px] font-medium px-1.5 py-0.5 rounded-full">
            {badge}
          </span>
        )}
      </div>
      <div className="px-4 py-2.5 space-y-1.5">{children}</div>
    </div>
  );
}

function DetailRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-baseline gap-2">
      <span className="text-[11px] text-slate-500">{label}</span>
      <span className={`text-[11px] font-medium text-right truncate max-w-[55%] ${highlight ? "text-green-600" : "text-slate-700"}`}>
        {value}
      </span>
    </div>
  );
}

export default function CartPanel() {
  const { cart, activities } = useChatContext();
  const { quote, order, scheduling, payment, fulfillment, notifications } = activities;

  const hasContent = cart?.items?.length > 0 || quote || order || scheduling || payment || fulfillment?.length > 0 || notifications?.length > 0;

  if (!hasContent) return null;

  return (
    <div
      id="cart-panel"
      className="w-80 flex-shrink-0 bg-white flex flex-col overflow-hidden border-l border-slate-200"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 flex items-center gap-2">
        <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
        </svg>
        <h2 className="text-sm font-semibold text-slate-700">Activity Summary</h2>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto chat-scroll">

        {/* Customer Context (show at top once known) */}
        {(() => {
          const customerId = order?.customer_id || quote?.customer_id || activities?.customer?.customer_id;
          const customerName = order?.customer_name || quote?.company_name || activities?.customer?.company_name;
          if (!customerId && !customerName) return null;
          return (
            <div className="px-4 py-2.5 border-b border-slate-200 bg-primary-50/50">
              <div className="flex items-center gap-2">
                <span className="text-sm">👤</span>
                <div className="min-w-0 flex-1">
                  {customerName && <div className="text-xs font-semibold text-slate-700 truncate">{customerName}</div>}
                  {customerId && <div className="text-[10px] text-slate-500 font-mono">{customerId}</div>}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Cart Section */}
        {cart?.items?.length > 0 && (
          <Section title="Shopping Cart" icon="🛒" badge={cart.items.length}>
            <div className="space-y-2">
              {cart.items.map((item, i) => (
                <CartItem key={`${item.service_type}-${i}`} item={item} />
              ))}
            </div>
            {cart.discount_amount > 0 && (
              <DetailRow label="Discount" value={`-$${cart.discount_amount.toFixed(2)}`} highlight />
            )}
            <div className="flex justify-between items-baseline pt-1.5 border-t border-slate-100 mt-1.5">
              <span className="text-xs font-medium text-slate-600">Monthly Total</span>
              <span className="text-sm font-bold text-slate-900">${cart.total_amount?.toFixed(2)}/mo</span>
            </div>
          </Section>
        )}

        {/* Quote Section */}
        {quote && (
          <Section title="Quote" icon="📋">
            {quote.offer_id && <DetailRow label="Offer ID" value={quote.offer_id} />}
            {quote.term_months && <DetailRow label="Term" value={`${quote.term_months} months`} />}
            {quote.company_name && <DetailRow label="Customer" value={quote.company_name} />}

            {/* Line items */}
            {quote.items?.map((item, i) => (
              <div key={i} className="rounded border border-slate-100 p-2 mt-1.5">
                <div className="flex justify-between items-baseline">
                  <span className="text-[11px] font-semibold text-slate-700">{item.product_name || item.product_id}</span>
                  {item.quantity > 1 && <span className="text-[10px] text-slate-400">×{item.quantity}</span>}
                </div>
                {item.price_points?.unit_price && (
                  <DetailRow label="List Price" value={`$${item.price_points.unit_price.toFixed(2)}/mo`} />
                )}
                {item.discount > 0 && (
                  <DetailRow label="Discount" value={`-$${item.discount.toFixed(2)}`} highlight />
                )}
                <DetailRow label="Final Price" value={`$${(item.final_price || 0).toFixed(2)}/mo`} />
              </div>
            ))}

            {/* Discount breakdown */}
            {quote.discount_breakdown?.length > 0 && (
              <div className="mt-2 pt-1.5 border-t border-slate-100">
                <span className="text-[10px] font-semibold text-slate-500 uppercase">Savings</span>
                {quote.discount_breakdown.map((d, i) => (
                  <div key={i} className="flex justify-between items-baseline mt-0.5">
                    <span className="text-[10px] text-green-600 flex-1 mr-1 truncate">{d.label} ({d.rate_display})</span>
                    <span className="text-[10px] font-medium text-green-600">-${d.amount?.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Totals */}
            <div className="mt-2 pt-1.5 border-t border-slate-100 space-y-1">
              {quote.subtotal && quote.total_discount > 0 && (
                <DetailRow label="Subtotal" value={`$${quote.subtotal.toFixed(2)}/mo`} />
              )}
              {quote.total_discount > 0 && (
                <DetailRow label="Total Savings" value={`-$${quote.total_discount.toFixed(2)}/mo`} highlight />
              )}
              <div className="flex justify-between items-baseline">
                <span className="text-xs font-medium text-slate-600">Monthly Total</span>
                <span className="text-sm font-bold text-slate-900">${(quote.monthly_total || quote.total_price || 0).toFixed(2)}/mo</span>
              </div>
              {quote.yearly_total && (
                <DetailRow label="Annual Total" value={`$${quote.yearly_total.toFixed(2)}/yr`} />
              )}
            </div>
          </Section>
        )}

        {/* Order Section */}
        {order && (
          <Section title="Order" icon="📦">
            {order.order_id && <DetailRow label="Order ID" value={order.order_id} />}
            {order.status && <DetailRow label="Status" value={order.status} highlight={order.status === "confirmed"} />}
            {order.customer_name && <DetailRow label="Customer" value={order.customer_name} />}
            {order.service_type && <DetailRow label="Service" value={order.service_type} />}
            {order.service_address && <DetailRow label="Address" value={order.service_address} />}
            {order.total_amount && <DetailRow label="Monthly" value={`$${order.total_amount}/mo`} />}
            {order.payment_status && <DetailRow label="Payment" value={order.payment_status} highlight={order.payment_status === "paid"} />}
          </Section>
        )}

        {/* Payment Section */}
        {payment && (
          <Section title="Payment" icon="💳">
            {payment.transaction_id && <DetailRow label="Transaction" value={payment.transaction_id} />}
            {payment.amount && <DetailRow label="Amount" value={`$${Number(payment.amount).toFixed(2)}`} />}
            {payment.status && <DetailRow label="Status" value={payment.status === "approved" ? "✅ Approved" : payment.status} highlight={payment.status === "approved"} />}
            {payment.payment_method_token && <DetailRow label="Method" value={payment.payment_method_token} />}
          </Section>
        )}

        {/* Scheduling Section */}
        {scheduling && (
          <Section title="Installation" icon="📅">
            {scheduling.appointment_id && <DetailRow label="Appointment" value={scheduling.appointment_id} />}
            {scheduling.scheduled_date && <DetailRow label="Date" value={scheduling.scheduled_date} />}
            {scheduling.window && <DetailRow label="Window" value={scheduling.window === "AM" ? "8AM – 12PM" : "1PM – 5PM"} />}
            {scheduling.service_address && <DetailRow label="Address" value={scheduling.service_address} />}
            {scheduling.status && <DetailRow label="Status" value={scheduling.status} highlight />}
          </Section>
        )}

        {/* Fulfillment Section */}
        {fulfillment?.length > 0 && (
          <Section title="Fulfillment" icon="⚡" badge={fulfillment.length}>
            {fulfillment.map((step, i) => {
              const toolLabel = {
                provision_equipment: "Equipment",
                dispatch_technician: "Technician",
                activate_service: "Activation",
                run_service_tests: "Tests",
              }[step.tool] || step.tool;
              return (
                <div key={i} className="rounded border border-slate-100 p-2 mb-1.5 last:mb-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-green-500 text-xs">✓</span>
                    <span className="text-[11px] font-semibold text-slate-700">{toolLabel}</span>
                  </div>
                  {step.tool === "provision_equipment" && step.equipment_items && step.equipment_items.map((eq, j) => (
                    <DetailRow key={j} label={eq.type || "Equipment"} value={`${eq.model || ""} ${eq.tracking_number ? `• ${eq.tracking_number}` : ""}`} />
                  ))}
                  {step.tool === "provision_equipment" && step.estimated_delivery && (
                    <DetailRow label="Delivery" value={step.estimated_delivery.split("T")[0]} />
                  )}
                  {step.tool === "dispatch_technician" && (
                    <>
                      {step.technician_name && <DetailRow label="Technician" value={step.technician_name} />}
                      {step.dispatch_id && <DetailRow label="Dispatch ID" value={step.dispatch_id} />}
                    </>
                  )}
                  {step.tool === "activate_service" && (
                    <>
                      {step.circuit_id && <DetailRow label="Circuit" value={step.circuit_id} />}
                      {step.account_id && <DetailRow label="Account" value={step.account_id} />}
                      {step.ip_address && <DetailRow label="IP" value={step.ip_address} />}
                    </>
                  )}
                  {step.tool === "run_service_tests" && step.results && (
                    <>
                      {step.results.download_speed && <DetailRow label="Download" value={`${step.results.download_speed} Mbps`} highlight />}
                      {step.results.upload_speed && <DetailRow label="Upload" value={`${step.results.upload_speed} Mbps`} highlight />}
                      {step.results.latency && <DetailRow label="Latency" value={`${step.results.latency} ms`} highlight />}
                    </>
                  )}
                </div>
              );
            })}
          </Section>
        )}

        {/* Notifications Section */}
        {notifications?.length > 0 && (
          <Section title="Notifications" icon="🔔" badge={notifications.length}>
            {notifications.map((notif, i) => {
              const label = (notif.tool || "")
                .replace("send_", "")
                .replace(/_/g, " ")
                .replace(/\b\w/g, (c) => c.toUpperCase());
              return (
                <div key={i} className="flex items-center gap-2 py-1">
                  <span className="text-green-500 text-[11px]">✓</span>
                  <span className="text-[11px] text-slate-700 flex-1 truncate">{label}</span>
                  <span className="text-[10px] text-slate-400">
                    {notif.status || "sent"}
                  </span>
                </div>
              );
            })}
          </Section>
        )}
      </div>

      {/* Version footer */}
      <div className="px-4 py-1.5 border-t border-slate-100 bg-slate-50">
        <span className="text-[10px] text-slate-400">v{APP_VERSION}</span>
      </div>
    </div>
  );
}
