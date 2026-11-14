# FrameOps — Forward Deployment Case Study

> **Scenario status:** Fictional portfolio case study. The business, people, jobs, addresses, and operating data are invented. This documents an implementation approach and working demo; it does not claim a customer engagement or a production customer deployment.

**[Open the live demo](https://frameops-operations.onrender.com/)** · **[Source repository](https://github.com/sachintechpro/frameops-window-door-operations)** · [Operating guide](OPERATING_GUIDE.md) · [Production readiness checklist](PRODUCTION_READINESS.md)

## The business problem

A growing residential window-and-door installer coordinates leads, site measurements, proposals, contracts, financing, supplier orders, installations, and warranty work across separate spreadsheets and communication channels. A job can stall when the next owner is unclear or a prerequisite is missing. Owners need to spot blocked work; office and field teams need to know what to do next.

The first release goal is a shared operational view that makes each job's stage, next assignment, dependencies, and activity visible. It is not intended to replace accounting, payment, e-signature, supplier, or insurance systems.

## Example discovery summary

These are **illustrative discovery findings**, not notes from a real customer interview.

| Finding to validate | Example question | Product implication |
| --- | --- | --- |
| Job details are re-entered at handoffs | Where is the authoritative customer and job record today? | Keep a common job record and visible activity history. |
| Measurement and product details are often incomplete | What must a technician record before a proposal can be prepared? | Capture structured measurements and flag missing information. |
| Teams are unsure who owns delayed work | Who receives the next task after each successful milestone? | Create a role-specific assignment and work queue at each handoff. |
| Materials or approvals can block installation | Which conditions must be satisfied before scheduling? | Enforce readiness gates and show the blocking reason. |
| Owners learn about exceptions late | Which overdue or blocked jobs require escalation, and after how long? | Surface exceptions for review; tune thresholds with business owners. |

A real discovery would confirm current systems, terminology, volumes, roles, exceptions, data ownership, access needs, and success measures before implementation.

## Roles and workflow

The demo includes owner/admin, front desk, sales, measurement technician, accounting, vendor, installation manager, service technician, customer service, warranty coordinator, financing, and homeowner perspectives.

A representative job path is:

**New Lead → Qualified → Measurement Scheduled → Measurements Complete → Proposal Sent → Proposal Approved → Contract Signed → Funding Cleared → Materials Ordered → Materials Received → Installation Scheduled → Installed → QA Passed → Closed**

Each successful milestone completes the current assignment and creates the next assignment and in-app notifications together. The workflow prevents skipping required stages. Readiness rules include funding before procurement, materials and applicable approvals before installation scheduling, and passed QA plus a paid balance before closeout.

### Example acceptance criteria

- **Lead handoff:** Given a new lead, when Front Desk qualifies it, then its stage changes to Qualified, the Front Desk assignment completes, and Sales receives the next assignment and notification.
- **No duplicate handoff:** Given a completed transition, when the same transition is retried, then the job does not receive a duplicate next-stage assignment.
- **Installation readiness:** Given a job without required materials or applicable approvals, when a user attempts to schedule installation, then the transition is blocked and the missing prerequisite is shown.
- **Closeout:** Given a job without passed QA or a recorded paid balance, when a user attempts to close it, then closeout is blocked.
- **Role access:** Given a non-admin role, when the user opens the application, then only that role's permitted work areas are available.

These criteria describe expected demo behavior. A customer rollout would require the business to approve detailed role permissions and exception rules.

## Key design decisions

- **One job record with explicit milestones:** supports a shared view and traceable handoffs. It requires clear ownership of data corrections.
- **One-step transitions with readiness checks:** reduce accidental skips and duplicate work. The customer must define how authorized corrections and urgent exceptions work.
- **Role-specific work queues:** make the next action clear to each team. They are only useful if assignments and due dates reflect actual operating practice.
- **In-app notifications on successful handoff:** keep the demo self-contained. Production email, text, or push notifications require consent, delivery monitoring, preferences, and failure handling.
- **Separate browser-only customer journey:** the storefront simulator demonstrates a customer flow without claiming production integrations. Its local browser state is not the same shared workspace as the legacy operations module.

## What is implemented in the portfolio demo

- A Python and SQLite operations workspace with fictional seeded jobs, role views, stage rules, assignments, and in-app notifications.
- A browser-only storefront and journey simulator with fictional catalog and simulated transactions.
- A public demo designed for walkthroughs with sample data and reset behavior.
- Operating and production-readiness documentation in this repository.

The demo does **not** connect to a real CRM, accounting package, supplier, lender, payment service, e-signature provider, or Guidewire system. It is not a production multi-tenant service. The storefront's simulated project state is browser-local. Public demo records and hosting persistence have limitations documented in the repository.

## Deployment and cutover approach

### Portfolio demo deployment

The public portfolio deployment runs as a Render web service from this repository. The repository includes Render configuration and uses `python server.py` as its start command. This demonstrates deploying and reviewing a running application; it is **not** evidence of a customer production cutover or customer environment.

### Proposed customer rollout checklist

Before a real rollout, confirm and record:

- [ ] Customer-approved scope, workflows, role matrix, and exception paths.
- [ ] Hosting location, environment configuration, access controls, and secret handling.
- [ ] Database choice, migration plan, backup schedule, and tested restore procedure.
- [ ] Required integrations, credentials, test endpoints, ownership, and failure behavior.
- [ ] Initial data mapping, cleansing, import reconciliation, and data sign-off.
- [ ] Acceptance-test results for normal paths, blocked paths, permissions, and duplicate requests.
- [ ] Support contacts, escalation rules, monitoring, and rollback decision owner.
- [ ] Training completed for office users, field users, and administrators.
- [ ] Go/no-go approval, cutover window, fallback process, and post-launch review date.

A real customer deployment would require production controls beyond the current demo, including durable storage, production identity and access management, audit retention, private document storage, backups, secured communications, and any required business-system integrations. See [Production Readiness](PRODUCTION_READINESS.md).

## Day-one operating guide

- **Owner / Admin:** review blocked and overdue jobs, resolve escalations, and confirm queue ownership.
- **Front Desk:** enter a lead, qualify it, and confirm the next owner is assigned.
- **Sales:** review qualified work, coordinate measurement, and record proposal decisions.
- **Measurement Technician:** open assigned visits, record site details, and flag missing or unsafe conditions.
- **Accounting / Financing:** record the agreed funding or payment status; the demo does not move money or contact a lender.
- **Vendor / Installation Manager:** update material readiness and scheduling milestones; the demo does not send supplier orders.
- **Service Technician:** record installation completion and QA results, then hand exceptions back to the owner.
- **Administrator:** manage deployment configuration, accounts, backups, and support according to the environment's runbook.

Use fictional information in the public demo. For module details, see the [Operating Guide](OPERATING_GUIDE.md).

## Outcomes to measure in a real pilot

No business improvement is claimed from this fictional demo. A real pilot could establish a baseline and measure:

- Median time from lead receipt to first response.
- Time from completed measurement to proposal.
- Number and age of jobs blocked at each handoff.
- Installation reschedules caused by missing materials or approvals.
- Rework or punch-list frequency at closeout.
- Time to resolve customer service and warranty requests.

Any sample dashboard values should be labeled **illustrative scenario data** until measured against an agreed baseline and a real operating period.

## Evidence map

| FDE activity | Evidence in this case study |
| --- | --- |
| Understand the operating problem | Example discovery questions and findings to validate |
| Translate needs into a solution | Roles, lifecycle, readiness rules, acceptance criteria |
| Build and integrate | Python/SQLite workflow module plus a separate browser-only customer simulator |
| Validate behavior | Workflow rules and the repository's automated tests |
| Deploy and prepare handoff | Live portfolio demo, deployment boundary, proposed cutover and day-one guides |
| Measure value | Pilot metrics without invented improvement claims |
