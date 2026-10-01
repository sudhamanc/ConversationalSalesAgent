# Spec Delta: agent-services

## ADDED Requirements

### Requirement: FAQ answers are grounded

`faq_agent` SHALL call `search_faq` before answering and SHALL state only facts present in the returned passages. When no relevant passage is returned, it SHALL say a specialist will follow up instead of answering.

#### Scenario: Question not in the corpus
- **WHEN** a customer asks something the FAQ corpus does not cover
- **THEN** the agent does not invent an answer and offers a specialist follow-up

### Requirement: Agents know the current date

Every agent's instruction SHALL include today's date (from `import_forwarded_context`). Tools that create plans or appointments SHALL reject start dates in the past.

#### Scenario: Payment plan without a date
- **WHEN** a customer asks for a payment plan without a start date
- **THEN** the first installment is due after today, never in a past year

### Requirement: Fulfilled orders cannot be cancelled

`cancel_order` SHALL refuse orders whose status is fulfilled, activated, installed, completed or cancelled. The order agent SHALL relay the refusal without first asking for a cancellation reason.

#### Scenario: Cancel a fulfilled order
- **WHEN** the customer asks to cancel an order with status `fulfilled`
- **THEN** the order is unchanged and the agent explains the service is already active

### Requirement: Payment history from the payments table

`get_payment_history` SHALL return the customer's rows from `payments` (matched on the payment's or its order's customer id), newest first, with optional date bounds and limit.

#### Scenario: Seeded customer
- **WHEN** history is requested for CUST-20260427-152
- **THEN** it returns the 495.97 payment for ORD-20260427-518 and no generated transactions

### Requirement: Competitor comparisons are declined

`product_agent` SHALL decline to compare with or comment on competitors and offer its own product specifications instead.

#### Scenario: Competitor question
- **WHEN** asked "How does your fiber compare to AT&T?"
- **THEN** the reply says it cannot compare with other providers and offers Connectivity Max fiber details

### Requirement: Registration without optional address fields

`discovery_agent` SHALL register a new company with `add_new_company` as soon as name, industry, street, city, state and ZIP are known. It SHALL NOT ask for suite, unit or floor.

#### Scenario: Complete address in one message
- **WHEN** a prospect gives company, industry and a full street address with ZIP
- **THEN** the company is registered in the same turn and the serviceability handoff runs
