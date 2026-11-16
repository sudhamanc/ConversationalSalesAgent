## ADDED Requirements

### Requirement: Returning customers are acknowledged and resumed

When `discovery_agent` identifies a customer that already exists in the CRM, it SHALL publish `returning_customer_context` with `status` (`active_service`, `in_progress` or `known`) and the customer's active quote, pending orders, fulfillments, active services and last stored serviceability check. It SHALL restore the most recent active quote as `offer_context`. It SHALL restore a serviceability check for the account address made within `SERVICEABILITY_REUSE_DAYS` (default 30) as `serviceability_context` with `reused: true`. Its reply SHALL acknowledge that the customer was found and summarize their status before anything else happens:
- **active service:** the active service, and a question about what else the customer needs
- **in progress:** the saved quote, order or installation, and an offer to continue
- **known:** the address on file, and a question to confirm it

#### Scenario: Returning customer with a saved quote
- **WHEN** a customer with active quote `OFF-1` introduces their company
- **THEN** `offer_context.offer_id` is `OFF-1`
- **AND** the reply welcomes them back and offers to continue with `OFF-1`

#### Scenario: Customer with an activated service
- **WHEN** a customer with a `customer_master` row introduces their company
- **THEN** `returning_customer_context.status` is `active_service`
- **AND** the reply names the active service and asks what else they need

#### Scenario: Serviceability reused
- **WHEN** the account address was checked 3 days ago
- **THEN** `serviceability_context.reused` is true and no serviceability check runs in that turn

### Requirement: Unsaved quotes are not presented

`generate_offer_quote` SHALL return `success: false` with `error: "quote_not_saved"` and SHALL NOT publish `offer_context` when the quote cannot be persisted. The offer agent SHALL tell the customer that the quote could not be saved. When no quote is found, it SHALL say so without inventing a reason.

#### Scenario: Database unavailable while quoting
- **WHEN** saving the quote raises a database error
- **THEN** the tool result has `success: false` and `error: "quote_not_saved"`
- **AND** session state has no new `offer_context`
