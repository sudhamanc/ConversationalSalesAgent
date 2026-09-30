# Business Voice & Unified Communications — Business Knowledge Base

## Overview

Our Business Voice portfolio spans four tiers: Basic VoIP for micro-businesses, Standard VoIP for growing teams, Enterprise SIP Trunking for large organizations with existing PBX infrastructure, and a cloud UCaaS platform (Unified Communications as a Service) that integrates voice, video, messaging, and collaboration in a single application.

All voice services use VoIP (Voice over IP) technology, delivered over our business internet connections. Voice traffic is prioritized via QoS policies on our network.

**Product IDs covered:** VOICE-BAS, VOICE-STD, VOICE-ENT, VOICE-UCAAS

---

## Business Voice Basic (VOICE-BAS)

### Description
Essential business phone service for micro-businesses and small offices needing 1–5 lines. Managed hosted PBX — no on-premises hardware required beyond IP phones or soft clients. Delivered as a cloud service over any qualified internet connection.

### Technical Specifications
- **Lines supported:** 1–5 concurrent lines
- **Voice codec:** G.711 HD Voice (narrowband), 64 kbps per active call
- **Minimum internet bandwidth required:** 100 kbps per active call (upstream + downstream)
- **Recommended internet:** COAX-200M or higher; fiber recommended for office primary use

### Features
- HD Voice quality (G.711 codec)
- Voicemail to email (audio file attached as .wav)
- Auto-attendant (single level: "Press 1 for Sales, Press 2 for Support...")
- Call forwarding and transfer
- Free local and long-distance calling (continental US)
- Business portal for admin configuration

### SLA
- 99.9% platform availability (separate from internet circuit SLA)
- 24/7 business support via phone and online portal

### Use Cases — Best Fit
- Solo practitioners, home offices, micro-businesses
- Retail locations needing 1–2 customer lines and 1–2 internal lines
- As an add-on to any internet plan where the customer needs a simple phone system without PBX complexity

### Limitations
- Maximum 5 lines; upgrade to VOICE-STD for 6+ lines
- Single-level auto-attendant only (no multi-level IVR)
- No conference bridge included

---

## Business Voice Standard (VOICE-STD)

### Description
Full-featured hosted PBX for teams of 5–20 lines. Adds multi-level IVR, hunt group routing, call parking, and a 10-person built-in conference bridge. Designed for businesses that have outgrown basic voice but don't need enterprise SIP trunking.

### Technical Specifications
- **Lines supported:** 5–20 concurrent lines
- **Voice codec:** G.711 HD Voice
- **Minimum internet bandwidth:** 100 kbps per active call; recommend FIB-1G or COAX-500M minimum for 10+ simultaneous calls

### Features
- HD Voice quality
- Voicemail to email
- Auto-attendant with multi-level IVR (nested menus, time-of-day routing)
- Call forwarding, transfer, and parking
- Hunt groups and ring groups (round-robin, simultaneous ring, sequential)
- Free local and long-distance calling (continental US)
- Built-in conference bridge (up to 10 participants per bridge)
- Priority business support

### SLA
- 99.9% platform availability
- Priority 24/7 support queue (faster response time than Basic tier)

### Use Cases — Best Fit
- Professional services offices (law firms, medical practices, accounting)
- Real estate and insurance agencies
- B2B companies with an inside sales team (hunt groups for inbound calls)
- Any business with departments needing call routing logic (Sales → Service → Billing menus)

---

## Business Voice Enterprise / SIP Trunking (VOICE-ENT)

### Description
Enterprise-grade SIP trunking for large organizations (20–100+ concurrent lines) that already have an on-premises PBX (Cisco, Avaya, Mitel, Asterisk, etc.) or a session border controller (SBC). Rather than replacing existing PBX infrastructure, VOICE-ENT connects it to our carrier network via SIP, enabling unlimited concurrent calls at a per-trunk price.

### Technical Specifications
- **Lines supported:** 20–100+ concurrent SIP channels
- **Voice codec:** G.711 and G.722 HD Voice
- **SIP compatibility:** SIP RFC 3261 with T.38 fax support
- **Bandwidth requirement:** 100–250 kbps per concurrent call depending on codec; FIB-1G or FIB-5G strongly recommended for 20+ concurrent calls
- **E911:** Supported with static address provisioning per trunk group

### Features
- HD Voice (G.711 and G.722 wideband codec)
- SIP trunk integration with existing on-premises PBX or SBC
- Unlimited concurrent calls (capacity scales with trunk count)
- E911 support (PSAP routing with registered address)
- Toll-free number (TFN) options — dedicated 800/888/877/866 numbers available
- Call recording options (network-side or PBX-side)
- Call detail record analytics via portal
- Conference bridge: 50-participant bridge available
- Dedicated account manager
- Porting of existing numbers (local number portability — LNP) supported

### Uptime SLA
- **Guaranteed voice uptime:** 99.99%
- This is the highest voice SLA in our portfolio
- Translates to a maximum of approximately **53 minutes of downtime per year**
- Proactive monitoring with automated failover options

### Use Cases — Best Fit
- Large call centers (in-bound or outbound)
- Enterprises with an existing PBX investment they want to retain
- Organizations that need toll-free numbers for customer-facing lines
- Multi-office organizations wanting centralized SIP trunking with distributed PBX
- Companies with compliance requirements around call recording (financial services, healthcare)

### Technical Considerations
- Customer must provide or procure a compatible SBC or PBX; we do not provide PBX hardware under the VOICE-ENT plan
- Configuration requires coordination with the customer's IT team or PBX vendor
- Typically 5–10 business days for SIP trunk provisioning after number porting paperwork is complete

### Common Customer Questions
**Q: Can I keep my existing phone numbers?**
A: Yes. We support full number porting (LNP) for local, long-distance, and toll-free numbers. The porting process typically takes 7–15 business days after LOA submission.

**Q: What if my PBX isn't on your certified compatibility list?**
A: Most standards-compliant SIP PBX and SBC devices work. We recommend a pre-deployment SIP interoperability test (free of charge) to validate signaling compatibility before go-live.

---

## Unified Communications (UCaaS) — VOICE-UCAAS

### Description
All-in-one cloud communications platform combining HD voice calling, video conferencing, team messaging, presence, file sharing, and analytics. No PBX hardware required. Users access via desktop app (Windows/macOS), mobile app (iOS/Android), and web browser. Ideal for distributed and hybrid workforces.

### Technical Specifications
- **Users:** Unlimited licensed seats (per-user pricing)
- **Voice codec:** Opus (adaptive) and G.722 HD Voice
- **Video:** up to 200-participant video meetings with full HD (1080p) support
- **Data:** All messaging and file sharing is encrypted in transit (TLS 1.2+) and at rest (AES-256)
- **Minimum internet bandwidth per user:** 1–2 Mbps up/down for HD video calling

### Features
- HD Voice and video calling (person-to-person and multi-party)
- Team messaging with threaded conversations, @mentions, and emoji
- Presence indicators (Available, Busy, Do Not Disturb, Away)
- Video conferencing up to 200 participants
- Screen sharing and remote control
- File sharing with version history (up to 25 GB storage per user)
- Mobile and desktop native apps
- CRM integrations: Salesforce, HubSpot, Microsoft Dynamics (pre-built connectors)
- Auto-attendant with AI-based intent routing
- Call analytics and reporting dashboard (call volume, hold time, agent performance)
- 24/7 priority support

### Uptime SLA
- **Guaranteed platform uptime:** 99.99%
- Multi-region redundant cloud infrastructure
- Automatic failover to secondary region in < 10 seconds

### Use Cases — Best Fit
- Remote-first or hybrid companies (no fixed office, or distributed teams)
- Sales teams needing CRM-integrated click-to-call and call logging
- Companies wanting to eliminate on-premises PBX maintenance costs
- Organizations that require strong collaboration tools alongside voice (Zoom alternative with built-in telephony)
- Fast-growing companies wanting a per-seat model that scales linearly

### UCaaS vs. Hosted PBX (VOICE-STD) Comparison
| Feature | VOICE-STD (Hosted PBX) | VOICE-UCAAS |
|---|---|---|
| Voice | ✅ | ✅ |
| Video conferencing | ❌ | ✅ (200 participants) |
| Team messaging | ❌ | ✅ |
| Mobile app | Basic | Full-featured native app |
| CRM integration | ❌ | ✅ (Salesforce, HubSpot, Dynamics) |
| Analytics dashboard | Basic call logs | Full reporting suite |
| Best for | Traditional office with stable headcount | Distributed / hybrid teams, growth-oriented |

---

## Voice Bandwidth Planning Guide

When selling any voice product alongside an internet plan, use this quick sizing guide:

| Concurrent calls | Minimum recommended internet upload |
|---|---|
| 5 | 1 Mbps |
| 10 | 2 Mbps |
| 20 | 4 Mbps |
| 50 | 10 Mbps |
| 100+ | 25 Mbps+ (fiber strongly recommended) |

For G.722 HD voice (VOICE-ENT, VOICE-UCAAS), add ~25% to these figures.

**Key rule:** Total upstream bandwidth used for voice should not exceed 20% of the internet circuit's upload capacity, to leave headroom for other business traffic. If a customer's math exceeds this, recommend upgrading the internet plan alongside voice.
