## ADDED Requirements

### Requirement: Suggestions are customer-voice and journey-aware

Each string in a `suggestions` event SHALL be a first-person message the customer could send to the sales agent. A suggestion SHALL NOT address the customer (for example "Tell me about your company"), SHALL NOT mention "the customer", and SHALL NOT be filler ("Continue", "Show me next best step"). Suggestions SHALL be chosen for the journey stage derived from the gateway session state (customer, serviceability, offer, order, installation and payment context), not only from the answering agent. They SHALL NOT ask the customer to provide information the journey already holds. When the agent's reply asks the customer for information or a decision, the first suggestion SHALL answer it, as a fill-in template using `[bracketed placeholders]` where the customer must supply details. When suggestions are enabled and the turn produced text, the gateway SHALL send three suggestions even if the suggestion model call fails.

#### Scenario: Agent asks for the company and address
- **WHEN** discovery_agent replies "What is your company name and business address?"
- **THEN** the first suggestion is a fill-in template such as "We're [company name], located at [street, city, state ZIP]"
- **AND** no suggestion contains "your company" or "your address"

#### Scenario: Quote already exists
- **WHEN** the session has an `offer_context.offer_id` and faq_agent answers a policy question
- **THEN** the suggestions include a request to proceed with or adjust the quote
- **AND** no suggestion offers to share the company name or address

#### Scenario: Suggestion model fails
- **WHEN** the suggestion model call raises an error after a reply that asks for a contact email
- **THEN** the gateway sends three suggestions, the first being a contact template containing `[email]`

#### Scenario: Rep-voice output from the model
- **WHEN** the model returns "Send order confirmation to customer"
- **THEN** that suggestion is dropped and replaced from the stage playbook

### Requirement: Placeholder templates are completed before sending

When the customer clicks a suggestion containing `[bracketed placeholders]`, the UI SHALL pre-fill the input and select the first placeholder. Tab or Enter SHALL move the selection to the next placeholder while any remain. The message SHALL NOT be sent while any placeholder remains.

#### Scenario: Filling a template
- **WHEN** the customer clicks "You can reach me at [email] or [phone]"
- **THEN** `[email]` is selected in the input
- **AND** after typing an email and pressing Tab, `[phone]` is selected
- **AND** pressing Enter while `[phone]` remains does not send the message
