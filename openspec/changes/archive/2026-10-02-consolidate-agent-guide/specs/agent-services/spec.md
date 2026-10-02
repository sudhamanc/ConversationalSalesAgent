# Spec Delta: agent-services

## ADDED Requirements

### Requirement: Agent service pattern documented in README

README.md SHALL contain the "Agent Service Guide" section, the single description of how an agent service is built: layout, `agent.py`, `server.py`, journey context, database access, notifications, prompts, tests and golden evals, Dockerfile, environment variables. Other docs SHALL link to it instead of a separate guide or a template folder.

#### Scenario: New agent
- **WHEN** a developer adds an agent
- **THEN** README "Agent Service Guide" gives the layout and templates, and no other template folder exists
