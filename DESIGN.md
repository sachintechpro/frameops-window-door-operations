# FrameOps — Full product design

## Product promise

One client-owned operating system for a residential window-and-door business. A job begins as a homeowner inquiry, carries one immutable job identifier, and collects all decisions, tasks, documents, suppliers, people and payments until installation, accounting closeout and warranty aftercare. The company hosts and operates the solution; the software developer does not operate customer jobs.

## Users and boundaries

| Persona | Owns | Access in the proposed production app |
|---|---|---|
| Owner / admin | Portfolio, margins, staffing, escalations, policy | All jobs, role assignment, approvals and audit |
| Front desk | Lead intake, appointments, inbound calls, homeowner updates | Contact and scheduling; limited finance fields |
| Sales | Consultation, proposal, discounts, contract handoff | Assigned jobs, scope, pricing, approval status |
| Measurement technician | Appointment, accurate sizes, installation constraints and photos | Assigned site visits; no financial data |
| Accountant | Deposit terms, loan statuses, invoice, refunds, reconciliation | Finance data; no unnecessary private field photos |
| Installation manager | Supplier selection, ordering, crew planning, permits, COI, quality risks | Fulfillment and readiness; required documents |
| Vendor / supplier | PO acknowledgment, material status, ETA and shortages | Assigned POs only, not homeowner financials |
| Service / installation technician | Work order, checklists, QA, issues, warranty visits | Assigned installs/service jobs only |
| Homeowner | Proposal, signed documents, milestones, financing links, payment links, service | Only their own projects and documents |

## Canonical lifecycle (event-driven)

**Inquiry → Qualification → Measurement appointment → Measured scope → Proposal → Homeowner approval → Contract acceptance → Funding verification → PO → Materials receipt → Installation scheduling → Installation completion → QA/punch list → Final reconciliation → Closeout & warranty → Service cases.**

This is a *default path*, not the only business path. Real products also require parallel tasks and conditional loops:
- **Re-measure / design change:** new measurement revision and price revision before homeowner re-approval.
- **Change order:** scope or price changes after contract need versioned approval, revised finance plan and notifications to purchasing.
- **Vendor delay:** revised ETA triggers installation-manager alert, rescheduling, homeowner update.
- **Partial delivery:** shortage creates discrepancy and blocks only affected opening(s) if phased installation is permitted.
- **Permits and HOA:** per-city / homeowner requirements resolved before applicable construction.
- **Insurance:** COI from installer/subcontractor; optionally homeowner insurance claim documentation where relevant.
- **Financing:** opt-in, secure redirect to lender, lender status webhooks, funding authorization separate from cash posted.
- **Homeowner cancellations:** cancellation/refund approval and disposition of custom materials.
- **Punch list / failed QA:** correction tasks, reinspection and revised closeout date.
- **Warranty case:** issue intake, eligibility review, supplier vs labor responsibility, appointment, resolution, signed outcome.

## Record structure

- **Customer & Property:** homeowner ID, address, best contact, consent, occupancy and access notes.
- **Lead & Opportunity:** channel/source, campaign, referral, consult, next follow-up, lead score.
- **Job:** stable job ID, status, owner, priority, target dates, blockers and SLA.
- **Openings / Product Items:** window/door location, height, width, material, finish, glazing, tempered safety glass, energy specs, labor, disposal.
- **Measurement Revisions:** technician, timestamp, photos, dimension confidence, remeasure status.
- **Quotes & Contracts:** versioned quote lines, tax, discounts, deposit, cancellation and warranty terms, consent/e-sign audit.
- **Financials:** invoice, payment requests, settlement IDs, financing consent/status, refunds, credit notes, reconciliation.
- **Fulfillment:** supplier catalog, PO, order line, acknowledgments, tracking, ETA, goods receipt and damage checks.
- **Field Work:** crew assignment, appointment, work order, checks, installation images, punch lists, homeowner handover.
- **Compliance:** permit requirements, COIs, policy expiry, inspections, evidence, access control.
- **Documents:** tags, version, uploader, privacy scope, required/optional status, immutable signed artifacts.
- **Communications:** call/SMS/email log, subscription and quiet hours, deliveries, opt-out and escalations.
- **Events & Tasks:** source event, owning role, due date, escalations, resolved by, timestamp, link to job.
- **Warranty / Service:** coverage by product and labor, manufacturer registration, claims, technician visit and outcomes.

## Navigation

- Overview (owner/admin KPI dashboard, alerts and conversion funnel)
- Leads & Jobs (kanban/table, filtering, lead intake)
- Job workspace (Journey, Scope, Tasks, Financials, Documents, Activity, Team)
- My Work Queue (personal handoffs and overdue assignments)
- Scheduling / calendar (sales, measurement, installers, warranty)
- Procurement (POs, vendor ETAs, receipts, shortages)
- Finance & financing (deposit/final billing, receivables, lender statuses)
- Documents / contracts (templates, e-sign, retention)
- Warranty & service (service cases)
- Notifications / messaging (role-appropriate inbox, customer messaging)
- Homeowner portal and supplier portal
- Owner reports and administration (permissions, products, prices, automation rules, branches)

The MVP prototype implements a subset of these screens and workflows, not the full production module list.

## Notification matrix

| Trigger | Primary recipient | Secondary recipients |
|---|---|---|
| New qualified lead | Sales | Front Desk |
| Measurement booked | Measurement Tech | Front Desk |
| Site measurements complete | Sales | Installation Manager |
| Quote approved and contract accepted | Accountant | Sales |
| Deposit or financing verified | Installation Manager | Sales |
| PO placed or ETA changed | Vendor | Installation Manager |
| Goods received | Installation Manager | Front Desk |
| Installation booked / moved | Field Crew | Homeowner, Front Desk |
| Installation complete | QA / Service | Accountant |
| QA approved | Accountant | Homeowner |
| Closeout and warranty active | Homeowner | Front Desk / Service |
| Warranty service requested | Service Team | Front Desk |

Notifications need idempotency keys, user time-zone preferences, business-hour quiet windows, retries and escalation policies. For failures, never send homeowner messages that reveal vendor internal notes or unnecessary financial details.

## Delivery plan

**Phase 1 — Operations MVP:** real auth and authorization, lead intake, jobs, task engine, field measurement, proposal/contract versioning, documents, audit, calendar, notification inbox.

**Phase 2 — Financials and fulfillment:** payment processor, financing partner, purchase orders, vendor supplier access, ETA/reconciliation, field checklists and QA sign-off.

**Phase 3 — Customer experience:** homeowner portal, e-sign, self-service payments, approved SMS/email notifications and warranty service workflows.

**Phase 4 — Operational intelligence:** scheduling capacity, exception automation, aging and bottleneck reports, cycle time, conversion and margin analytics, configurable escalations.

## Engineering and deployment

A robust production architecture might use PostgreSQL for transactional data, an API layer, server-side auth and role/record-level policy, an auditable state machine, durable queues/outbox for notifications, private object storage for files, and managed integration adapters. Keep all keys in company-owned infrastructure. Vendor-facing portals should expose only their own purchase orders; homeowner sessions should only access their own jobs. Conform to applicable state licensing, contract, finance, consumer privacy, card-payment and retention requirements with legal/compliance review rather than embedding blanket rules.
