## ADDED Requirements

### Requirement: Notification dispatch endpoint

The customer communication service SHALL serve `POST /dispatch`, without calling a model: it delivers the due pending notifications within the request (the same delivery as the background loop, safe to run concurrently with it) and returns `{"success": true, "processed", "sent", "simulated", "deduped", "retrying", "failed"}`. On Cloud Run the endpoint SHALL be private like every agent service.

#### Scenario: Pending rows delivered on request
- **WHEN** two `pending` notifications exist and `POST /dispatch` is called
- **THEN** the response reports `processed: 2` and both rows are no longer `pending`

### Requirement: Agents warm their tool services at startup

An agent service SHALL, when it starts, send a `GET` in the background to the endpoint of each configured MCP dependency (environment variables ending in `_MCP_URL`), with service authentication; any response from the tool service counts as warmed. Failures SHALL NOT delay or fail startup.

#### Scenario: Product agent cold start
- **WHEN** the product agent starts with `CATALOG_MCP_URL=https://csa-catalog-…/mcp/`
- **THEN** it sends `GET https://csa-catalog-…/mcp/` without waiting for the response before serving

### Requirement: Producer tools report the queued notification id

Every tool that queues an outbox notification SHALL return its `notification_id` (order: `email_notification_id`) in the result, next to any boolean flag, so the gateway can report the notification's delivery status. This covers `schedule_installation`, `dispatch_technician`, `complete_installation` and `activate_service` in service fulfillment.

#### Scenario: Installation booked
- **WHEN** `schedule_installation` books an appointment and queues `installation_scheduled`
- **THEN** its result contains `notification_queued: true` and the row's `notification_id`

### Requirement: Installation emails show the time window

The `installation_scheduled` email SHALL show the booked time window as a readable range built from `start_time` and `end_time` (for example `1 PM–5 PM (afternoon)`), not the bare window code (`PM`); without times it SHALL fall back to the window name.

#### Scenario: Afternoon window
- **WHEN** the notification args are `window: "PM"`, `start_time: "13:00"`, `end_time: "17:00"`
- **THEN** the email reads `Time Window: 1 PM–5 PM (afternoon)`
