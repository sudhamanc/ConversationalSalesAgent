import React from "react";
import { useChatContext } from "../contexts/ChatContext";
import JourneyStep from "./JourneyStep";

export default function JourneySidebar() {
  const { journeySteps, isSidebarOpen } = useChatContext();

  if (!isSidebarOpen) return null;

  return (
    <div
      id="journey-sidebar-panel"
      className="w-72 flex-shrink-0 bg-slate-50 flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-700">
          Journey Summary
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          {journeySteps.length} {journeySteps.length === 1 ? "step" : "steps"}
        </p>
      </div>

      {/* Steps list */}
      <div className="flex-1 overflow-y-auto chat-scroll px-3 py-3 space-y-2">
        {journeySteps.length === 0 && (
          <p className="text-xs text-slate-400 text-center mt-8">
            Steps will appear as the conversation progresses.
          </p>
        )}

        {journeySteps.map((step) => (
          <JourneyStep key={step.stepNumber} step={step} />
        ))}
      </div>
    </div>
  );
}
