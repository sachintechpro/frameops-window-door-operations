/* FrameOps Operations Command Center — fictional-data portfolio edition.
 * Navigation, contextual guidance, operational records and inline status actions.
 * Not production identity, lender, billing, communications or Google integration.
 */
const OPS_MODULES = {
  'frontdesk': {title:'Front Desk',kicker:'Lead intake and customer coordination',desc:'Own the initial response, confirm scope, prioritize callbacks, and hand qualified work to Sales.',roles:['Front Desk'],stages:['New Lead','Qualified'],help:'Qualify a new inquiry, confirm an appointment, and escalate unanswered customer calls.'},
  'leads': {title:'Leads & Sales',kicker:'Sales pipeline',desc:'Manage homeowner conversations from qualified inquiry through verified measurements, proposal and agreement.',roles:['Sales','Front Desk'],stages:['New Lead','Qualified','Measurement Scheduled','Measurements Complete','Proposal Sent','Proposal Approved'],help:'Qualify, measure, price, follow up, and capture the contract acceptance.'},
  'measurements': {title:'Measurements',kicker:'Field survey and specifications',desc:'Coordinate site visits and accurately capture window/door openings, sizes, glazing and site constraints.',roles:['Measurement Tech'],stages:['Qualified','Measurement Scheduled','Measurements Complete'],help:'Book site measurement, capture dimensions per opening, then hand off the verified scope to Sales.'},
  'vendors': {title:'Vendors & Procurement',kicker:'Supplier delivery readiness',desc:'Track purchase orders, supplier acknowledgments, delivery dates, delay reasons, material receipt and escalations.',roles:['Vendor','Installation Manager'],stages:['Funding Cleared','Materials Ordered','Materials Received'],help:'After funding clears, place the PO, confirm supplier ETA, record exceptions, then confirm materials received.'},
  'installation': {title:'Installation',kicker:'Crew scheduling and quality control',desc:'Review permits, insurance, material readiness, crew calendars, installation reports and QA checkpoints.',roles:['Installation Manager','Service Tech'],stages:['Materials Received','Installation Scheduled','Installed','QA Passed'],help:'Only schedule work after materials and required checks are ready. Complete field work and QA before closeout.'},
  'financing': {title:'Financing',kicker:'Funding decision workflow',desc:'Track deposit requirements, external lender decisions and the funding gates that control procurement.',roles:['Financing','Accountant'],stages:['Contract Signed','Funding Cleared'],help:'Confirm external financing approval or the deposited amount. This app never issues loans or collects payments.'},
  'accounting': {title:'Accounting',kicker:'Receivables and reconciliation',desc:'Track estimates, deposit records, invoices, outstanding balances, and final payment clearance.',roles:['Accountant'],stages:['Contract Signed','Funding Cleared','Installed','QA Passed','Closed'],help:'Issue a draft invoice, record its sent/paid status, and verify all external payments before closing a job.'},
  'warranty': {title:'Warranty & Aftercare',kicker:'Post-installation obligations',desc:'Maintain warranty terms, linked service cases, technician follow-up and closure evidence.',roles:['Warranty Coordinator','Service Tech','Customer Service'],stages:['QA Passed','Closed'],help:'Close the paid and QA-approved installation, activate warranty coverage, and triage aftercare service tickets.'},
  'customer-service': {title:'Customer Service',kicker:'Customer satisfaction and review journey',desc:'Track issues through resolution, collect voluntary satisfaction feedback, and offer optional Google review links after closeout.',roles:['Customer Service','Warranty Coordinator','Front Desk'],stages:['New Lead','Installed','QA Passed','Closed'],help:'Respond to open cases, record customer sentiment and follow through without making review submission a condition of service.'},
  'documents': {title:'Documents & Invoices',kicker:'Traceable project records',desc:'Locate job documents and printable sample invoices, create new invoice records and track due dates.',roles:['Accountant','Sales','Front Desk'],stages:[],help:'Review contract, measurement, supplier, insurance, permit and warranty records and create/print sample invoices.'},
};
const appointmentTypes = {
 'Measurement': ['Front Desk','Sales'],
 'Vendor delivery': ['Vendor','Installation Manager'],
 'Installation': ['Installation Manager'],
 'QA inspection': ['Service Tech','Installation Manager'],
 'Warranty service': ['Service Tech','Customer Service','Warranty Coordinator'],
 'Follow-up call': ['Front Desk','Sales','Customer Service']
};
const appointmentOptions = () => Object.keys(appointmentTypes).filter(kind=>visibleTo(appointmentTypes[kind]));
const opData = () => state.data?.operations || {jobs:[],tasks:[],appointments:[],invoices:[],tickets:[],satisfaction:[],documents:[],alerts:[],payments:[]};
const opsJob = id => opData().jobs.find(j=>j.id===id);
const opsNum = (n,d=0) => Number(n||0).toLocaleString('en-US',{maximumFractionDigits:d});
const opsStatus = (s) => `<span class="ops-status ${/delayed|overdue|declined/i.test(s)?'hot':/closed|complete|paid|resolved|passed|verified/i.test(s)?'okay':''}">${esc(s||'Pending')}</span>`;
const opHint = (tip) => `<span class="ops-hint" tabindex="0" data-tip="${esc(tip)}" title="${esc(tip)}" aria-label="Help: ${esc(tip)}">?</span>`;
const opsLink = (label, view, main=false) => `<button class="button ${main?'primary':''} small" data-nav="${view}">${esc(label)}</button>`;
const opsJobButton = (id, label='Open job')=>`<button class="ops-link" data-job="${esc(id)}">${esc(label)} →</button>`;
const opsPageHead = (kicker,title,description,aside='')=> `<div class="ops-page-head"><div><div class="ops-eyebrow">${esc(kicker)}</div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${aside?`<div class="ops-head-actions">${aside}</div>`:''}</div>`;
const opsDate = (s) => s ? dateStr(s):'Not scheduled';
const opsNoData = (copy) => `<div class="ops-empty">${esc(copy)}</div>`;
const opsMetric = (name,value,desc,icon='◈') => `<div class="ops-metric"><div class="ops-metric-top"><span>${esc(name)} ${opHint(desc)}</span><span class="ops-metric-icon">${icon}</span></div><strong>${esc(String(value))}</strong><small>${esc(desc)}</small></div>`;
const opsAlerts = (limit=5) => {
 const alerts=opData().alerts.slice(0,limit);
 return alerts.length?alerts.map(a=>`<div class="ops-alert ${a.priority==='critical'?'critical':a.priority==='warning'?'warn':'info'}"><span class="ops-alert-symbol">${a.priority==='critical'?'!':a.priority==='warning'?'◷':'i'}</span><div><strong>${esc(a.title)}</strong><p>${esc(a.description)}</p></div><span class="ops-alert-kind">${esc(a.kind)}</span>${opsJobButton(a.job_id,'View')}</div>`).join(''):opsNoData('No attention items at this time.');
};
const opsStageProgress = j => {const n=state.data.stages.indexOf(j.stage);const pct=Math.round((n+1)*100/state.data.stages.length);return `<div class="ops-progress" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" title="${esc(j.stage)}"><span style="width:${pct}%"></span></div><small>${esc(j.stage)} · ${pct}% of operational milestones</small>`};
const opsJobTile = j => `<article class="ops-job-tile"><div class="ops-tile-top"><strong>${esc(j.homeowner)}</strong>${opsStatus(j.stage)}</div><p>${esc(j.service_type)} · ${esc(j.id)}</p>${opsStageProgress(j)}<div class="ops-tile-bottom"><span>${esc(j.assigned_sales||'Unassigned')}</span>${opsJobButton(j.id)}</div></article>`;
const canUpdateAppointment = a => a.status!=='Completed' && (state.role==='Admin'||state.role===a.owner_role||
 state.role==='Front Desk'||(state.role==='Installation Manager'&&['Installation','Vendor delivery','QA inspection'].includes(a.kind)));
const opsAppointment = a => `<article class="ops-record"><div class="ops-record-top"><strong>${esc(a.kind)}</strong>${opsStatus(a.status)}</div><p>${esc(a.homeowner||a.job_id)} · ${opsDate(a.scheduled_date)} · ${esc(a.time_window||'TBC')}</p><small>Owner: ${esc(a.owner_role)} · Assigned: ${esc(a.assignee)} · ETA: ${opsDate(a.eta_date)}</small>${a.delay_reason?`<div class="ops-record-warning">Delay: ${esc(a.delay_reason)}</div>`:''}<div class="ops-record-actions">${opsJobButton(a.job_id)}<button class="ops-link" data-ops-open="appointmentStatus" data-ops-id="${a.id}" ${canUpdateAppointment(a)?'':'hidden'} data-ops-job="${esc(a.job_id)}">Update / delay</button></div></article>`;
const opsInvoice = i => `<article class="ops-record"><div class="ops-record-top"><strong>${esc(i.number)}</strong>${opsStatus(i.status)}</div><p>${esc(i.homeowner||i.job_id)} · ${esc(i.category)} · ${moneyPrecise(i.amount)}</p><small>Due ${opsDate(i.due_date)} · ${esc(i.job_id)}</small><div class="ops-record-actions"><a class="ops-link" href="/api/ops/invoices/${Number(i.id)}/print" target="_blank" rel="noopener">Print invoice ↗</a>${opsJobButton(i.job_id)}<button class="ops-link" data-ops-open="invoiceStatus" data-ops-id="${i.id}" data-ops-job="${esc(i.job_id)}">Update</button></div></article>`;
const opsTicket = t=>`<article class="ops-record"><div class="ops-record-top"><strong>${esc(t.subject)}</strong>${opsStatus(t.status)}</div><p>${esc(t.homeowner||t.job_id)} · ${esc(t.category)}</p><small>Owner: ${esc(t.assignee)} · Target: ${opsDate(t.target_date)}</small><p class="ops-small-desc">${esc(t.detail)}</p><div class="ops-record-actions">${opsJobButton(t.job_id)}<button class="ops-link" data-ops-open="ticketStatus" data-ops-id="${t.id}" data-ops-job="${esc(t.job_id)}">Update case</button></div></article>`;
const opsTable = (headers,trs)=>`<div class="ops-table-scroll"><table class="ops-table"><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${trs||`<tr><td colspan="${headers.length}">No records</td></tr>`}</tbody></table></div>`;
const opsPanel = (title,subtitle,content,action='')=>`<section class="ops-panel"><div class="ops-panel-head"><div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div>${action}</div>${content}</section>`;
const opsCardGrid=(items)=>`<div class="ops-cardgrid">${items.join('')}</div>`;
const opsUpcoming = (items,limit=6) => items.filter(a=>a.status==='Scheduled'||a.status==='Delayed').slice(0,limit).map(opsAppointment).join('')||opsNoData('No upcoming appointments.');

function renderControlTower(){
 const d=opData(),active=d.jobs.filter(j=>j.stage!=='Closed'),due=d.tasks.filter(t=>t.due_date<new Date().toISOString().slice(0,10));
 const critical=d.alerts.filter(a=>a.priority==='critical');
 const unpaid=d.invoices.filter(i=>!['Paid — manually verified','Void'].includes(i.status));
 const intro=`<div class="ops-welcome"><div><div class="ops-eyebrow">OPERATIONS COMMAND CENTER</div><h1>Every job. Every handoff. One view.</h1><p>Manage lead-to-installation flow, track exceptions, and complete the customer journey through warranty and satisfaction.</p><div class="ops-welcome-actions">${opsLink('Create customer lead','storefront',true)}${opsLink('View all jobs','jobs')}</div></div><div class="ops-welcome-mark">FO<span>360°</span></div></div>`;
 const banner=critical.length?`<div class="ops-priority-banner"><div><strong>${critical.length} priority exception${critical.length===1?'':'s'} need attention</strong><p>Open the alert center to review missed ETAs, overdue visits, and service concerns.</p></div>${opsLink('View notifications','notifications')}</div>`:`<div class="ops-success-banner"><strong>Operational watch is active.</strong> Upcoming work and blockers are tracked below.</div>`;
 const metrics=`<div class="ops-metrics">${opsMetric('Open customer jobs',active.length,'Live work across departments','▦')}${opsMetric('Open work items',d.tasks.length,`${due.length} overdue tasks`,'☷')}${opsMetric('Upcoming appointments',d.appointments.filter(x=>x.status==='Scheduled').length,'Measurements, deliveries & installs','▤')}${opsMetric('Unpaid invoice records',unpaid.length,'Manual payment verification','＄')}${opsMetric('Service tickets',d.tickets.filter(x=>x.status!=='Resolved').length,'Customer & warranty follow-ups','◌')}</div>`;
 const pipeline=opsPanel('Lead-to-satisfaction journey','One customer record across the value stream',`<div class="ops-flow">${[['01','Capture lead','frontdesk'],['02','Measure & quote','measurements'],['03','Contract & fund','financing'],['04','Procure','vendors'],['05','Install & QA','installation'],['06','Warranty & delight','customer-service']].map(([n,label,view])=>`<button data-nav="${view}"><small>${n}</small><strong>${esc(label)}</strong><span>Explore →</span></button>`).join('')}</div>`);
 const schedule=opsPanel('Schedule & ETA watch','Upcoming appointments and supplier milestones',`<div class="ops-record-stack">${opsUpcoming(d.appointments,4)}</div>`,opsLink('Open scheduling','installation'));
 const alerts=opsPanel('Action center','Early warnings, delays and unblocked work',opsAlerts(6),opsLink('All alerts','notifications'));
 const jobs=opsPanel('Recently active customer jobs','Open any record to see the detailed work journey',opsCardGrid(d.jobs.slice(0,6).map(opsJobTile)),opsLink('Full pipeline','jobs'));
 return `<div class="page ops-dashboard">${intro}${banner}${metrics}${pipeline}<div class="ops-split">${schedule}${alerts}</div>${jobs}<div class="ops-disclaimer">Interactive portfolio sandbox. Role switching is simulated; financial records, contracts, notifications and Google review tracking are not external transactions.</div></div>`;
}

function renderStorefront(){
 const d=opData(),sample=d.jobs.find(j=>j.id===state.homeownerId)||d.jobs[0];
 return `<div class="page ops-dashboard ops-storefront">
  ${opsPageHead('CUSTOMER STOREFRONT','Better windows and doors. A clearer journey.','Explore replacement options, request a visit, and follow every milestone from first inquiry through warranty.')}
  <div class="ops-store-hero"><div><span class="ops-hero-tag">WINDOWS · ENTRY DOORS · PATIO DOORS</span><h2>Plan your next installation with confidence.</h2><p>Tell us what you are considering. A coordinator can qualify your request, arrange a measurement, and guide you through a sample project lifecycle.</p><button class="button primary" data-ops-open="storeLead">Request a free consultation →</button><div class="ops-hero-note">Demo: enter invented names and addresses only. No real requests are dispatched.</div></div><div class="ops-window-art"><div class="ops-window-sky"><span></span><span></span></div></div></div>
  <div class="ops-products">${[['Replacement windows','Energy performance, measured fit and frame options','▥'],['Entry & exterior doors','Security, weather protection and finished details','▣'],['Sliding patio doors','Daylight, access and easy operating systems','◫']].map(([t,desc,icon])=>`<article><div class="ops-product-icon">${icon}</div><h3>${t}</h3><p>${desc}</p><button data-ops-open="storeLead">Request estimate →</button></article>`).join('')}</div>
  ${opsPanel('Follow your sample project','Explore the homeowner journey using fictional records',`<div class="ops-track"><label>Choose sample customer <select id="homeowner-select" aria-label="Sample homeowner">${d.jobs.map(j=>`<option value="${esc(j.id)}" ${sample&&j.id===sample.id?'selected':''}>${esc(j.homeowner)} · ${esc(j.id)}</option>`).join('')}</select></label>${sample?`<h3>${esc(sample.homeowner)}</h3>${opsStageProgress(sample)}<p>Current stage: ${esc(sample.stage)}. The responsible team updates milestones, dates and outstanding actions.</p>${opsJobButton(sample.id,'Explore project record')}`:''}</div>`,opsLink('Open homeowner portal','homeowner'))}
  <div class="ops-disclaimer">FrameOps Storefront is a fictional workflow demonstration, not a live business or real customer ordering site.</div></div>`;
}

function opsModuleJobs(id){const c=OPS_MODULES[id],d=opData();if(!c)return [];
 if(id==='documents')return d.jobs;
 return d.jobs.filter(j=>c.stages.includes(j.stage)||d.tasks.some(t=>t.job_id===j.id&&c.roles.includes(t.role))||d.appointments.some(a=>a.job_id===j.id&&c.roles.includes(a.owner_role)));
}
function opsModuleActions(id){let buttons={
 'frontdesk':[['New lead','storeLead'],['Book visit','appointment']],
 'leads':[['New lead','storeLead'],['Schedule follow-up','appointment']],
 'measurements':[['Schedule site visit','appointment']],
 'vendors':[['Record supplier ETA','appointment']],
 'installation':[['Schedule crew / inspection','appointment']],
 'financing':[['Open job funding','', 'jobs']],
 'accounting':[['New invoice','invoice']],
 'warranty':[['Open service case','ticket']],
 'customer-service':[['Open service case','ticket'],['Record satisfaction','feedback']],
 'documents':[['Create invoice','invoice']]
 }[id]||[];
 return buttons.map(([title,modal,nav])=>nav?opsLink(title,nav):`<button class="button ${buttons.length===1?'primary':''} small" data-ops-open="${modal}">${esc(title)}</button>`).join('');
}
function opsModuleRecords(id){const d=opData(),jobs=opsModuleJobs(id),tasks=d.tasks.filter(t=>state.role==='Admin'?(OPS_MODULES[id]?.roles||[]).includes(t.role):t.role===state.role);
 const head=opsPageHead(OPS_MODULES[id].kicker,OPS_MODULES[id].title,OPS_MODULES[id].desc,opsModuleActions(id));
 const welcome=`<div class="ops-note-inline"><span>ⓘ</span><span><strong>How this team works:</strong> ${esc(OPS_MODULES[id].help)}</span><button class="ops-link" data-ops-ask="${esc(OPS_MODULES[id].title)}">Ask guide →</button></div>`;
 const jobtable=opsTable(['Customer / Job','Workflow stage','Owner','Value','Action'],jobs.slice(0,25).map(j=>`<tr><td><strong>${esc(j.homeowner)}</strong><small>${esc(j.id)} · ${esc(j.service_type)}</small></td><td>${opsStatus(j.stage)}</td><td>${esc(j.assigned_sales)}</td><td>${money(j.quote_total)}</td><td>${opsJobButton(j.id)}</td></tr>`).join(''));
 const queue=tasks.length?tasks.slice(0,12).map(t=>`<div class="ops-taskrow"><div><strong>${esc(t.title)}</strong><p>${esc(t.homeowner)} · Due ${opsDate(t.due_date)}</p></div>${opsJobButton(t.job_id)}</div>`).join(''):opsNoData('No open tasks assigned to this team.');
 let related='';
 if(['measurements','vendors','installation','frontdesk','leads'].includes(id)) {
  const kinds={'measurements':['Measurement'],'vendors':['Vendor delivery'],'installation':['Installation','QA inspection'],'frontdesk':['Follow-up call','Measurement'],'leads':['Measurement','Follow-up call']}[id];
  related=opsPanel('Appointments, ETAs & delays','Schedule changes create cross-team notifications',`<div class="ops-record-grid">${d.appointments.filter(x=>kinds.includes(x.kind)).map(opsAppointment).join('')||opsNoData('No scheduled work for this queue.')}</div>`);
 }
 if(id==='financing') related=opsPanel('Financing / deposit gates','Externally recorded approvals and payment status',opsTable(['Customer','Funding status','Contract / deposit','Next action'],jobs.map(j=>`<tr><td>${esc(j.homeowner)}</td><td>${opsStatus(j.financing_status)}</td><td>${money(j.quote_total)} / ${money(j.deposit_required)}</td><td>${opsJobButton(j.id,'Open financials')}</td></tr>`).join('')));
 if(id==='accounting') related=opsPanel('Invoice ledger','Printed invoices are sample documents, not payment requests',`<div class="ops-record-grid">${d.invoices.map(opsInvoice).join('')||opsNoData('No invoice records.')}</div>`);
 if(id==='warranty'||id==='customer-service')related=opsPanel('Trackable service cases','Response targets and resolution states',`<div class="ops-record-grid">${d.tickets.map(opsTicket).join('')||opsNoData('No open service cases.')}</div>`);
 if(id==='documents'){
 const docs=opsPanel('Document register','Category, owner and linked job',opsTable(['Document / Job','Type','Added','Open job'],d.documents.map(x=>`<tr><td><strong>${esc(x.name)}</strong><small>${esc(x.homeowner)} · ${esc(x.job_id)}</small></td><td>${esc(x.doc_type)}</td><td>${opsDate(x.created_at)}</td><td>${opsJobButton(x.job_id)}</td></tr>`).join('')));
 const invoices=opsPanel('Invoices','Create, print and track invoice status',`<div class="ops-record-grid">${d.invoices.map(opsInvoice).join('')}</div>`);
 return `<div class="page ops-dashboard">${head}${welcome}<div class="ops-metrics">${opsMetric('Document records',d.documents.length,'Referenced to one customer job','▤')}${opsMetric('Invoices',d.invoices.length,'Draft / sent / manually reconciled','＄')}${opsMetric('Jobs',d.jobs.length,'Customer-level document context','▦')}</div>${docs}${invoices}<div class="ops-disclaimer">Public upload is disabled. Documents here are sample metadata; invoice print pages are not payment requests.</div></div>`;
 }
 const priorities=opsPanel('Team work queue',`${tasks.length} assigned open action${tasks.length===1?'':'s'}`,queue,opsLink('View work queue','tasks'));
 const customers=opsPanel('Customer jobs / handoffs',`${jobs.length} relevant job${jobs.length===1?'':'s'}`,jobtable,opsLink('All jobs','jobs'));
 const extra=id==='customer-service'?opsPanel('Satisfaction & review follow-up','Feedback is voluntary; Google reviews are submitted by customers',`<div class="ops-feedback-list">${d.jobs.filter(j=>j.stage==='Closed').map(j=>{const s=d.satisfaction.find(x=>x.job_id===j.id);return `<article class="ops-feedback-card"><strong>${esc(j.homeowner)}</strong><span>${s?.rating?`${'★'.repeat(s.rating)}${'☆'.repeat(5-s.rating)}`:'Feedback not recorded'}</span><small>${esc(s?.review_status||'No review invitation')} · ${esc(j.id)}</small><div>${opsJobButton(j.id)}${d.review_url?`<a class="ops-link" href="${esc(d.review_url)}" target="_blank" rel="noopener noreferrer">Leave Google review ↗</a>`:''}<button class="ops-link" data-ops-open="feedback" data-ops-job="${esc(j.id)}">Feedback</button><button class="ops-link" data-ops-open="review" data-ops-job="${esc(j.id)}">Review invite</button></div></article>`}).join('')}</div>${!d.review_url?'<p class="ops-small-desc">Google review URL is not configured. Invitations may be tracked, but no external review link is sent.</p>':''}`):'';
 return `<div class="page ops-dashboard">${head}${welcome}<div class="ops-metrics">${opsMetric('Relevant jobs',jobs.length,'Across this operational stage','▦')}${opsMetric('Assigned tasks',tasks.length,'Next accountable steps','☷')}${opsMetric('Active exceptions',d.alerts.filter(a=>jobs.some(j=>j.id===a.job_id)).length,'Schedule, funding and service alerts','!')}</div>${related}${extra}<div class="ops-split">${priorities}${opsPanel('Exceptions to resolve','Dates, delays and follow-up requirements',opsAlerts(6))}</div>${customers}</div>`;
}

function opsFormField(name,label,type='text',required=true,options=[]){
 if(type==='select')return `<label class="ops-field"><span>${esc(label)}</span><select name="${name}" ${required?'required':''}>${options.map(o=>`<option value="${esc(o)}">${esc(o)}</option>`).join('')}</select></label>`;
 if(type==='textarea')return `<label class="ops-field"><span>${esc(label)}</span><textarea name="${name}" rows="3" maxlength="1200" ${required?'required':''}></textarea></label>`;
 return `<label class="ops-field"><span>${esc(label)}</span><input name="${name}" type="${type}" ${required?'required':''} ${type==='number'?'min="0" step="0.01"':''} ${type==='date'?`min="${new Date().toISOString().slice(0,10)}"`:''} maxlength="200"></label>`;
}
function opsCustomerSelect(selected='',filter=null){const arr=filter?opData().jobs.filter(filter):opData().jobs;return `<label class="ops-field"><span>Linked customer job</span><select name="job_id" required>${arr.map(j=>`<option value="${esc(j.id)}" ${selected===j.id?'selected':''}>${esc(j.id)} · ${esc(j.homeowner)} · ${esc(j.stage)}</option>`).join('')}</select></label>`;}
function opsModalHTML(kind,id='',job=''){
 const choices={
 storeLead:{title:'Request a consultation (demo)',desc:'A fictional storefront inquiry is converted into a tracked lead with front-desk ownership.',fields:opsFormField('homeowner','Customer name')+opsFormField('address','Project address')+opsFormField('service_type','Requested windows/doors')+opsFormField('email','Email (demo only)','email',false)+opsFormField('notes','Details of the work','textarea',false)},
 appointment:{title:'Book an operational milestone',desc:'Schedule a visit, delivery, crew assignment or customer callback.',fields:opsCustomerSelect(job)+opsFormField('kind','Appointment type','select',true,appointmentOptions())+opsFormField('scheduled_date','Scheduled date','date')+opsFormField('time_window','Time window / slot')+opsFormField('assignee','Assignee or crew','text',false)},
 appointmentStatus:{title:'Update schedule, ETA or delay',desc:'A delay reason and revised ETA appear on the dashboard and generate team alerts.',fields:opsFormField('status','Current status','select',true,['Scheduled','Delayed','Completed','Cancelled'].filter(status=>status!=='Completed'||!['Measurement','Installation','QA inspection','Vendor delivery'].includes(opData().appointments.find(a=>String(a.id)===id)?.kind)))+opsFormField('eta_date','Revised ETA','date')+opsFormField('reason','Reason / customer impact','textarea',false)},
 invoice:{title:'Create a sample invoice',desc:'Invoice is a local record only. It does not collect payments or send emails.',fields:opsCustomerSelect(job)+opsFormField('category','Invoice category','select',true,['Deposit','Progress','Final balance','Warranty service','Other'])+opsFormField('amount','Amount ($)','number')+opsFormField('due_date','Due date','date')+opsFormField('notes','Notes','textarea',false)},
 invoiceStatus:{title:'Update invoice status',desc:'Only record Paid when external funds were independently verified.',fields:opsFormField('status','Status','select',true,['Draft','Sent','Paid — manually verified','Void'])},
 ticket:{title:'Create a tracked service case',desc:'Customer Service owns the response target and follow-up.',fields:opsCustomerSelect(job)+opsFormField('category','Issue category','select',true,['Warranty','Installation concern','Scheduling','Billing question','Other'])+opsFormField('subject','Short subject')+opsFormField('detail','Customer concern','textarea')+opsFormField('target_date','Response target','date')},
 ticketStatus:{title:'Update service case',desc:'Change the operational status with the responsible customer service or service technician role.',fields:opsFormField('status','Case status','select',true,['Open','In progress','Awaiting customer','Resolved','Cancelled'])},
 feedback:{title:'Customer satisfaction follow-up',desc:'Record voluntary satisfaction after closeout. Low scores create recovery cases; no review pressure.',fields:opsCustomerSelect(job,j=>j.stage==='Closed')+opsFormField('rating','Satisfaction rating (1–5)','select',true,['5','4','3','2','1'])+opsFormField('feedback','What worked / what should improve?','textarea',false)+opsFormField('contact_permission','Permission to follow up','select',true,['no','yes'])},
 review:{title:'Optional Google review follow-up',desc:'This records invitation status only. We do not submit or verify Google reviews.',fields:opsCustomerSelect(job,j=>j.stage==='Closed')+opsFormField('status','Review invitation status','select',true,['Invited','Opened Google review page','Customer-reported submitted','Declined'])},
 };
 const def=choices[kind];if(!def)return '';
 return `<div class="modal-scrim ops-modal-scrim" id="ops-modal-scrim"><section class="modal ops-modal" role="dialog" aria-modal="true" aria-labelledby="ops-dialog-title"><div class="modal-head"><div><h2 id="ops-dialog-title">${esc(def.title)}</h2><p>${esc(def.desc)}</p></div><button class="modal-close" data-ops-close aria-label="Close">×</button></div><form id="ops-form" data-ops-kind="${esc(kind)}" data-ops-id="${esc(id)}" class="modal-body"><div class="form-error" id="ops-form-error"></div>${def.fields}<div class="modal-actions"><button type="button" class="button" data-ops-close>Cancel</button><button type="submit" class="button primary">Save record</button></div></form></section></div>`;
}
function opsOpen(kind,id='',job=''){
 if(!opsActAs(kind))return;
 if(kind==='appointmentStatus'&&!opData().appointments.some(a=>String(a.id)===id&&canUpdateAppointment(a)))return;
 document.querySelector('#modal-root').innerHTML=opsModalHTML(kind,id,job);
 document.querySelector('#ops-modal-scrim input,#ops-modal-scrim select,#ops-modal-scrim textarea')?.focus();
}
function opsActAs(kind){
 const role=state.role;
 const expected={storeLead:['Admin','Front Desk','Sales'],appointment:['Admin','Front Desk','Sales','Measurement Tech','Installation Manager','Service Tech','Customer Service','Vendor','Warranty Coordinator'],appointmentStatus:['Admin','Front Desk','Sales','Measurement Tech','Vendor','Installation Manager','Service Tech','Customer Service','Warranty Coordinator'],invoice:['Admin','Accountant','Financing'],invoiceStatus:['Admin','Accountant'],ticket:['Admin','Customer Service','Homeowner','Service Tech','Front Desk','Warranty Coordinator'],ticketStatus:['Admin','Customer Service','Service Tech','Warranty Coordinator'],feedback:['Admin','Homeowner','Customer Service','Warranty Coordinator'],review:['Admin','Homeowner','Customer Service','Warranty Coordinator']};
 return kind==='appointment'?appointmentOptions().length>0:!expected[kind]||expected[kind].includes(role);
}
async function opsSubmit(form){
 const kind=form.dataset.opsKind,vals=Object.fromEntries(new FormData(form).entries()),id=form.dataset.opsId;
 let path='',data={...vals,actor:state.role};
 if(kind==='storeLead'){path='/api/jobs';data={...vals,actor:state.role,lead_source:'Storefront'};}
 else if(kind==='appointment')path='/api/ops/appointments';
 else if(kind==='appointmentStatus')path=`/api/ops/appointments/${encodeURIComponent(id)}/status`;
 else if(kind==='invoice')path='/api/ops/invoices';
 else if(kind==='invoiceStatus')path=`/api/ops/invoices/${encodeURIComponent(id)}/status`;
 else if(kind==='ticket')path='/api/ops/tickets';
 else if(kind==='ticketStatus')path=`/api/ops/tickets/${encodeURIComponent(id)}/status`;
 else if(kind==='feedback')path='/api/ops/feedback';
 else if(kind==='review')path='/api/ops/review';
 if(!opsActAs(kind))throw Error('Switch the Working as role to the responsible department, or Admin, then retry.');
 const r=await api(path,{method:'POST',body:JSON.stringify(data)});
 document.querySelector('#modal-root').innerHTML='';
 await load();
 toast(r.message||'Record saved');
}

function opsAddGuide(){
 if(document.querySelector('#ops-guide'))return;
 document.body.insertAdjacentHTML('beforeend',`<div class="ops-guide-shell" id="ops-guide"><button class="ops-guide-button" id="ops-guide-launch" aria-label="Open FrameOps operating guide" aria-expanded="false"><span>✦</span><span>Ask FrameOps</span></button><section class="ops-guide-panel" id="ops-guide-panel" hidden aria-label="FrameOps guided help"><div class="ops-guide-header"><div><strong>FrameOps Guide</strong><small>How to operate every stage</small></div><button id="ops-guide-close" aria-label="Close guide">×</button></div><div class="ops-guide-messages" id="ops-guide-messages" aria-live="polite"><div class="ops-guide-reply"><strong>How can I help?</strong><p>Ask me how to qualify leads, schedule measurements, handle supplier delays, manage invoices, or complete warranty and satisfaction.</p></div></div><div class="ops-guide-prompts">${['Process a new lead','Handle an ETA delay','Close a job','Google review follow-up'].map(x=>`<button data-ops-question="${esc(x)}">${esc(x)}</button>`).join('')}</div><form id="ops-guide-form"><input id="ops-guide-input" placeholder="Ask how to operate FrameOps..." maxlength="400" aria-label="Ask a question" required><button type="submit" aria-label="Send question">➤</button></form><div class="ops-guide-foot">Workflow guide · Not connected to external AI</div></section></div>`);
}
async function opsAsk(question){
 const messages=document.querySelector('#ops-guide-messages');if(!messages)return;
 document.querySelector('#ops-guide-panel').hidden=false;
 document.querySelector('#ops-guide-launch').setAttribute('aria-expanded','true');
 messages.insertAdjacentHTML('beforeend',`<div class="ops-guide-user">${esc(question)}</div>`);
 try{
  const response=await api('/api/ops/guide',{method:'POST',body:JSON.stringify({question,context:state.view,role:state.role})});
  messages.insertAdjacentHTML('beforeend',`<div class="ops-guide-reply"><strong>${esc(response.title)}</strong><p>${esc(response.answer)}</p><button class="ops-link" data-nav="${esc(response.view||'overview')}">Open this section →</button></div>`);
 }catch(err){messages.insertAdjacentHTML('beforeend',`<div class="ops-guide-reply"><p>Help is unavailable: ${esc(err.message)}</p></div>`)}
 messages.scrollTop=messages.scrollHeight;
}
window.addEventListener('DOMContentLoaded',opsAddGuide);
document.addEventListener('click',e=>{
 if(e.target.closest('#ops-guide-launch')){const p=document.querySelector('#ops-guide-panel');p.hidden=!p.hidden;document.querySelector('#ops-guide-launch').setAttribute('aria-expanded',String(!p.hidden));return;}
 if(e.target.closest('#ops-guide-close')){document.querySelector('#ops-guide-panel').hidden=true;document.querySelector('#ops-guide-launch').setAttribute('aria-expanded','false');return;}
 const prompt=e.target.closest('[data-ops-question]');if(prompt){opsAsk(prompt.dataset.opsQuestion);return;}
 const hint=e.target.closest('[data-ops-ask]');if(hint){opsAsk('How do I use '+hint.dataset.opsAsk+'?');return;}
 const modalBtn=e.target.closest('[data-ops-open]');if(modalBtn){opsOpen(modalBtn.dataset.opsOpen,modalBtn.dataset.opsId||'',modalBtn.dataset.opsJob||'');return;}
 if(e.target.closest('[data-ops-close]')||e.target.id==='ops-modal-scrim'){document.querySelector('#modal-root').innerHTML='';return;}
});
document.addEventListener('submit',async e=>{
 if(e.target.id==='ops-form'){
  e.preventDefault();const f=e.target,button=f.querySelector('button[type=submit]'),err=f.querySelector('#ops-form-error');button.disabled=true;button.textContent='Saving…';err.style.display='none';
  try{await opsSubmit(f);}catch(ex){err.textContent=ex.message;err.style.display='block';button.disabled=false;button.textContent='Save record'}
 }
 if(e.target.id==='ops-guide-form'){
  e.preventDefault();const field=document.querySelector('#ops-guide-input');const q=field.value.trim();if(q){field.value='';await opsAsk(q)}
 }
});
