# Service Fulfillment Agent

A deterministic, tool-based ADK agent for handling service fulfillment operations in the B2B telecommunications process.

## Overview

The Service Fulfillment Agent is responsible for:
- Order scheduling and coordination
- Installation appointment management
- Equipment provisioning and tracking
- Service activation and testing
- Completion verification and handoff

## Features

- **Order Management**: Tracks orders from placement to completion
- **Scheduling**: Manages installation appointments and technician dispatch
- **Equipment Tracking**: Monitors equipment provisioning and delivery
- **Service Activation**: Coordinates service turn-up and testing
- **Deterministic**: Temperature set to 0.0 for reliable fulfillment operations

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Run the agent
python main.py
```

## Usage

```python
from service_fulfillment_agent import get_agent

agent = get_agent()

# Schedule installation
response = agent.run("Schedule installation for 123 Main St next Tuesday")

# Check order status
response = agent.run("What's the status of order #12345?")
```

## Integration

This agent is designed to integrate with the Super Agent orchestration system as a sub-agent for the Fulfillment cluster.

## Architecture

- **Agent**: ADK-based tool agent with deterministic configuration
- **Tools**: Scheduling, equipment tracking, service activation
- **Models**: Pydantic schemas for order and appointment data
- **Utils**: Logging, caching, and integration with backend systems

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_agent.py
```

## Environment Variables

See `.env.example` for required configuration:
- `GEMINI_MODEL`: Gemini model to use (default: gemini-2.0-flash)
- `AGENT_NAME`: Agent identifier (default: service_fulfillment_agent)
- Scheduling system API credentials
- Equipment management system credentials

## Workflow

1. **Order Received**: Parse order details and validate requirements
2. **Schedule Installation**: Find available time slots and book technician
3. **Provision Equipment**: Order and track equipment delivery  
4. **Coordinate Installation**: Dispatch technician and manage appointment
5. **Activate Service**: Complete service turn-up and testing
6. **Complete Order**: Verify completion and update status
