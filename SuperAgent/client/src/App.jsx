import React from "react";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-3xl h-[90vh] flex flex-col bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <header className="flex items-center gap-3 px-6 py-4 border-b border-slate-200 bg-white">
          <div className="w-10 h-10 rounded-full bg-primary-600 flex items-center justify-center text-white font-bold text-lg">
            S
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-900">
              SuperAgent
            </h1>
            <p className="text-xs text-slate-500">
              B2B Sales Assistant &middot; Powered by Gemini
            </p>
          </div>
        </header>

        {/* Chat area */}
        <ChatWindow />
      </div>
    </div>
  );
}
