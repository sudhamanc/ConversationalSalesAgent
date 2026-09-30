"""Shared runtime library for the Conversational Sales Agent services.

Modules
-------
config        Fail-fast environment configuration and model settings
logging       Service logging setup and secret masking
db            PostgreSQL connection pool and query helpers (psycopg 3)
migrate       SQL migration + seed runner (``python -m sales_common.migrate``)
context       Journey-context forwarding across the A2A boundary
adk_app       ADK ``App`` factory (context compaction + model context caching)
a2a_server    ``to_a2a`` service factory with durable sessions and task store
a2a_client    ``RemoteA2aAgent`` factory for the gateway
mcp_client    ``McpToolset`` factory for agents consuming tool services
auth          Service-to-service authentication (Google ID tokens)
memory        PostgreSQL-backed ADK ``BaseMemoryService``
notifications Transactional notification outbox
repositories  Cross-domain SQL helpers shared by several agents
maintenance   Periodic stale-record cleanup
"""

__version__ = "2.0.0"
