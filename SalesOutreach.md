# Plan: Agent-Driven Prospect Outreach (Option B — Live Call Coach)

## TL;DR

Add a **Sales Outreach Coach** mode where internal reps select a prospect from a BANT-ranked dashboard, click "Start Outreach Call," and receive AI-powered live coaching as they speak with the prospect on the phone. The rep types what the customer says; the AI suggests what to say next, handles objections, and drives the conversation toward an order — using the same agent pipeline, cart, and journey sidebar as the existing customer-facing chat.

---

## Interaction Model

```
┌──────────────────────────────────────────────────────────────────────┐
│  VIEW 1: Prospect Dashboard (Landing)                                │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │  Full-width prospect list (ranked by BANT score)              │   │
│  │  Each card: Company, Contact, Phone, BANT bar, "Start Call"   │   │
│  │  No journey sidebar, no cart (irrelevant before call starts)  │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

         ↓ Click "Start Outreach Call"

┌──────────────────────────────────────────────────────────────────────┐
│  VIEW 2: Outreach Chat (same layout as Customer Chat mode)           │
│  ┌──────────┬─────────────────────────────────────┬─────────────┐   │
│  │ Journey  │  Chat (coaching responses)           │  Cart/      │   │
│  │ Sidebar  │  Header: "🎯 Outreach: Crane.io"    │  Activity   │   │
│  │          │  Input: "Customer says: ___"         │  Panel      │   │
│  │ (fills   │                                     │  (fills as  │   │
│  │  as flow │  AI: "Say this: '...'"              │  products/  │   │
│  │  progr.) │  AI: "Good buying signal! Ask..."   │  quotes     │   │
│  │          │                                     │  added)     │   │
│  └──────────┴─────────────────────────────────────┴─────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Principle:** Outreach mode is a different *entry point* into the same conversation engine. Once the call progresses toward an order, the same agents (Serviceability, Product, Offer, Order, Payment, Fulfillment) handle it — the cart fills, the journey sidebar updates, everything works as today. The only difference is the `[OUTREACH MODE]` prefix that makes responses coaching-style instead of customer-facing.

---

## Conversation Flow Example

| Phase | Rep Types | AI Coaching Response |
|-------|-----------|---------------------|
| **Opening** | *(auto-generated on Start Call)* | "Here's your opener: 'Hi Sarah, this is [Rep] from ComSales. I noticed Crane.io has been expanding — are you evaluating connectivity for your new offices?'" |
| **Discovery** | "She said yes, they need internet for their new Philly office at 123 Main St" | "Perfect — address captured. Let me check serviceability... ✅ Fiber available up to 10Gbps. Say: 'Great news — we can deliver dedicated fiber at that location. What speeds are you looking at?'" |
| **Product Interest** | "She asked about 5Gbps fiber pricing" | *(runs offer tools)* → "Quote: $523/mo on 24-month term. Say: 'For Business Fiber 5Gbps with our SLA guarantee, it's $523 per month on a 2-year agreement. That includes 24/7 support and 99.99% uptime.'" |
| **Close** | "She said let's do it, send the contract to sarah@crane.io" | *(creates order)* → "Order ORD-20260505-XXX created! Say: 'Excellent! I'll send the service agreement to sarah@crane.io now. When would you like us to schedule the installation?'" |
| **Scheduling** | "Next Tuesday morning works" | *(schedules install)* → "Booked for Tuesday AM. Say: 'You're all set for Tuesday between 8AM and noon. You'll get a confirmation email shortly. Anything else I can help with?'" |

---

## Implementation Plan

### Phase 1: Backend — Prospects Endpoint

**New file:** `SuperAgent/server/api/prospects.py`

```python
"""
GET /api/prospects/top — Return top prospects ranked by BANT score.

Query params:
  - limit (int, default 10): Max prospects to return
  - sort_by (str, default 'bant_score'): Sort field ('bant_score' | 'priority')
"""

import sqlite3
from fastapi import APIRouter, Query
from super_agent.utils.database import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_PROSPECTS_SQL = """
SELECT
    a."Company Name"            AS company_name,
    a.Industry                  AS industry,
    a."Territory/Region"        AS region,
    a."Existing Customer"       AS existing_customer,
    a.Street                    AS street,
    a.City                      AS city,
    a.State                     AS state,
    a.zip_code                  AS zip_code,
    c."Name"                    AS contact_name,
    c."Title"                   AS contact_title,
    c."Role in Decision Making" AS contact_role,
    c."Phone"                   AS phone,
    c."Email"                   AS email,
    o."Opportunity Name"        AS opportunity_name,
    o."Stage"                   AS stage,
    o."Total MRC (Est)"         AS total_mrc,
    o."BANT_Score_0to100"       AS bant_score,
    o."BANT_Priority_Bucket"    AS bant_priority,
    o."BANT_Budget_Score"       AS budget_score,
    o."BANT_Authority_Score"    AS authority_score,
    o."BANT_Need_Score"         AS need_score,
    o."BANT_Timing_Score"       AS timing_score,
    o."BANT_Data_Gaps"          AS bant_gaps,
    i."Buying Signals"          AS buying_signals,
    i."Pain Points"             AS pain_points,
    i."Recommended Positioning" AS recommended_positioning
FROM accounts a
JOIN opportunities o ON a."Company Name" = o."Company Name"
LEFT JOIN contacts c ON a."Company Name" = c."Company Name"
LEFT JOIN insights i ON a."Company Name" = i."Company Name"
WHERE o."BANT_Score_0to100" IS NOT NULL
  AND a."Existing Customer" != 'Y'
ORDER BY o."BANT_Score_0to100" DESC
LIMIT ?
"""


@router.get("/api/prospects/top")
def get_top_prospects(limit: int = Query(10, ge=1, le=50)):
    """Return top BANT-scored prospects for outreach."""
    conn = get_connection()
    try:
        rows = conn.execute(_PROSPECTS_SQL, (limit,)).fetchall()
        prospects = [dict(row) for row in rows]
        return {"prospects": prospects, "count": len(prospects)}
    except Exception as e:
        logger.error(f"Error fetching prospects: {e}")
        return {"prospects": [], "count": 0, "error": str(e)}
    finally:
        conn.close()
```

**Register in `SuperAgent/server/main.py`:**
```python
from api.prospects import router as prospects_router
app.include_router(prospects_router, tags=["Prospects"])
```

---

### Phase 2: SuperAgent Prompt — Outreach Mode Routing

**Modify:** `SuperAgent/super_agent/prompts.py`

Add after the existing `[GREETING]` override and before all other routing rules:

```
**OUTREACH MODE OVERRIDE — CHECK SECOND (after GREETING):**
If the user message starts with "[OUTREACH MODE]", a sales rep is using AI-assisted
coaching during a live prospect call. Route as follows:
- If the message contains "Initiate outreach for", transfer to **greeting_agent**
  (it will generate a call opening script based on the prospect context).
- Otherwise, extract the customer's statement from after "Customer said:" and route
  based on the INTENT of what the customer said, using the same routing rules below.
  The responding agent should frame its response as COACHING for the rep — suggest
  what to say next (in quotes), flag buying signals, and handle objections.
  Do NOT output text directly addressed to the customer.
```

**Modify:** GreetingAgent prompt (in `SuperAgent/super_agent/sub_agents/greeting/`)

Add to instruction:

```
When the user message starts with "[OUTREACH MODE] Initiate outreach for:", generate a
personalized cold-call opening script based on the prospect details provided. Include:
1. A warm opener referencing their industry/company
2. A value proposition hook tied to their identified needs (use BANT data)
3. A qualifying question to get the conversation started
4. 2-3 backup pivots if the prospect is cold/resistant

Format as coaching for the rep — use "Say this:" with verbatim lines in quotes.
Include alternatives for different prospect reactions (warm, neutral, cold).
```

---

### Phase 3: Frontend — ProspectDashboard Component

**New file:** `SuperAgent/client/src/components/ProspectDashboard.jsx`

**Structure:**
```jsx
// ProspectDashboard.jsx
// - Fetches GET /api/prospects/top on mount via fetch()
// - Renders responsive card grid
// - Each card shows:
//   • Company name, industry, region
//   • Contact name, title, decision role
//   • Phone (click-to-call tel: link), email
//   • BANT score (0-100) with colored progress bar:
//     - Green ≥67, Yellow ≥33, Red <33
//   • Priority bucket badge (A=green, B=yellow, C=red)
//   • Opportunity name, stage, estimated MRC
//   • Buying signals and pain points (from insights)
//   • "Start Outreach Call" button
// - Loading skeleton while fetching
// - Empty state: "No prospects with BANT scores found"
// - Tailwind CSS only (follows CartPanel/Section component pattern)

// Props: onStartOutreach(prospect) — called when rep clicks the button
```

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  🎯 Top Prospects for Outreach          [Refresh] [Filter]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────┐  ┌───────────────────────┐│
│  │ Crane.io              [A] 82│  │ VoiceStream Net  [A] 75││
│  │ SaaS · Northeast           │  │ Telecom · Mid-Atl     ││
│  │ Sarah Chen, VP Engineering │  │ Mark Rivera, CTO      ││
│  │ 📞 (215) 555-1234         │  │ 📞 (302) 555-5678    ││
│  │ ████████████░░ Budget: 90  │  │ ████████░░░░ Budget:70││
│  │ ███████████░░░ Auth:   85  │  │ █████████████ Auth: 90││
│  │ █████████░░░░░ Need:   70  │  │ ████████░░░░ Need: 65││
│  │ ██████████░░░░ Timing: 80  │  │ █████████░░░ Timing:75││
│  │ Opp: Fiber 5G Bundle       │  │ Opp: SD-WAN + Fiber   ││
│  │ Est MRC: $4,200            │  │ Est MRC: $3,800       ││
│  │ 🚀 Start Outreach Call     │  │ 🚀 Start Outreach Call││
│  └─────────────────────────────┘  └───────────────────────┘│
│                                                             │
│  ┌─────────────────────────────┐  ┌───────────────────────┐│
│  │ Meridian Health       [B] 58│  │ ...                   ││
│  │ Healthcare · Southeast      │  │                       ││
│  │ ...                         │  │                       ││
│  └─────────────────────────────┘  └───────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 4: Frontend — App.jsx View Switching

**Modify:** `SuperAgent/client/src/App.jsx`

**Changes:**
1. Add `view` state: `useState('chat')` — values: `'chat'` | `'prospects'`
2. Add navigation tabs above or in the header area:
   - "💬 Customer Chat" → `setView('chat')`
   - "🎯 Prospect Outreach" → `setView('prospects')`
3. Conditional rendering:
   - `view === 'prospects'`: Render `<ProspectDashboard />` full-width (no sidebars)
   - `view === 'chat'`: Current layout (JourneySidebar + ChatWindow + CartPanel)
4. `handleStartOutreach(prospect)`:
   ```js
   setView('chat');
   startOutreach(prospect); // from ChatContext
   ```
5. When `mode === 'outreach'` (from context), modify header:
   - Avatar: 🎯 orange background
   - Title: "Sales Outreach Coach"
   - Subtitle: `Coaching for: ${outreachProspect.company_name}`
   - "← Back to Prospects" button

---

### Phase 5: Frontend — ChatContext Outreach Integration

**Modify:** `SuperAgent/client/src/contexts/ChatContext.jsx`

**Changes:**

1. **Add state:**
   ```js
   const [mode, setMode] = useState('customer'); // 'customer' | 'outreach'
   const [outreachProspect, setOutreachProspect] = useState(null);
   ```

2. **Add `startOutreach(prospect)` function:**
   ```js
   const startOutreach = useCallback(async (prospect) => {
     setMode('outreach');
     setOutreachProspect(prospect);
     // Clear existing conversation for fresh outreach session
     resetSession();
     setMessages([]);
     setJourneySteps([]);
     setCart(null);
     setActivities({
       customer: null, quote: null, order: null,
       scheduling: null, payment: null,
       fulfillment: [], notifications: []
     });

     // Generate opening script — no user bubble shown
     const trigger = [
       `[OUTREACH MODE] Initiate outreach for: ${prospect.company_name}.`,
       `Contact: ${prospect.contact_name}, Phone: ${prospect.phone},`,
       `Title: ${prospect.contact_title}, Role: ${prospect.contact_role},`,
       `Industry: ${prospect.industry}, Region: ${prospect.region},`,
       `BANT Score: ${prospect.bant_score}/100`,
       `(Budget: ${prospect.budget_score}, Authority: ${prospect.authority_score},`,
       `Need: ${prospect.need_score}, Timing: ${prospect.timing_score}),`,
       `Opportunity: ${prospect.opportunity_name}, Est MRC: $${prospect.total_mrc},`,
       `Buying Signals: ${prospect.buying_signals || 'N/A'},`,
       `Pain Points: ${prospect.pain_points || 'N/A'}.`,
       `Generate my personalized opening call script and coaching strategy.`,
     ].join(' ');

     setIsStreaming(true);
     setMessages([{ role: "assistant", content: "", isStreaming: true }]);
     await streamChat(trigger, onToken, onDone, onError, ...);
   }, []);
   ```

3. **Modify `sendMessage` to prefix in outreach mode:**
   ```js
   const sendMessage = useCallback(async (text) => {
     const payload = mode === 'outreach'
       ? `[OUTREACH MODE] Customer said: "${text}"`
       : text;

     // Show user message in UI
     setMessages(prev => [...prev, {
       role: "user",
       content: text,
       isOutreach: mode === 'outreach'
     }]);

     setIsStreaming(true);
     await streamChat(payload, onToken, onDone, onError, ...);
   }, [mode]);
   ```

4. **Export new values from context:**
   ```js
   value={{
     messages, isStreaming, sendMessage, clearChat,
     journeySteps, cart, activities, isSidebarOpen, setIsSidebarOpen,
     // New exports:
     mode, setMode, outreachProspect, startOutreach,
   }}
   ```

---

### Phase 6: Frontend — UI Polish

**Modify:** `SuperAgent/client/src/components/ChatWindow.jsx`
- When `mode === 'outreach'`:
  - Input placeholder: `"Type what the prospect is saying on the call..."`
  - Small info bar above input: "🎙️ Relay what [Contact Name] says"

**Modify:** `SuperAgent/client/src/components/MessageBubble.jsx`
- When `message.isOutreach && message.role === 'user'`:
  - Label: "📞 Customer:" instead of "You"
  - Bubble styling: slate border instead of blue

---

## Files Summary

### New Files

| File | Purpose | ~Lines |
|------|---------|--------|
| `SuperAgent/server/api/prospects.py` | GET /api/prospects/top endpoint | ~50 |
| `SuperAgent/client/src/components/ProspectDashboard.jsx` | Prospect selection UI | ~200 |

### Modified Files

| File | Change | ~Lines Changed |
|------|--------|----------------|
| `SuperAgent/server/main.py` | Register prospects router | +3 |
| `SuperAgent/super_agent/prompts.py` | Add `[OUTREACH MODE]` routing rule | +15 |
| `SuperAgent/super_agent/sub_agents/greeting/` prompt | Outreach script generation instruction | +15 |
| `SuperAgent/client/src/App.jsx` | View state, nav tabs, conditional rendering | +40 |
| `SuperAgent/client/src/contexts/ChatContext.jsx` | `mode`, `startOutreach()`, prefix logic | +50 |
| `SuperAgent/client/src/components/ChatWindow.jsx` | Outreach input placeholder/label | +10 |
| `SuperAgent/client/src/components/MessageBubble.jsx` | Outreach user bubble label | +5 |

**Total new/changed code: ~390 lines**

### Unchanged (reused as-is)

| Component | Why No Changes Needed |
|-----------|----------------------|
| DiscoveryAgent | Prospect data already in DB; handles company lookups normally |
| ServiceabilityAgent | Works same — address comes from rep's relay |
| ProductAgent | Same product lookup regardless of mode |
| OfferManagementAgent | Same pricing/quote generation |
| OrderAgent | Same cart/order creation |
| PaymentAgent | Same payment flow |
| ServiceFulfillmentAgent | Same scheduling/activation |
| FAQAgent | Can still answer questions in outreach mode |
| `streamChat()` in api.js | No changes — prefix is just text in the message |
| JourneySidebar | Populates naturally from agent events |
| CartPanel | Populates naturally from cart_update events |
| Database schema | All tables already exist with BANT data |
| `api/chat.py` | No changes (prefix is just text in the message) |

---

## Agent Code Impact Assessment

| Agent | Changes Required | Reason |
|-------|-----------------|--------|
| **SuperAgent (orchestrator)** | +15 lines in prompts.py | Add `[OUTREACH MODE]` routing rule |
| **GreetingAgent** | +15 lines in prompt | Handle outreach script generation |
| **DiscoveryAgent** | None | Already handles company lookups |
| **ServiceabilityAgent** | None | Address comes from rep relay |
| **ProductAgent** | None | Same product catalog |
| **OfferManagementAgent** | None | Same pricing engine |
| **OrderAgent** | None | Same cart/order flow |
| **PaymentAgent** | None | Same payment processing |
| **ServiceFulfillmentAgent** | None | Same scheduling/activation |
| **FAQAgent** | None | Answers questions normally |

**Total agent changes: 2 files, ~30 lines. Zero new agents.**

---

## How the `[OUTREACH MODE]` Prefix Works

The prefix is injected by the **frontend only** — invisible to the rep:

```
┌─────────────────────────────────────────────────────────────────┐
│  Rep sees in UI        │  What's actually sent to backend       │
├────────────────────────┼────────────────────────────────────────┤
│  (Start Call click)    │  [OUTREACH MODE] Initiate outreach     │
│                        │  for: Crane.io. Contact: Sarah Chen... │
├────────────────────────┼────────────────────────────────────────┤
│  "They need 5Gbps"    │  [OUTREACH MODE] Customer said:        │
│                        │  "They need 5Gbps"                     │
├────────────────────────┼────────────────────────────────────────┤
│  "She said yes"        │  [OUTREACH MODE] Customer said:        │
│                        │  "She said yes"                        │
└────────────────────────┴────────────────────────────────────────┘
```

The SuperAgent recognizes the prefix and:
1. Routes to the appropriate sub-agent based on customer intent
2. Sub-agents respond normally (tools execute, data flows)
3. The routing instruction tells agents to frame output as coaching

---

## Design Decisions

1. **No new agent** — Outreach coaching is a prompt-level behavioral switch, not a separate agent. Reuses the entire existing pipeline.

2. **Client-side prefix injection** — The `[OUTREACH MODE]` prefix is invisible to the rep and handled purely by the frontend. No special server middleware needed.

3. **Same session/cart/journey** — Outreach conversations use the same ADK session infrastructure. Cart and journey populate naturally as the call progresses.

4. **Prospect data from existing DB** — The `accounts`, `contacts`, `opportunities`, and `insights` tables already contain everything needed. No new data ingestion.

5. **View-based routing (no React Router)** — A simple `view` state in App.jsx controls which panel renders, matching the existing single-page architecture.

6. **Phone-first UX** — Input labeled "Customer says:" reinforces that the rep is relaying voice, not typing to the AI directly.

---

## Verification Plan

1. **Prospects API:** `curl http://localhost:8000/api/prospects/top` → returns JSON with BANT-scored prospects sorted desc
2. **Empty DB graceful:** Remove BANT data → endpoint returns `{"prospects": [], "count": 0}` → dashboard shows empty state
3. **Prospect Dashboard:** Navigate to "Prospect Outreach" tab → see ranked list with BANT bars, contact info, phone links
4. **Start Outreach:** Click "Start Outreach Call" on a prospect → view flips to chat → AI generates opening script automatically (no user message bubble)
5. **Live Coaching:** Type "They said they already have Verizon" → AI responds with objection handling coaching ("Say: '...'")
6. **Full Flow:** Drive conversation through serviceability → product → quote → order → payment → scheduling → verify cart fills, journey updates, emails sent
7. **Mode Toggle:** Click "← Back to Prospects" → returns to dashboard; click "Customer Chat" → returns to normal mode
8. **No Regression:** Switch to Customer Chat mode → regular conversation works identically to before

---

## Estimated Effort

| Phase | Description | Complexity |
|-------|-------------|-----------|
| Phase 1 | Backend prospects endpoint | Low (~50 lines, pure SQL) |
| Phase 2 | Prompt modifications | Low (~30 lines across 2 files) |
| Phase 3 | ProspectDashboard component | Medium (~200 lines, new UI) |
| Phase 4 | App.jsx view switching | Low (~40 lines) |
| Phase 5 | ChatContext integration | Medium (~50 lines, state logic) |
| Phase 6 | UI polish | Low (~15 lines) |

**Dependencies:** Phase 1 → Phase 3 (dashboard needs API). Phase 2 → Phase 5 (prefix needs prompt to recognize it). Phases 4-6 depend on Phase 3+5.

**Recommended build order:** Phase 1 → Phase 2 → Phase 5 → Phase 3 → Phase 4 → Phase 6
