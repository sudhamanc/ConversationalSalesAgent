import React from "react";

function InfoRow({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-3 text-xs">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-800">{value}</span>
    </div>
  );
}

export default function ServiceabilityCard({ details }) {
  const statusTone = details.isServiceable
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : "bg-rose-50 text-rose-700 border-rose-200";

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Serviceability Check</p>
          {details.heading && <p className="text-sm text-slate-700">{details.heading}</p>}
        </div>
        {details.isServiceable !== null && (
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone}`}>
            {details.isServiceable ? "Serviceable" : "Not Serviceable"}
          </span>
        )}
      </div>

      {details.summary && <p className="mt-3 text-sm text-slate-800">{details.summary}</p>}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Infrastructure</p>
          <div className="mt-2 space-y-1.5">
            <InfoRow label="Type" value={details.infrastructureType} />
            <InfoRow label="Zone" value={details.serviceZone} />
            <InfoRow label="Switch" value={details.switchId} />
            <InfoRow label="Cabinet" value={details.cabinetId} />
            <InfoRow label="Fiber Pairs" value={details.availableFiberPairs} />
            <InfoRow label="OLT" value={details.oltEquipment} />
          </div>
        </div>

        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Speed & SLA</p>
          <div className="mt-2 space-y-1.5">
            <InfoRow label="Minimum" value={details.minimumSpeed} />
            <InfoRow label="Maximum" value={details.maximumSpeed} />
            <InfoRow label="Symmetrical" value={details.symmetrical} />
            <InfoRow label="Service Class" value={details.serviceClass} />
            <InfoRow label="Redundancy" value={details.redundancy} />
            <InfoRow label="Install Timeline" value={details.installationTimeline} />
          </div>
        </div>
      </div>

      {details.products?.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Available Products</p>
          <div className="grid gap-2 md:grid-cols-2">
            {details.products.map((product) => (
              <div key={product.id} className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                <p className="text-xs font-semibold text-slate-900">{product.id}</p>
                <p className="text-xs text-slate-600">{product.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
