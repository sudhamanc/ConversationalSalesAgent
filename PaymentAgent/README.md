# Payment Agent

A deterministic, tool-based ADK agent for handling payment operations in the B2B telecommunications sales process.

## Overview

The Payment Agent is responsible for:
- Payment method validation and processing
- Credit checks and authorization
- Invoice generation and management
- Payment history tracking
- Billing account setup

## Features

- **Payment Validation**: Validates credit cards, ACH, and other payment methods
- **Credit Checks**: Performs credit worthiness assessment for business customers
- **Transaction Processing**: Securely processes payments and authorizations
- **Invoice Management**: Generates quotes, invoices, and payment schedules
- **Deterministic**: Temperature set to 0.0 for consistent, reliable payment operations

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
from payment_agent import get_agent

agent = get_agent()

# Process a payment
response = agent.run("I'd like to pay with a credit card ending in 1234")

# Check credit
response = agent.run("Can you run a credit check for this business?")
```

## Integration

This agent is designed to integrate with the Super Agent orchestration system as a sub-agent for the Payment cluster.

## Architecture

- **Agent**: ADK-based tool agent with deterministic configuration
- **Tools**: Payment validation, credit checks, transaction processing
- **Models**: Pydantic schemas for payment data structures
- **Utils**: Logging, caching, and secure credential handling

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
- `AGENT_NAME`: Agent identifier (default: payment_agent)
- Payment gateway API keys and credentials

## Security

- All payment data is encrypted in transit and at rest
- PCI-DSS compliance for credit card processing
- Sensitive credentials stored in environment variables
- Audit logging for all payment transactions
