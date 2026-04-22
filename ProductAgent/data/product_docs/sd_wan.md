# SD-WAN Products — Business Knowledge Base

## Overview

Software-Defined Wide Area Networking (SD-WAN) replaces or augments traditional WAN architectures (MPLS, dedicated leased lines) with software-defined intelligence layered on top of standard internet connections. Our SD-WAN portfolio spans three tiers: Essentials for small multi-site deployments, Professional for mid-market with integrated security, and Enterprise for large organizations requiring global backbone access, full SASE integration, and managed NOC services.

All tiers use zero-touch provisioning (ZTP), meaning branch hardware ships pre-configured and self-activates at power-on without requiring on-site IT staff.

**Product IDs covered:** SDWAN-ESS, SDWAN-PRO, SDWAN-ENT

---

## SD-WAN Essentials (SDWAN-ESS)

### Description
Entry-level SD-WAN for small businesses with 1–5 locations that need basic traffic optimization, WAN failover, and centralized management. Ideal first step away from single-ISP connectivity with no redundancy.

### Technical Specifications
- **Throughput per site:** Up to 250 Mbps (aggregate WAN capacity)
- **Sites supported:** 1–5 sites per deployment
- **WAN links per site:** Dual-WAN (2 simultaneous ISP connections)
- **Failover time:** < 60 seconds automatic failover on link failure
- **Management:** Cloud-managed portal (web browser, no on-site hardware management)

### Features
- Application-aware routing (identifies and prioritizes traffic by application type — voice, video, web, bulk transfer)
- Dual-WAN failover (automatic cutover when active link fails)
- Basic QoS and traffic shaping (3 priority classes: voice/video, business apps, bulk data)
- Cloud-managed portal with basic visibility dashboard
- Zero-touch provisioning (ZTP) — device self-activates on first power-on
- SD-WAN gateway appliance included (installed at each site)
- Business support

### Uptime
- No formal circuit uptime SLA at the Essentials tier (dependent on underlying ISP SLAs)
- For sites requiring formal SLA, recommend pairing with our fiber or coax business internet

### Use Cases — Best Fit
- Retail chains (1–5 locations) wanting centralized visibility and automatic failover
- Small franchise businesses with branch offices
- Businesses currently using a single ISP link with no redundancy
- Organizations moving from MPLS to internet-based WAN for the first time

### Common Customer Questions
**Q: What does "application-aware routing" mean in practice?**
A: The SD-WAN appliance inspects packet headers to identify the traffic type (e.g., VoIP, Microsoft Teams, Salesforce CRM, file backup). It then routes each type across the best available WAN link — for example, sending real-time video calls over the lower-latency fiber link and bulk file backups over the cheaper coax link.

**Q: What if both WAN links go down simultaneously?**
A: When both links fail, the site has no WAN connectivity until at least one is restored. For mission-critical operations requiring higher resilience, the Professional tier supports up to 4 WAN links simultaneously (including LTE/5G failover modem integration).

---

## SD-WAN Professional (SDWAN-PRO)

### Description
Advanced SD-WAN for mid-market organizations with 5–25 sites. Adds AI-optimization, up to 4 simultaneous WAN links, integrated firewall and IPS, multi-cloud connectivity (AWS, Azure, GCP), and advanced QoS with 8 traffic classes. Includes 99.9% uptime SLA.

### Technical Specifications
- **Throughput per site:** Up to 1 Gbps (aggregate WAN capacity)
- **Sites supported:** 5–25 sites per deployment
- **WAN links per site:** Up to 4 simultaneous links (MPLS, fiber, coax, LTE/5G)
- **Failover time:** < 10 seconds automatic failover
- **QoS classes:** 8 traffic priority classes

### Features
- Application-aware routing with AI optimization (ML model learns traffic patterns over 7–14 days to improve path selection)
- Multi-WAN failover supporting up to 4 simultaneous links
- Advanced QoS with 8 traffic classes (granular per-application policy)
- Integrated next-generation firewall (stateful, application-layer filtering)
- Integrated IPS (intrusion prevention, signature-updated hourly)
- Cloud-managed portal with detailed analytics and flow reporting
- Multi-cloud connectivity: direct optimized paths to AWS, Azure, and GCP regions
- Zero-touch provisioning
- SD-WAN gateway appliance included at each site
- 99.9% uptime SLA
- Priority 24/7 support

### Uptime SLA
- **Guaranteed uptime:** 99.9% per site per month
- SLA credits issued for confirmed downtime exceeding the monthly window

### Use Cases — Best Fit
- Mid-market companies (50–500 employees) with 5–25 branch offices or retail locations
- Organizations moving critical SaaS workloads to the cloud (Microsoft 365, Salesforce, ServiceNow)
- Businesses requiring a firewall/IPS at each branch without deploying dedicated appliances separately
- Organizations with a hybrid MPLS + internet WAN strategy (SD-WAN overlays both seamlessly)
- Healthcare or financial services organizations needing encryption-in-transit across all sites

### Multi-Cloud Connectivity Detail
The Professional and Enterprise tiers provide direct SD-WAN gateways co-located with major cloud providers. This means traffic from a branch office to Microsoft Azure, for example, exits the SD-WAN fabric at an optimized cloud peering point rather than hairpinning through a central data center. This typically reduces latency to cloud applications by 30–60% compared to traditional hub-and-spoke WAN architectures.

---

## SD-WAN Enterprise (SDWAN-ENT)

### Description
Enterprise-grade SD-WAN with full SASE (Secure Access Service Edge) integration, global private backbone network, AI-driven optimization, and optional managed NOC service. Designed for large enterprises, global organizations, and businesses with stringent compliance requirements.

### Technical Specifications
- **Throughput per site:** Up to 10 Gbps
- **Sites supported:** 25–500+ sites (globally scalable)
- **WAN links per site:** Unlimited simultaneous links
- **Failover time:** Sub-second (< 1 second) with automatic path restoration
- **Management:** Advanced analytics platform with AIOps, custom dashboards, and API access

### Features
- AI-driven application optimization (real-time path selection, predictive rerouting before degradation)
- Multi-WAN failover with sub-second switchover
- Full SASE integration:
  - ZTNA (Zero Trust Network Access) — identity-based access replacing traditional VPN
  - SWG (Secure Web Gateway) — cloud-delivered URL filtering and threat inspection
  - CASB (Cloud Access Security Broker) — visibility and control of SaaS application usage
- Global private backbone network (our owned infrastructure spanning 40+ PoPs worldwide)
- Advanced analytics and AIOps (anomaly detection, capacity planning, root-cause analysis)
- Multi-cloud connectivity with private peering (not public internet) to AWS, Azure, GCP, Oracle Cloud
- Managed service option: 24/7 NOC monitoring and incident response included
- Custom traffic policies per application or user group
- SD-WAN gateway appliance (enterprise-class hardware) included at each site
- Dedicated account manager
- **Guaranteed uptime: 99.99%**

### Uptime SLA
- **Guaranteed uptime:** 99.99% per site per month
- Highest WAN availability commitment in our portfolio
- Translates to maximum ~53 minutes per year
- Proactive anomaly detection with automated remediation

### SASE Integration Details

**Zero Trust Network Access (ZTNA):** All user-to-application access is authenticated and authorized dynamically based on user identity, device posture, and context — regardless of physical location. Remote users access applications through the SASE cloud without a traditional VPN tunnel to a data center. This is the recommended path for organizations replacing aging remote access VPN infrastructure.

**Secure Web Gateway (SWG):** All web traffic from sites and remote users is inspected inline for malware, phishing, and policy violations before reaching the internet. SWG policies are centrally managed.

**Cloud Access Security Broker (CASB):** Provides visibility into which SaaS applications employees are using (including unsanctioned "shadow IT") and enforces data loss prevention (DLP) policies on cloud upload/download activity.

### Use Cases — Best Fit
- Large enterprises (500+ employees) with global or national footprint
- Organizations replacing legacy MPLS networks with internet-based WAN
- Financial services, insurance, or healthcare companies with strict security and compliance mandates (SOC 2, PCI-DSS, HIPAA, FedRAMP-aligned)
- Companies with a large remote/hybrid workforce requiring secure access (ZTNA replacing VPN)
- Organizations that want WAN and security managed as a single converged service
- Global businesses needing consistent performance outside North America (via private backbone)

### Compliance Alignment
SD-WAN Enterprise's SASE feature set directly addresses several regulatory compliance frameworks:

| Framework | Relevant SASE Controls |
|---|---|
| PCI-DSS | ZTNA (least-privilege access), SWG (traffic inspection), encrypted backbone |
| HIPAA | ZTNA (access controls), encryption in transit, audit logging |
| SOC 2 | Audit logs, CASB (data visibility), SWG (threat controls) |
| NIST 800-53 | ZTNA, IPS, anomaly detection via AIOps |

### Transition from MPLS
When a customer is currently on MPLS:
1. SD-WAN Enterprise supports hybrid operation — MPLS and internet links run simultaneously with intelligent load balancing. The customer doesn't need to cut over all at once.
2. Most MPLS contracts can be wound down site-by-site as SD-WAN is deployed.
3. Expected cost savings from MPLS-to-SD-WAN migration typically range from 40–70% in annual WAN spend, though actual savings depend on MPLS contract terms and required bandwidth.

---

## SD-WAN Tier Selection Guide

| Factor | Essentials | Professional | Enterprise |
|---|---|---|---|
| Sites | 1–5 | 5–25 | 25–500+ |
| Max throughput/site | 250 Mbps | 1 Gbps | 10 Gbps |
| Uptime SLA | None (ISP-dependent) | 99.9% | 99.99% |
| Failover time | < 60 sec | < 10 sec | < 1 sec |
| WAN links/site | 2 | 4 | Unlimited |
| Integrated security | None | Firewall + IPS | Full SASE (ZTNA, SWG, CASB) |
| Cloud connectivity | None | AWS/Azure/GCP | Private peering + global backbone |
| Managed NOC option | No | No | Yes |
| Best for | Simple redundancy | Mid-market cloud-first | Enterprise / compliance-driven |
