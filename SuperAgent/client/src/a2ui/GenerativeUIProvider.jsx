import { CopilotKitProvider } from "@copilotkit/react-core/v2";
import { salesUI } from "./salesUI";
import { salesTheme } from "./theme";
import { InertAgent } from "./InertAgent";

// Stable across renders (CopilotKit warns about changing agent maps).
const AGENTS = { default: new InertAgent() };
const GENERATIVE_UI = { ui: salesUI, theme: salesTheme };

/**
 * CopilotKit's generative UI runtime for A2UI surfaces in the sales chat.
 * No CopilotKit runtime or chat is used (see InertAgent).
 */
export default function GenerativeUIProvider({ children }) {
  return (
    <CopilotKitProvider
      agents__unsafe_dev_only={AGENTS}
      generativeUI={GENERATIVE_UI}
      showIntelligenceIndicator={false}
      enableInspector={false}
    >
      {children}
    </CopilotKitProvider>
  );
}
