import { AbstractAgent } from "@ag-ui/client";
import { EMPTY } from "rxjs";

/**
 * A local CopilotKit agent that never does anything.
 *
 * `CopilotKitProvider` needs a `runtimeUrl`, a public key or a local agent
 * (production builds throw without one). This app has no CopilotKit runtime:
 * replies come from the ADK gateway over `/api/chat`, and A2UI surfaces are
 * ingested from its `a2ui` SSE events. So the provider gets this agent, which
 * holds no keys and completes immediately if anything ever runs it.
 */
export class InertAgent extends AbstractAgent {
  constructor() {
    super({ agentId: "default", description: "Placeholder: the sales chat talks to the ADK gateway." });
  }

  run() {
    return EMPTY;
  }

  clone() {
    return new InertAgent();
  }
}
