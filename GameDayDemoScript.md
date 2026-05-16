# Game Day Demo Script
## B2B Conversational Sales Agent — New Customer, New Quote

---

## PRESENTER BRIEFING

**Scenario:** A new B2B prospect calls in. By the end of the conversation they have a signed order, a scheduled install date, and a full notification trail — entirely through one chat window.

**Exact data to use (do not improvise these values):**

| Field | Value |
|-------|-------|
| Company | NorthBridge Logistics LLC |
| Contact | Alex Rivera, VP of Operations |
| Email | alex.rivera@northbridgelogistics.com |
| Phone | 215-555-0147 |
| Address | 1234 Arch Street, Philadelphia, PA 19103 |
| Products | Business Fiber 5 Gbps + SD-WAN Essentials |
| Term | 24 months |
| Base price | $798.00/mo |
| Bundle discount (7%, Internet + SD-WAN) | −$55.86 |
| Term discount (5%, 24-month) | −$37.10 |
| **Final monthly total** | **$705.04/mo** |

**Total time:** ~12–15 minutes including Q&A

---

## OPENING (~2.5 minutes)

*[Start with the chat interface visible and idle. No slides needed — the product speaks for itself.]*

---

"What you're looking at is a multi-agent AI system that automates the full B2B telecom sales lifecycle — from a customer's first 'hello' through service activation — in a single chat conversation.

It runs on Google's Agent Development Kit with Gemini 2.5 Flash. There are 11 specialized agents coordinated by a central orchestrator: Greeting, Discovery, Serviceability, Product, Offer Management, Order, Payment, Service Fulfillment, Customer Communications — each owning exactly one domain.

The design philosophy is strict separation: the LLM decides *what* to do, deterministic tools do the actual work. Prices come from a hardcoded price book. Addresses are validated against a GIS system. Orders are written to a database. The model cannot hallucinate any of those values."

---

**Pause. Address the obvious questions before anyone asks.**

---

**"How do we know it actually works?"**

"We validate at three levels. First, each agent has its own test suite — 40-plus documented scenarios covering happy paths and failure modes. Second, all critical data flows through deterministic tools and is persisted in SQLite — we can inspect the database after every demo run and confirm every record was written correctly. Third, every agent delegation and tool call is logged with a session trace ID, so we can replay exactly what happened in any conversation. The system also enforces zero-hallucination on critical values by running transactional agents at temperature 0.0 — those responses are completely deterministic."

---

**"PII concerns?"**

"Everything in this demo is entirely fictional — no real company names, addresses, or contacts. In a production deployment you'd add encryption at rest, access controls on PII fields, and consent-gated email delivery. Payment data is already tokenized in our implementation — raw card numbers are never stored. Email notifications in this demo are logged to the database but not actually sent to anyone."

---

**"What's the latency? Is it tunable?"**

"We're running Gemini 2.5 Flash, which is Google's speed-optimized model. End-to-end per turn is typically 2–4 seconds, and because responses stream over SSE the tokens appear progressively so it feels faster in practice. Yes, it's tunable: switching to Gemini Pro improves reasoning quality at roughly 2–3x the token cost. Conversational agents run at temperature 0.7; transactional agents run at 0.0, so those responses are both fast and deterministic. A full 10-turn sales cycle runs roughly 15,000–20,000 tokens — under a cent per complete conversation at current Flash pricing."

---

"Alright — let's run the scenario."

---

## LIVE DEMO — 10 Turns

---

### Turn 1 — Greeting Agent

**Type exactly:**
```
Hello
```

**What to say while waiting:**
"Greeting Agent. It generates a phone script — something a human agent could read aloud. Notice it doesn't know who's calling yet. It lists every product category we carry."

**Expected output:** Welcome message referencing "Connectivity Max," listing Internet, Ethernet, TV, SD-WAN, Security, Phone, and Mobile. Formatted as a readable phone script.

---

### Turn 2 — Discovery Agent (new prospect)

**Type exactly:**
```
Hi, I'm Alex Rivera, VP of Operations at NorthBridge Logistics LLC. We're at 1234 Arch Street, Philadelphia, PA 19103.
```

**What to say while waiting:**
"Discovery Agent. It searches the database first — NorthBridge Logistics doesn't exist yet, so it creates a new prospect record. The address is stored as structured JSON with the zip code in an explicit field — that's how we prevent the model from ever paraphrasing '19103' into something else when handing off to the next agent."

**Expected output:** Confirms registration of NorthBridge Logistics LLC at the exact address. Asks whether to check serviceability.

---

### Turn 3 — Serviceability Agent

**Type exactly:**
```
Yes, please check serviceability
```

**What to say while waiting:**
"Serviceability Agent. GIS lookup by ZIP — 19103 is a full-fiber zone, so we should get FTTP confirmed with available speeds up to 5 Gbps."

**Expected output:** ✅ Serviceable. Technology: Fiber (FTTP). Service class: Business. Available products include FIB-1G, FIB-5G, SD-WAN options. Install window: ~5 business days.

---

### Turn 4 — Product Agent

**Type exactly:**
```
Show me the fiber internet options
```

**What to say while waiting:**
"Product Agent. It returns technical specs — speeds, SLAs, features — but never prices. Pricing is the sole domain of the Offer Management Agent. This is an explicit guardrail: the product agent's instruction prompt will redirect any pricing question."

**Expected output:** Business Fiber 1 Gbps and Business Fiber 5 Gbps specs. Speeds, uptime SLA, symmetrical upload/download. No dollar amounts.

---

### Turn 5 — Offer Management Agent

**Type exactly:**
```
Give me a quote for Fiber 5G and SD-WAN Essentials on a 24-month contract
```

**What to say while waiting:**
"Offer Management Agent. Three discount layers will stack: a 7% Internet + SD-WAN bundle discount, and a 5% term discount for the 24-month commitment. Prices come from a hardcoded price book — the model cannot negotiate outside these rates."

**Expected output:**

| Line item | Amount |
|-----------|--------|
| Business Fiber 5 Gbps | $599.00/mo |
| SD-WAN Essentials | $199.00/mo |
| Subtotal | $798.00/mo |
| Internet + SD-WAN Bundle Discount (7%) | −$55.86 |
| 24-Month Commitment Discount (5%) | −$37.10 |
| **Monthly total** | **$705.04/mo** |

Offer ID assigned (OFF-[hash]). Quote persisted to database.

**What to say after seeing the output:**
"$705.04 a month. $92.96 in monthly savings off list. The offer ID is now written to the database — we can look that up against the price book at any point to verify no numbers were invented."

---

### Turn 6 — Order Agent

**Type exactly:**
```
Let's proceed with this quote
```

**What to say while waiting:**
"Order Agent. Cart created, order record written to SQLite. The quote status flips to 'ordered' so it can't be double-submitted. An ORDER_CONFIRMATION notification event fires automatically."

**Expected output:** Order number assigned (ORD-XXXXXXXX). Status: pending_payment. Total: $705.04/mo. Confirmation event logged.

---

### Turn 7 — Payment Agent

**Type exactly:**
```
Yes, process payment
```

**What to say while waiting:**
"Payment Agent. Credit check first — mock in demo, real API in production. Then payment authorization. Card numbers are tokenized; raw PAN data never touches our database."

**Expected output:** Credit check: Approved (score ~720). Payment authorized. Order status → paid. PAYMENT_SUCCESS event logged.

---

### Turn 8 — Service Fulfillment Agent (availability check)

**Type exactly:**
```
What installation dates do you have available?
```

**What to say while waiting:**
"Service Fulfillment Agent querying the scheduling system. 19103 has a 5-day install window, so slots should start within the week."

**Expected output:** Three available time slots — dates and time windows within the next 5–7 business days.

---

### Turn 9 — Service Fulfillment Agent (schedule)

**Type exactly:**
```
Book the first available slot
```

**What to say while the response streams:**
"After this step, the full post-sale flow kicks off automatically: the technician marks the job complete, the system activates the service and writes NorthBridge Logistics to the CustomerMaster database — prospect officially becomes a customer — and fires the SERVICE_ACTIVATED notification. We don't need to walk through that manually because we can show it in the notification history."

**Expected output:** Appointment confirmed — date, time window, Appointment ID (APT-XXXXX). INSTALL_SCHEDULED event logged.

---

### Turn 10 — Customer Communications Agent

**Type exactly:**
```
Show me all the notifications for this customer
```

**What to say while waiting:**
"Customer Communications Agent. Full audit trail."

**Expected output:** Notification history listing:
- ORDER_CONFIRMATION — timestamp, logged
- PAYMENT_SUCCESS — timestamp, logged
- INSTALL_SCHEDULED — timestamp, logged

Each with delivery status. In production with SMTP enabled these hit the customer's inbox.

---

## CLOSING (~30 seconds)

"Ten turns. Ten agents. One chat window. NorthBridge Logistics went from a name we'd never heard of to a paid order with a confirmed install date, a complete notification trail, and a prospect record in the database — in under three minutes of actual conversation.

The architecture is modular by design. Any agent can be upgraded, replaced, or handed to a different team without touching the others. The orchestrator's only job is intent routing — it never generates a price, never writes to a database, never makes a decision it could get wrong.

We're happy to go deeper on any piece: the ADK delegation model, the discount engine, the fulfillment state machine, or the SSE streaming setup."

---

## ANTICIPATED QUESTIONS

**"Could this connect to real telecom APIs?"**
ServiceabilityAgent's GIS lookup, PaymentAgent's credit check, and ServiceFulfillmentAgent's scheduler are all behind clean function-tool interfaces. You replace the mock implementation with a live API call and nothing else changes. The agent doesn't know or care what's behind the tool.

**"What happens if an agent fails mid-flow?"**
ADK session state persists across turns, so partial progress is preserved. Each agent returns structured error JSON rather than crashing — the SuperAgent catches that and responds gracefully. The user can retry without losing context.

**"How do you prevent the model from going off-script — making up prices, for example?"**
Three mechanisms: (1) routing-only SuperAgent — it cannot generate user-facing text itself, only delegate; (2) temperature 0.0 on all transactional agents — no creative variation; (3) explicit guardrails in each agent's instruction prompt blocking competitor mentions, direct pricing from conversational agents, and PII in responses.

**"What does it cost to run per conversation?"**
Gemini 2.5 Flash is Google's most cost-efficient model. A complete 10-turn sales cycle is roughly 15,000–20,000 tokens. At current pricing that's well under $0.01 per conversation. Switching to Gemini Pro for higher reasoning quality roughly doubles the per-token cost — still very low for a transaction that closes a B2B deal.

**"How would you scale this for a real sales team?"**
The current architecture is single-session. For production: containerize each agent service, put a message queue in front of the SuperAgent for concurrent session handling, move SQLite to PostgreSQL for multi-tenancy, and add a secrets manager for API keys. The agent code doesn't change — only the infrastructure layer.

---

*End of script*
