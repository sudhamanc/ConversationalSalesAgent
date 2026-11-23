# generative-ui Specification

## Purpose
Interactive UI in the sales chat: the gateway builds A2UI 1.0 surfaces deterministically from remote tool results (no model writes UI), streams them as SSE `a2ui` events, and the React client renders them inside the conversation with CopilotKit's standard catalog. Surface buttons send customer-voice chat messages. Introduced by `a2ui-generative-cards`; extended by `guided-checkout`.
## Requirements
### Requirement: A2UI surfaces from tool results

When `A2UI_ENABLED` is not `false`, the gateway SHALL emit one SSE event `{"type": "a2ui", "surface_id", "tool", "author", "operations"}` for each successful remote result of a quote tool (`generate_offer_quote`, `find_best_bundle_offer`, `get_quote_details` with an `offer_id`), of `check_service_availability`, and of a product listing tool (`list_available_products`, `search_products_by_criteria` with at least one product, `compare_products`). `operations` SHALL be A2UI 1.0 operations (`version` `"1.0"`) whose first operation is `createSurface` with a component whose id is `root`. Every component SHALL be a component of CopilotKit's standard catalog with its required props. All values SHALL come from the tool result; the gateway SHALL NOT call a model to build a surface. Product surfaces SHALL NOT contain prices. A failed or unrecognized tool result SHALL produce no `a2ui` event. When `A2UI_ENABLED` is `false`, no `a2ui` event SHALL be emitted and the other events are unchanged.

#### Scenario: Quote surface
- **WHEN** `generate_offer_quote` returns `offer_id` `OFF-1` with two items and `monthly_total` 450.0
- **THEN** the stream contains an `a2ui` event with `tool` `generate_offer_quote` whose surface shows both items and the monthly total

#### Scenario: Serviceability from an MCP result
- **WHEN** `check_service_availability` returns an MCP result whose `structuredContent` has `serviceable: true`, `infrastructure_type` `FTTP` and `max_speed_mbps` 5000
- **THEN** the stream contains an `a2ui` event whose surface states that service is available with FTTP up to 5000 Mbps

#### Scenario: Product surface without prices
- **WHEN** `list_available_products` returns three products
- **THEN** the `a2ui` surface lists the three products and contains no price

#### Scenario: Disabled
- **WHEN** `A2UI_ENABLED=false` and a quote is generated
- **THEN** the stream contains the `structured_card` event and no `a2ui` event

### Requirement: Surface actions send customer messages

Every Button in a gateway-built surface SHALL bind its action to the client function `sendChatMessage` with a non-empty, first-person customer `message` authored by the gateway. When the customer clicks the button, the UI SHALL send that message as the customer's next chat message, exactly as if typed, while no reply is streaming.

#### Scenario: Accepting a quote from the card
- **WHEN** the customer clicks "Accept this quote and place my order" on a quote surface
- **THEN** the chat shows that text as the customer's message and sends it to `POST /api/chat`

### Requirement: Surfaces render in the chat with the standard catalog

The UI SHALL render each `a2ui` event inside the assistant message of that turn with CopilotKit's standard catalog (`standardUI`, extended only by the `sendChatMessage` function), themed with `--a2ui-*` variables matching the app. A message that has an A2UI surface for a quote, serviceability result or product list SHALL NOT also render the legacy card of the same kind. Messages without a surface SHALL render as before. The UI SHALL NOT require a CopilotKit runtime or send requests to one.

#### Scenario: Quote surface replaces the legacy quote card
- **WHEN** a turn delivers both a `structured_card` quote and an `a2ui` quote surface
- **THEN** the assistant message shows the A2UI surface and not `QuoteCard`

