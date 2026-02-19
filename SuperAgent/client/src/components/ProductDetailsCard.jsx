import React from "react";

function DetailRow({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-3 text-xs">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-800">{value}</span>
    </div>
  );
}

export default function ProductDetailsCard({ payload }) {
  const products = Array.isArray(payload?.products) ? payload.products : [];
  const outroLines = Array.isArray(payload?.outroLines) ? payload.outroLines : [];

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="border-b border-slate-100 pb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Product Specifications</p>
        {payload?.intro && <p className="mt-1 text-sm text-slate-700">{payload.intro}</p>}
      </div>

      <div className="mt-4 space-y-3">
        {products.map((product) => (
          <div key={`${product.productId}-${product.title}`} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-slate-900">{product.title}</p>
              {product.productId && (
                <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                  {product.productId}
                </span>
              )}
            </div>

            {product.description && <p className="mt-1 text-xs text-slate-700">{product.description}</p>}

            {product.attributes?.length > 0 && (
              <div className="mt-3 space-y-1.5">
                {product.attributes.map((item, index) => (
                  <DetailRow key={`${product.productId}-${item.label}-${index}`} label={item.label} value={item.value} />
                ))}
              </div>
            )}

            {product.features?.length > 0 && (
              <div className="mt-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Highlights</p>
                <ul className="space-y-1">
                  {product.features.map((feature, index) => (
                    <li key={`${product.productId}-f-${index}`} className="flex items-start gap-2 text-xs text-slate-700">
                      <span className="mt-1 text-slate-400">•</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {outroLines.length > 0 && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Next Steps</p>
          <ul className="space-y-1">
            {outroLines.map((line, index) => (
              <li key={`outro-${index}`} className="flex items-start gap-2 text-xs text-slate-700">
                <span className="mt-1 text-slate-400">•</span>
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
