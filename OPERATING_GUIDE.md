# FrameOps — Operations Guide (Demo)

Start at **Admin Dashboard**. All records are fictional and may reset. Use **Working as** to preview the responsible department; this does not authenticate a real employee. Click **Ask FrameOps** in the bottom-right to open the built-in step-by-step guide.

## Navigate from the customer side

1. **Customer Storefront:** explore window/door products and submit a fictional consultation request. FrameOps creates a lead with a Front Desk task.
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
