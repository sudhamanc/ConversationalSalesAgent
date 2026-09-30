# Coax Internet Products — Business Knowledge Base

## Overview

Our Business Coax Internet line delivers high-speed internet over the existing hybrid fiber-coaxial (HFC) cable network. The coax line runs from a neighborhood node to the premises. This "last mile" copper coaxial segment is the key architectural difference from FTTP fiber: multiple businesses in the same area share the node capacity. Modern DOCSIS 3.1 technology on our network minimizes congestion, but the asymmetrical speed ratio and shared infrastructure are inherent to the technology.

**Product IDs covered:** COAX-200M, COAX-500M, COAX-1G

---

## Business Internet 200 Mbps (COAX-200M)

### Description
Affordable, reliable internet for small businesses with light to moderate bandwidth needs. Excellent value for businesses that need reliable connectivity without requiring multi-gigabit speeds.

### Technical Specifications
- **Download speed:** 200 Mbps
- **Upload speed:** 20 Mbps
- **Technology:** HFC (Hybrid Fiber-Coaxial)
- **Upload:Download ratio:** 1:10 (asymmetrical)

### Uptime SLA
- **Guaranteed uptime:** 99.5% monthly
- Translates to a maximum of approximately **3.6 hours downtime per month** (43 hours/year)
- Standard business support included

### Hardware Included
- Business modem (DOCSIS 3.0 compatible)
- Standard professional installation

### Use Cases — Best Fit
- Very small offices (1–10 employees)
- Retail or restaurant with POS, basic email, and minimal cloud use
- Kiosk or branch location requiring a low-cost backup or secondary link
- Businesses that primarily consume content (browsing, email, light video streaming)

### Limitations to Discuss
- 20 Mbps upload limits cloud backup speed and can bottleneck video conferencing if more than 2–3 simultaneous video calls occur
- 99.5% SLA is appropriate for cost-sensitive use cases but not for mission-critical operations

---

## Business Internet 500 Mbps (COAX-500M)

### Description
Mid-tier coax internet for growing businesses that need solid download capacity and a reasonable upload ceiling. Includes 1 static IP option and a Business Gateway router.

### Technical Specifications
- **Download speed:** 500 Mbps
- **Upload speed:** 50 Mbps
- **Technology:** HFC
- **Upload:Download ratio:** 1:10

### Uptime SLA
- **Guaranteed uptime:** 99.5% monthly
- SLA credit issued for monthly outage time exceeding the allowance

### Hardware Included
- Business Gateway router (GbE ports, basic Wi-Fi)
- Free professional installation
- 1 static IP address available (on request)

### Use Cases — Best Fit
- Small to medium businesses (10–30 employees) with standard internet use
- Businesses with significant file downloads (software updates, media consumption)
- Secondary / backup link for a primary fiber circuit
- Retail locations with moderate POS, video surveillance, and guest Wi-Fi
- Businesses not yet ready for fiber pricing but needing more than basic service

### Common Customer Questions
**Q: Why is my upload only 50 Mbps when I'm downloading at 500 Mbps?**
A: This is the fundamental nature of DOCSIS/HFC technology. Cable networks are engineered for more downstream (download) capacity because most consumer traffic historically was download-heavy. Business-grade service prioritizes your traffic over consumer plans, but the asymmetry is inherent to HFC architecture. If symmetrical speeds are required, our fiber products (FIB-1G and above) provide equal upload and download.

---

## Business Internet 1 Gbps (COAX-1G)

### Description
Gigabit download speed over DOCSIS 3.1 — the highest capacity tier on the coax network. While download matches fiber's 1G tier, upload is capped at 100 Mbps due to DOCSIS architectural limits. Best suited for download-heavy businesses where the cost premium of fiber is not justified.

### Technical Specifications
- **Download speed:** 1 Gbps (1,000 Mbps)
- **Upload speed:** 100 Mbps
- **Technology:** DOCSIS 3.1 (latest-generation cable modem standard)
- **Upload:Download ratio:** 1:10
- **Static IPs:** 2 included

### Uptime SLA
- **Guaranteed uptime:** 99.5% monthly

### Hardware Included
- Advanced Business Gateway (DOCSIS 3.1 modem + router, multi-GbE capable)
- Free professional installation
- 2 static IP addresses included

### Use Cases — Best Fit
- Businesses that primarily download large volumes of data (software distribution, media delivery, large dataset pulls)
- Organizations with 30–75 employees with moderate upload needs (under 100 Mbps aggregate)
- Cost-conscious businesses that want gigabit download at a lower price point than 1G fiber

### Fiber vs. Coax-1G — Key Tradeoffs
Customers sometimes compare FIB-1G and COAX-1G since both offer 1 Gbps download at a similar price point. Key differences:

| Feature | COAX-1G | FIB-1G |
|---|---|---|
| Download | 1 Gbps | 1 Gbps |
| Upload | 100 Mbps | 1 Gbps (10× faster) |
| SLA | 99.5% | 99.9% |
| Latency | 15–40 ms | 5–15 ms |
| Infrastructure | Shared node | Dedicated fiber |
| Static IPs | 2 | Optional |
| Best for | Download-heavy, cost-sensitive | Balanced or upload-heavy, higher SLA |

**Recommendation guidance:** If the customer runs video conferencing, cloud sync, hosted VoIP, or has more than 10 simultaneous users, recommend FIB-1G. If the customer primarily downloads large datasets or media and upload is secondary, COAX-1G is a viable cost-saving option.

---

## General Coax / HFC Notes

### Technology Background
HFC networks were originally built for cable television. The coaxial cable from the neighborhood node to the business is shared among nearby subscribers. DOCSIS 3.1 significantly increases capacity (up to 10 Gbps downstream in aggregate per node), but in practice, peak-hour congestion on busy nodes can reduce effective speeds below the advertised tier.

Our network operations team actively monitors node utilization and performs node splits when utilization exceeds thresholds, but this is a fact of the technology that does not apply to FTTP fiber.

### Installation
HFC installation requires access to the existing cable infrastructure at the building. Where coax infrastructure is already run to the building, installation typically takes 1–3 hours. New cable builds require additional lead time.

### When to Upgrade from Coax to Fiber
Recommend a fiber upgrade conversation when a coax customer reports:
- Slow uploads affecting business operations
- Video call quality issues (upload limited)
- Outage frequency concerns (SLA upgrade from 99.5% to 99.9%+)
- Growing headcount pushing bandwidth ceiling
- Adding hosted VoIP or SD-WAN with QoS requirements
