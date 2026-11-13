# FrameOps — Production Readiness & Integration Checklist

**Status:** FrameOps 2.0 is an operationally realistic, testable **fictional-data prototype** deployed on a free Render web service. The demo is **not production-ready** and must not collect actual homeowner, financial, or employee records.

## Business process and operational ownership

| Stage | Responsible team | Gate / evidence | Exception and escalation |
| --- | --- | --- | --- |
| Customer storefront and lead intake | Front Desk / Sales | Consent, contact, service address, source and request | Duplicates, spam, contact SLA, unreachable customer |
| Qualification | Front Desk | Confirmed scope and handoff | Lead age, unanswered request, eligibility |
| Measurement appointment | Sales / Measurement Tech | Appointment confirmation, technical site survey | Rescheduling, no access, measuring discrepancies |
| Proposal and approval | Sales | Approved itemized scope, labor, tax, exclusions | Price/version conflicts, change orders, discounts |
| Contract and financing | Sales / Financing / Accounting | Legally executed contract and cleared funds / lender confirmation | Financing declined, deposit mismatch, payment exceptions |
| Vendor procurement | Installation Manager / Vendor | Authorized PO, product specification, vendor ETA | Shipment delay, backorder, damage, substitutions |
| Permit, insurance, installation | Installation Manager | Approvals, COI, materials, crew capacity, customer consent | Permit delay, weather, subcontractor absence, reschedule |
| QA and financial closeout | Service Tech / Accounting | Completed punch list, homeowner acceptance, reconciled balance | Failed QA, dispute, incomplete invoice |
| Warranty and service | Warranty Coordinator / Customer Service | Warranty record, ticket response SLA and resolution | Repeat defect, claim denial, escalation |
| Customer satisfaction | Customer Service / Homeowner | Voluntary customer feedback and recovery follow-up | Low satisfaction, unresolved complaint, lack of consent |
| Google review request | Customer Service / Homeowner | Optional invitation only after closeout; link to verified business profile | No pressure, gating, incentives or fabricated reviews |

## Current prototype features

- 13+ sidebar operational views, job activity log, work queue, appointment and ETA tracking, alert banners, invoice register with printable sample invoices, service case ownership, satisfaction tracking and optional Google review-invitation status.
- Contextual “Ask FrameOps” assistant uses a **deterministic operating guide**, not a generative AI service. It does not read private company systems or perform changes on its own.
- Role selection demonstrates journeys, **not authentication or enforced access control**. API actor values are supplied by the browser.
- Public demo disables document upload and uses synthetic sample records. In-app notifications are stored; no external email, SMS, calendar, payment, lending or Google integration is active.
- Demo SQLite storage on Render's free ephemeral filesystem can be reset on instance restart or redeployment; it is not backed up or suitable for live customer use.

## Mandatory before going live with real customers

1. **Identity and tenancy:** use an OIDC provider (e.g. Okta, Entra, WorkOS), secure sessions/MFA, customer identity verification, server-enforced RBAC/ABAC with ownership checks, segregated tenant/customer data, and access audit logging. Disable arbitrary role switching for actual users.
2. **Data platform:** replace local SQLite with managed PostgreSQL; implement schema migrations, transactional outbox/event processing, backups and point-in-time restore, encryption and retention rules, input sanitization, a secure secrets manager, and a documented disaster recovery plan.
3. **Privacy and security:** consent and contact preferences, data minimization, uploads to private object storage with malware scanning and signed URLs, HTTPS transport, CSP and CSRF controls, rate limits and abuse protection, vulnerability scanning, dependency update process, security logging, and penetration tests.
4. **Commerce, documents and finance:** payment provider with PCI-aligned hosted flow/webhooks; accounting reconciliations; legally compliant e-signature; proper tax/payment invoicing and refunds; approved lender/financing API with secure consent and required regulatory disclosures. Never collect raw card information in the app.
5. **Operational integrations:** Gmail/Outlook, Twilio/email delivery, Google/Microsoft Calendar, supplier EDI/API, job/workforce availability, permit/COI evidence collection, reliable retries, idempotency and failed-message queues. Persist real ETA updates, notifications, delivery receipts and opt-outs.
6. **Scheduling and SLA engine:** timezone-aware scheduling with conflict detection, assignment/availability, business hours, customer channel preferences, holiday calendars, automated escalation rules, versioned ETAs and clear delay ownership.
7. **Sales and workflow controls:** product catalogs, price lists and quote versioning; approval gates and change orders; fraud and duplicate-lead checks; contract and warranty terms under legal review; jurisdiction-specific permit and insurance requirements.
8. **Customer satisfaction and Google reviews:** verified official Google Business Profile review link configured by the business (`GOOGLE_REVIEW_URL`). Customers must write and submit their own reviews. Record permission to contact; do not filter solicitation only to satisfied customers, offer incentives, or imply reviews are required. Customer-reported submission is **not verification** of publication.
9. **Quality and operations:** structured E2E tests (including permissions), load tests, mobile accessibility audits (WCAG), observability, SLOs and on-call alerts, runbooks, staged rollout, backup/restore drill, incident response, UAT with field staff, and rollback capability.

## Current Render settings (fictional demo only)

- Web service: `frameops-operations`, Python, free plan, `main` branch.
- Build: `echo "No dependencies to install"`; start: `python server.py`; health: `/health`.
- `PUBLIC_DEMO=1`; do not turn this off on the public sandbox.
- `GOOGLE_REVIEW_URL` should be set **only** to the official business's verified Google review link. If not configured, the app intentionally does not display a review link.
- Auto-deploy requires Render's GitHub provider to be authorized for the `sachintechpro/frameops-window-door-operations` repository. Test a future commit and inspect Render's deploy history to confirm automatic deployment, not just a dropdown setting.

## Suggested definition of done for production

A real customer should be able to progress from inquiry through customer support without unsupported manual handoffs **while retaining explicit exceptions and human approvals**. A release is production-ready only after engineering security sign-off, privacy and compliance approval, operational UAT, integration tests, environment resilience, ownership of runbooks, and positive rollback drills. This prototype is a reference implementation for planning that work, not a substitute for it.
