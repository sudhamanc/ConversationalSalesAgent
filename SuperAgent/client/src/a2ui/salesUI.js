/**
 * The generative UI of the sales chat: CopilotKit's standard A2UI catalog
 * (`standardUI`, 69 components), the app's `SecurePaymentForm` and one client
 * function.
 *
 * `sendChatMessage` is what every gateway-built Button calls
 * (`action: {functionCall: {"@call": "sendChatMessage", args: {message}}}`):
 * the click sends `message` as the customer's next chat message. The handler
 * is mounted with `useGenerativeUIFunction` in `ChatContext`.
 *
 * The A2UI 1.0 catalog of this UI is exported to
 * `SuperAgent/server/a2ui/catalog.json` by `scripts/export_a2ui_catalog.mjs`;
 * gateway tests validate surfaces against it.
 */
import { z } from "zod";
import { createGenerativeUI, standardUI } from "@copilotkit/react-core/v2/generative-ui";
import SecurePaymentForm from "./SecurePaymentForm";

export const SALES_UI_ID = "connectivitymax/sales@1";

export const salesUI = createGenerativeUI({
  id: SALES_UI_ID,
  extends: [standardUI],
  functions: {
    sendChatMessage: {
      description: "Send a message to the sales assistant as the customer's next chat message.",
      parameters: z.object({ message: z.string().min(1) }),
      requiresUserActivation: true,
    },
  },
  components: {
    // Card/bank entry that bypasses the chat and the model (spec: guided-checkout).
    SecurePaymentForm: {
      component: SecurePaymentForm,
      description:
        "Secure card or bank account entry. Details are tokenized by the payment service and never reach the assistant.",
      props: z.object({
        amount: z.string().optional().describe("Amount due, formatted, e.g. $224.10"),
        title: z.string().optional().describe("Heading of the form"),
      }),
    },
  },
});
