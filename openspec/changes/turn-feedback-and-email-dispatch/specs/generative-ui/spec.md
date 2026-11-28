## MODIFIED Requirements

### Requirement: Surface actions send customer messages

Every Button in a gateway-built surface SHALL bind its action to the client function `sendChatMessage` with a non-empty, first-person customer `message` authored by the gateway, plus `surface` (the surface id) and `button` (the Button's component id). When the customer clicks the button, the UI SHALL send that message as the customer's next chat message, exactly as if typed. A click while a reply is still streaming (a card can arrive before its turn ends, for example before a handoff) SHALL be accepted and its message sent as soon as that reply ends; at most one such click is held at a time.

#### Scenario: Accepting a quote from the card
- **WHEN** the customer clicks "Accept this quote and place my order" on a quote surface
- **THEN** the chat shows that text as the customer's message and sends it to `POST /api/chat`

#### Scenario: Button args identify the surface
- **WHEN** the gateway builds a surface with id `check_availability-3f9a1c0b2e7d`
- **THEN** every Button's `sendChatMessage` args contain `surface: "check_availability-3f9a1c0b2e7d"` and `button` equal to that Button's component id

## ADDED Requirements

### Requirement: Acted surfaces show completion

When the customer clicks a Button of a surface, the UI SHALL update that surface in place: the clicked Button SHALL be the only highlighted (`primary`) Button, every Button and input of the surface SHALL be disabled, and the surface SHALL show a status badge. While the turn runs, the clicked Button SHALL show a loading state and the badge SHALL read "Sending…". When the turn completes, the clicked Button SHALL show a check icon and the badge SHALL read "Saved" for a contact surface and "Selected: <button label>" otherwise. When the turn fails, the surface SHALL return to its original, clickable state.

#### Scenario: Choosing a later installation slot
- **WHEN** the slots surface highlights the earliest slot and the customer clicks another slot
- **THEN** after the turn completes the clicked slot is the highlighted Button with a check icon, the earliest slot is no longer highlighted, all slot Buttons are disabled, and the badge reads "Selected: <slot label>"

#### Scenario: Saving contact details
- **WHEN** the customer clicks "Save contact details" on the contact surface
- **THEN** the name, email and phone fields and the Save Button are disabled, the typed values stay visible, and the badge reads "Saved"

#### Scenario: Saving contact details while the reply that showed the card is still streaming
- **WHEN** the contact surface arrives with the registration result, the turn continues with a handoff, and the customer clicks "Save contact details" before that turn ends
- **THEN** the surface immediately shows the Save Button loading and the badge "Sending…", the contact message is sent to `POST /api/chat` once the running turn ends, and after it completes the badge reads "Saved"

#### Scenario: Turn fails after a click
- **WHEN** the customer clicks a Button and the turn ends with an `error` event
- **THEN** the surface shows its original Buttons, enabled, without a badge

### Requirement: Completed steps close their surfaces

A surface whose step was completed without a click on it SHALL be closed the same way as an acted surface, without a highlighted Button: when `create_order` succeeds the UI SHALL close every open cart, quote and contact surface with the badge "Order placed"; when `schedule_installation` succeeds it SHALL close every open scheduling surface with the badge "Installation booked". A surface that already shows a choice keeps it.

#### Scenario: Order placed in the same turn as the cart
- **WHEN** the order agent shows the cart surface and places the order in the same turn (the customer never clicks "Place my order")
- **THEN** the cart surface's Buttons are disabled, none is highlighted, and its badge reads "Order placed"
