import React, { useState } from "react";
import { ChatProvider } from "./contexts/ChatContext";
import JourneySidebar from "./components/JourneySidebar";
import ChatWindow from "./components/ChatWindow";
import CartPanel from "./components/CartPanel";

export default function App() {
  const [exportChatPdf, setExportChatPdf] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [includeJourneyInPdf, setIncludeJourneyInPdf] = useState(true);
  const [includeCartInPdf, setIncludeCartInPdf] = useState(true);

  const handleExportPdfClick = async () => {
    if (!exportChatPdf || isExporting) return;
    try {
      setIsExporting(true);
      await exportChatPdf({
        includeJourney: includeJourneyInPdf,
        includeCart: includeCartInPdf,
      });
    } catch (error) {
      console.error("PDF export failed:", error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <ChatProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
        <div className="w-full max-w-7xl h-[95vh] flex bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
          {/* Left sidebar — Journey Summary */}
          <JourneySidebar />

          {/* Center — Chat */}
          <div className="flex-1 flex flex-col min-w-0 border-l border-slate-200">
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

              <div className="ml-auto flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={includeJourneyInPdf}
                    onChange={(event) => setIncludeJourneyInPdf(event.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  />
                  Journey
                </label>

                <label className="flex items-center gap-1.5 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={includeCartInPdf}
                    onChange={(event) => setIncludeCartInPdf(event.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  />
                  Cart
                </label>

                <button
                  type="button"
                  onClick={handleExportPdfClick}
                  disabled={!exportChatPdf || isExporting}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isExporting ? "Exporting..." : "Export PDF"}
                </button>
              </div>
            </header>

            {/* Chat area */}
            <ChatWindow onRegisterExport={setExportChatPdf} />
          </div>

          {/* Right panel — Cart (conditional) */}
          <CartPanel />
        </div>
      </div>
    </ChatProvider>
  );
}
