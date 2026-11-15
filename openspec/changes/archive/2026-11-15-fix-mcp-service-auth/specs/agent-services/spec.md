## MODIFIED Requirements

### Requirement: Service authentication in cloud

When `SERVICE_AUTH=gcp_id_token`, callers SHALL attach a Google-signed ID token whose audience is the target service URL. This SHALL apply to every service-to-service request: A2A calls from the gateway, and every MCP request from an agent to a tool service, including session setup and tool listing that happen outside a request context. Agent and tool services SHALL NOT be publicly invokable. When `SERVICE_AUTH=none` (local), no token is attached.

#### Scenario: Unauthenticated call rejected in cloud
- **WHEN** an anonymous request reaches a deployed agent service
- **THEN** Cloud Run rejects it with HTTP 403 before it reaches the agent

#### Scenario: MCP tools load on a cold instance
- **WHEN** a freshly started agent instance lists its MCP tools before handling any request
- **THEN** the request carries `Authorization: Bearer <ID token for the tool service URL>` and the tools load
