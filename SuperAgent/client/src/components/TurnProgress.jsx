import React, { useEffect, useState } from "react";
import { progressLabel } from "../utils/agentLabels";

/** After this long on one step, explain that a service may be starting (Cloud Run cold start). */
const SLOW_STEP_MS = 10000;

/**
 * Status line shown for the whole turn, until `done` or `error`
 * (spec: conversation-orchestration, turn progress events): what the assistant is
 * doing now (from SSE `progress`) and how long the turn has taken.
 */
export default function TurnProgress({ progress }) {
  // Mounted for exactly one turn (ChatWindow renders it while a reply streams).
  const [turnStartedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const elapsed = Math.max(0, Math.floor((now - turnStartedAt) / 1000));
  const stepSlow = progress?.since && now - progress.since > SLOW_STEP_MS;

  return (
    <div className="flex justify-start" role="status" aria-live="polite">
      <div className="w-8 h-8 rounded-full bg-primary-100 flex-shrink-0 flex items-center justify-center mr-2 mt-1">
        <span className="text-primary-700 text-xs font-bold">SA</span>
      </div>
      <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[80%]">
        <div className="flex items-center gap-2 text-sm text-slate-700">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary-600" />
          </span>
          <span>{progressLabel(progress)}</span>
          <span className="text-xs text-slate-400 tabular-nums">{elapsed}s</span>
        </div>
        {stepSlow && (
          <p className="mt-1 text-xs text-slate-500">
            Starting a service can take up to a minute the first time. Still working…
          </p>
        )}
      </div>
    </div>
  );
}
