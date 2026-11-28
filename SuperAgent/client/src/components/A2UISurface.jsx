import { useLayoutEffect, useMemo } from "react";
import { GenerativeUISurface, useGenerativeUIRuntime } from "@copilotkit/react-core/v2/generative-ui";
import { salesUI } from "../a2ui/salesUI";
import { actedOperations } from "../a2ui/actedSurface";

/** One CopilotKit thread holds every surface of the sales chat. */
export const A2UI_THREAD_ID = "sales-chat";

/**
 * Renders one A2UI surface from an `a2ui` SSE event (spec: generative-ui).
 *
 * The gateway builds the surface from a tool result; its operations are
 * ingested into CopilotKit's generative UI runtime and drawn with the standard
 * catalog. Each surface is its own target (its `surface_id`), so it stays in
 * the message it arrived with. Buttons call `sendChatMessage` (ChatContext).
 * After a click, `surface.actions` (the click history kept by ChatContext) adds
 * `updateComponents` operations that show the choice as pending, done or
 * restored (`a2ui/actedSurface.js`).
 */
export default function A2UISurface({ surface }) {
  const runtime = useGenerativeUIRuntime();
  const surfaceId = surface?.surface_id;
  const operations = useMemo(
    () => actedOperations(surface?.operations, surface?.actions, surface?.kind),
    [surface?.operations, surface?.actions, surface?.kind]
  );

  useLayoutEffect(() => {
    if (!runtime || !surfaceId || !Array.isArray(operations)) return;
    runtime.manager.setActiveThread(A2UI_THREAD_ID);
    runtime.manager.ingest(A2UI_THREAD_ID, undefined, {
      surfaceId,
      target: surfaceId,
      operations,
      status: "ready",
      rejected: [],
    });
  }, [runtime, surfaceId, operations]);

  if (!runtime || !surfaceId) return null;
  return (
    <GenerativeUISurface
      id={surfaceId}
      ui={salesUI}
      autoScroll={false}
      className="mt-3 w-full"
    />
  );
}
