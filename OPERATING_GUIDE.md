# FrameOps — Operations Guide (Demo)

Start at **Admin Dashboard**. All records are fictional and may reset. Use **Working as** to preview the responsible department; this does not authenticate a real employee. Click **Ask FrameOps** in the bottom-right to open the built-in step-by-step guide.

## Navigate from the customer side

1. **Customer Storefront:** explore window/door products and submit a fictional consultation request. The new estimate-first storefront opens a browser-local simulated project with Front Desk, Sales and customer notifications. Legacy admin lead creation remains a separate fictional SQLite demo workflow.
2. **Front Desk / Leads & Sales:** open the newly created record, qualify the lead, book the measurement and record the next step.
3. **Measurements:** add openings with sizes (inches), frame/glazing and field notes. Complete the measurement stage so Sales can prepare the quote.
4. **Leads & Sales:** record the proposed price, homeowner approval and contract acceptance. The demo does not execute a real legal signature.
5. **Financing / Accounting:** record externally verified funds or a mock lender decision. The funding gate must clear before procurement.
6. **Vendors:** create a supplier PO, confirm the ETA, and mark the shipment received. To simulate delay, select the appointment → **Update / delay**, enter a reason and revised ETA. Dashboard banners and notifications update.
7. **Installation:** check required permits and insurance, schedule the crew, document completed installation and pass QA.
8. **Accounting / Documents & Invoices:** reconcile payments, create printable sample invoices, update their state and close the fully paid/QA-approved job with warranty terms.
9. **Warranty / Customer Service:** open trackable service tickets, set response targets and follow the tickets to resolution.
10. **Customer satisfaction and Google reviews:** after closeout, record an optional rating and feedback. Ratings of 3 or below create a service recovery follow-up. An optional Google review invitation may be recorded. Only a verified business review link is shown when configured; customers submit reviews on Google themselves.

## Workflow controls and information design

- Every job has a single ID and shared timeline; the next-stage button enforces core readiness gates.
- The **Admin Dashboard** shows active jobs, task count, appointments, invoice records, service cases, alerts and the end-to-end lifecycle.
- **Notifications** are in-app records, not real messages or promises of communication to a person.
- **Tooltips** on dashboard measures clarify calculation context; role-specific module descriptions explain team ownership.
- **Appointments and ETA changes** are tracked separately from core job stages so a delay does not silently advance or reverse business milestones.
- **Documents & Invoices** lists sample document references and printable invoice pages. Public file uploads are intentionally disabled.
- **Ask FrameOps** is a deterministic help guide with category keywords, relevant instructions and a jump to the module, not a connection to a language model or private data.

## Documentation

See `DESIGN.md` for the original operational concept, `PRODUCTION_READINESS.md` for mandatory architecture/security/integration work, and `TESTING.md` for regression validation. Do not use real homeowner addresses, contacts, payment information, or documents in this public environment.

## Customer storefront & local demonstration journey (v2.3)

1. **Customer Storefront:** search among 17 fictional products, filter material/category, compare the indicative installed-price ranges, add desired units and submit an example estimate inquiry. Use invented names and addresses only.
2. **Live Journey Simulator:** after a new quote request, change **Working as** to Front Desk and qualify the lead; Sales and Measurement Tech can take subsequent steps; the customer can approve the fictional quote and click **Pay sample advance** without entering any card details.
3. **Handoffs:** the fictitious payment moves the project to supplier preparation and adds notifications for Accounting, Financing, Sales, Vendor, Installation, and customer. Changes to delivery ETA or installation dates (including cancellation/rebooking) route in-app alerts to the affected departments.
4. **Browser-local “real time”:** other tabs of the same browser/device receive changes through localStorage events and BroadcastChannel. Other devices are **not** linked, and the backend does not process simulated payments, scheduling or notifications.
5. **Business & Social Settings:** add the actual business’s own HTTPS profile links on Facebook, X, Medium, LinkedIn, YouTube, Instagram and TikTok. Enable only the desired sites; preview them on the customer storefront. Settings persist on this device/browser only. No social network credentials or APIs are used.

**Security:** The business settings and role dropdown are not protected by authentication in this public demo. There are no real business owners, logged-in customers, real deposits, tax calculations, supplier integrations or externally delivered notifications.


## Version 2.4 — Customer fast-quote and staff schedule simulation

**Customer storefront first**: select one or more fictional products → `Instant quote` → enter only invented example.com contact details and a `555` phone number → choose measurement and target-installation arrival windows → type a matching fictional signature name → accept the demo terms → select the simulated payment method → submit. The resulting browser-local project immediately records an advance of at least 10%, reserves both dates and notifies the assigned measurement technician, customer, owner, Sales, Front Desk, Accounting, Vendor and impacted Installation staff through in-app role inboxes.

**Customer Project Portal**: monitor the project stage, quote and advance/balance, confirm or reschedule appointments, cancel with a reason, open a printable sample agreement/invoice/receipt/confirmation, use fictional SMS/email CTA previews and review warranty after closure. Installation reservation remains contingent on actual measurement, materials and readiness in a real workflow.

**Staff Console**: click `Staff workspace` from the customer site, then select `Quote & Schedule Console`. Sales/Admin can negotiate **0–5%** before the customer confirms a quote. The price engine protects supplier cost × 1.35 × 1.10 after discounts. Measurement Tech marks measurements complete; Vendor confirms materials or records delivery delays; Installation Manager / Service Tech closes field work. Simulate a final payment before activating a sample warranty.

**Appointments**: the demo generates 24-hour and 1-hour reminder previews only while the browser is open, or when using the demo-clock controls. Rescheduling or cancellation invalidates prior reminder keys and creates new role-specific events. No SMS or email is sent, and separate browsers/devices do not share the same project. Real reminders need a backend scheduler, authoritative timezone, customer consent, delivery provider and idempotent retry mechanism.

**Role access is a simulation**: a dropdown does not authenticate customers or staff. No financial details, actual payment cards or real signatures should be entered. Browser-stored records are fictional and intended for interface testing only.
