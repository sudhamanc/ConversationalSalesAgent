import React from "react";
import { getAgentInfo } from "../utils/agentLabels";

export default function JourneyStep({ step }) {
  const agentInfo = getAgentInfo(step.agent);

  return (
    <div className="rounded-lg bg-white border border-slate-200 p-3 text-xs">
      {/* Step number + agent badge */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-slate-400 font-mono">#{step.stepNumber}</span>
        {step.agent && (
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${agentInfo.badgeBg} ${agentInfo.badgeText}`}
          >
            {agentInfo.label}
          </span>
        )}
      </div>

      {/* User action */}
      <p className="text-slate-600 mb-1 truncate">
        <span className="font-medium text-slate-500">You: </span>
        {step.userMessage}
      </p>

      {/* Agent response summary */}
      {step.agentSummary && (
        <p className="text-slate-500 line-clamp-2">
          <span className="font-medium">Agent: </span>
          {step.agentSummary}
        </p>
      )}

      {/* Streaming indicator */}
      {step.status === "streaming" && (
        <div className="mt-1.5 flex items-center gap-1.5 text-primary-500">
          <span className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-pulse" />
          <span>Processing...</span>
        </div>
      )}
    </div>
  );
}
