# Payment Agent

**Type:** Transactional Agent (Transaction Phase)
**Framework:** Google ADK 1.20.0
**Package:** `payment_agent`
**Status:** ⏳ Standalone (Not Yet Integrated into SuperAgent)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (PaymentAgent/AGENTS.md)

2. **Common tasks → Required reading:**
   - Configuration changes → [SuperAgent/README.md](/SuperAgent/README.md) (`.env` variables)
   - Agent development → [Root AGENTS.md - Golden Rule](/AGENTS.md#the-golden-rule)
   - Payment integration → This file (see Tools section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Purpose

The Payment Agent handles all **payment-related operations** for B2B sales, including credit checks, payment validation, fraud assessment, and authorization.

**Key Responsibilities:**

1. **Business Credit Verification** - Dun & Bradstreet, Experian integration points
2. **Payment Method Validation** - Credit Card (Luhn algorithm), ACH, Wire
3. **Fraud Risk Assessment** - ML-based scoring with configurable thresholds
4. **Payment Authorization** - Gateway integration ready
5. **Transaction Processing** - Capture and settlement

---

## Architecture

| Attribute | Value |
|-----------|-------|
| **Type** | Transactional |
| **Phase** | Transaction (Phase 3) |
| **Source of Truth** | Payment Gateway API, Credit Bureaus |
| **Temperature** | 0.0 (deterministic) |
| **Invocation** | After customer confirms order |

---

## Tools

5 specialized tools:

1. **`verify_business_credit(ein: str, business_name: str)`**
   - Queries credit bureaus (mock: deterministic hash-based scoring)
   - Returns credit score, payment history, risk level

2. **`validate_payment_method(payment_type: str, details: dict)`**
   - Validates credit cards using Luhn algorithm
   - Checks ACH routing numbers
   - Verifies wire transfer details

3. **`assess_fraud_risk(customer_data: dict, order_amount: float)`**
   - ML-based fraud scoring
   - Transaction velocity monitoring
   - Behavioral analysis

4. **`authorize_payment(payment_details: dict, amount: float)`**
   - Gateway authorization (mock)
   - Returns authorization code

5. **`process_payment(authorization_code: str, amount: float)`**
   - Capture and settlement
   - Transaction confirmation

---

## Integration Points (Production)

**Credit Bureaus:**
- Dun & Bradstreet Business Credit
- Experian Business
- Equifax

**Payment Gateways:**
- Stripe
- Braintree
- Authorize.net

**Fraud Detection:**
- Sift Science
- Kount
- Stripe Radar

**Current Implementation:** Mock APIs with deterministic responses

---

## Security Considerations

⚠️ **NOT PCI-DSS compliant** (academic demo only)

**Production Requirements:**
- PCI DSS compliance
- Tokenization for stored payment methods
- Encryption at rest and in transit
- Rate limiting on payment attempts
- Audit logging for all financial transactions

---

## Development

```bash
cd PaymentAgent
pip install -e .
python main.py
```

**Related Documentation:** [/AGENTS.md](/AGENTS.md)
