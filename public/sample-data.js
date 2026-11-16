/* FrameOps / sample-input assistant
 * Presentation-only convenience for fictional demo use.
 * Never submits a form, dispatches a business action, uploads files, or calls an API.
 * Sample values are illustrative and must be reviewed before any explicit submission.
 */
(function () {
  "use strict";
  const EXAMPLE_ADDRESS = "100 Example Canyon Road, Chatsworth, CA 91311";
  const EXAMPLE_EMAIL = "morgan.rivera@example.com";
  const EXAMPLE_PHONE = "202-555-0147";
  const EXAMPLES = {
    homeowner:"Morgan Rivera",customer:"Morgan Rivera",full_name:"Morgan Rivera",
    phone:EXAMPLE_PHONE,email:EXAMPLE_EMAIL,address:EXAMPLE_ADDRESS,
    service_type:"Replace 3 living-room windows and 1 sliding patio door",
    lead_source:"Website",assigned_sales:"Jordan Lee",priority:"Normal",
    room:"Living room, west-facing",product_type:"Window",quantity:"3",width:"48",height:"60",
    frame:"White vinyl frame",glazing:"Double-pane Low-E tempered glass",unit_price:"749.00",
    notes:"Customer requests three energy-efficient windows and a patio door. Confirm rough-opening measurements, access restrictions and disposal before final quote.",
    date:"",scheduled_date:"",due_date:"",eta_date:"",target_date:"",requested_installation:"",
    amount:"1250.00",deposit:"1250.00",po:"PO-DEMO-1042",
    vendor:"Westhaven Sample Supply",time_window:"9:00 AM – 11:00 AM",
    assignee:"Alex Morgan — measurement technician",
    kind:"Deposit",category:"Deposit",status:"Draft",
    subject:"Patio door does not slide smoothly",
    detail:"Customer reports resistance when opening the patio door. Request an inspection and track follow-up.",
    reason:"Sample scenario: supplier revised shipment ETA by two business days; notify installation coordinator and homeowner.",
    rating:"3",feedback:"Sample feedback: installation was tidy; clearer arrival-time updates would improve the experience.",
    contact_permission:"no",reference:"DEMO-EXTERNAL-REF-1042",
    terms:"Illustrative 12-month workmanship warranty. Verify all actual coverage and exclusions against the signed agreement.",
    method:"Bank transfer",financing_type:"Customer pay",
    doc_type:"Measurements",
    project_type:"Window replacement",timeline:"Within 3 months",budget:"$10,000–$20,000",
    actual:"SAMPLE ONLY — no test was executed. Replace this with actual observed results before saving.",
    pre:"Start in the Admin demo role with a seeded customer job at the required prior stage.",
    steps:"1. Open the relevant job.\n2. Perform the permitted workflow action.\n3. Inspect the updated job stage, assigned task and event log.\n4. Attempt an out-of-order transition and verify rejection.",
    expected:"Only a valid stage transition succeeds; event history and assigned team update, while unauthorized or out-of-order transitions are rejected.",
    level:"Functional / E2E",
    title:"Sample — reject invalid job-stage transition",
    description:"SAMPLE DEFECT — not verified.\nSteps: Open a sample job and attempt a stage skip.\nExpected: HTTP validation error and unchanged state.\nActual: Record real observed behavior here before saving.",
    severity:"Medium",req:"",
    action:"",
    facebook:"https://www.facebook.com/frameops-example-not-real",
    x:"https://x.com/frameops_example",
    medium:"https://medium.com/@frameops-example",
    linkedin:"https://www.linkedin.com/company/frameops-example-not-real",
    youtube:"https://www.youtube.com/@frameops-example-not-real",
    instagram:"https://www.instagram.com/frameops_example_not_real",
    tiktok:"https://www.tiktok.com/@frameops_example_not_real",
    "ops-guide-input":"What should the Front Desk do after a new lead is submitted?",
    "job-search":"F-",
    "st-search":"sliding"
  };
  const FORM_TYPES=new Set([
    "action-form","ops-form","sim-form","st-quote-form","social-settings-form",
    "manual-form","custom-form","defect-form","ops-guide-form"
  ]);
  const SINGLE_INPUTS=["job-search","st-search"];
  const SKIP_TYPES=new Set(["hidden","submit","button","reset","file","image","color"]);
  const containsInteractive = form => [...form.querySelectorAll("input,select,textarea")]
    .some(c=>isEditable(c));
  const isEditable = c => !c.disabled && !c.readOnly && !SKIP_TYPES.has((c.type||"").toLowerCase());
  function addDays(count){
    const date=new Date();date.setHours(12,0,0,0);date.setDate(date.getDate()+count);
    return date.getFullYear()+"-"+String(date.getMonth()+1).padStart(2,"0")+"-"+String(date.getDate()).padStart(2,"0");
  }
  function dayFor(el,key){
    const days=key==="due_date"?21:key==="target_date"?5:key==="eta_date"?10:key==="requested_installation"?30:key==="scheduled_date"?7:14;
    let proposed=addDays(days);
    if(el.min&&el.min>proposed)proposed=el.min;
    if(el.max&&el.max<proposed)proposed=el.max;
    return proposed;
  }
  function keyFor(el){
    return (el.name||el.id||"").trim().toLowerCase().replace(/^fld-/,"");
  }
  function contextFor(form){return form.dataset.mode||form.dataset.opsKind||form.id||"";}
  function readableLabel(el){
    const wrapper=el.closest("label,.form-field,.bs-platform");
    const label=el.labels?.[0]||wrapper?.querySelector("label,.bs-name,.ops-field>span")||null;
    return (label?.textContent||el.getAttribute("aria-label")||el.name||el.id||"Input").replace(/\s+/g," ").replace(/\s*\*$/,"").trim().slice(0,80);
  }
  function selectValue(el,key,kind){
    const enabled=[...el.options].filter(o=>!o.disabled&&o.value!==""&&o.value!==undefined);
    if(!enabled.length)return null;
    const choose=value=>enabled.find(o=>o.value===String(value)||o.textContent.trim()===String(value));
    const chooseContains=text=>enabled.find(o=>o.textContent.toLowerCase().includes(text.toLowerCase()));
    if(key==="job_id"){
      // Preserve the selected customer / stage: do not redirect a record to another job.
      return el.value||enabled[0].value;
    }
    if(key==="status"){
      const choices={
        invoiceStatus:"Draft",ticketStatus:"Open",appointmentStatus:"Delayed",
        finance_update:"Pending",insurance_update:"Pending",permit_update:"Pending",
        sim:"", "manual-form":"Blocked",review:"Invited"
      };
      const value=choices[kind]||"Draft";
      return (choose(value)||enabled[0]).value;
    }
    if(key==="category"&&kind==="ticket")return (choose("Installation concern")||enabled[0]).value;
    if(key==="category"&&kind==="invoice")return (choose("Deposit")||enabled[0]).value;
    if(key==="severity")return (choose("Medium")||enabled[0]).value;
    if(key==="rating")return (choose("3")||enabled[0]).value;
    if(key==="priority")return (choose("Normal")||enabled[0]).value;
    if(key==="assigned_sales")return (choose("Jordan Lee")||enabled[0]).value;
    if(key==="lead_source")return (choose("Website")||enabled[0]).value;
    if(key==="contact_permission")return (choose("no")||enabled[0]).value;
    if(key==="req"||key==="caseId")return el.value||enabled[0].value;
    if(key==="kind"&&kind==="appointment")return el.value||enabled[0].value;
    if(key==="rating"&&kind==="sim-form")return (choose("4")||enabled[0]).value;
    if(key==="project_type")return (chooseContains("window")||enabled[0]).value;
    if(key==="requested_installation")return (chooseContains("replac")||enabled[0]).value;
    if(key==="timeline")return (chooseContains("3 month")||enabled[0]).value;
    if(key==="budget")return (chooseContains("10,000")||enabled[0]).value;
    const example=EXAMPLES[key];
    return (example&&choose(example)||enabled[0]).value;
  }
  function example(el,kind){
    const key=keyFor(el),type=(el.type||el.tagName).toLowerCase();
    if(type==="file")return null;
    if(type==="date")return dayFor(el,key);
    if(type==="datetime-local")return dayFor(el,key)+"T09:00";
    if(type==="time")return "09:00";
    if(type==="checkbox")return key.endsWith("-enabled")?true:false;
    if(type==="radio")return null;
    if(el.tagName==="SELECT")return selectValue(el,key,kind);
    if(key==="notes"){
      if(kind==="complete_measurement")return "Verified: 3 living-room openings at 48 × 60 inches and 1 patio door at 72 × 80 inches. Check trim clearance and exterior access.";
      if(kind==="installation_complete")return "Installed 3 windows and 1 patio door. Verified operation, weather seals and cleanup; no open punch-list items.";
      if(kind==="qa_passed")return "QA walkthrough: verified smooth operation, locking, caulking, trim, glass condition and homeowner orientation.";
      if(kind==="service_request")return "Customer reports the patio door sticks in the lower track; schedule warranty inspection.";
      if(kind==="note")return "Sample internal update: measurements verified and proposal review assigned to Sales.";
      if(kind==="invoice")return "Illustrative deposit invoice for a fictional job; no payment has been collected.";
      if(kind==="manual-form")return "SAMPLE ONLY — Chromium desktop; no independent test evidence was collected. Replace before reporting.";
      return EXAMPLES.notes;
    }
    if(key==="amount"){
      if(kind==="send_proposal")return "12480.00";
      if(kind==="record_payment")return "1250.00";
      if(kind==="invoice")return "1250.00";
      return EXAMPLES.amount;
    }
    if(key==="title"&&kind==="defect-form")return "Sample — stage transition unexpectedly allowed";
    if(key==="status"&&kind==="manual-form")return "Blocked";
    if(key==="reason"&&kind==="sim-form")return "Sample reason: the installation team needs two additional business days after the supplier schedule change.";
    if(key==="notes"&&kind==="manual-form")return "SAMPLE ONLY — Chromium desktop, isolated demo data. No actual execution evidence attached.";
    if(key==="feedback"&&kind==="feedback")return "Sample only — request clear arrival time updates after installation.";
    if(key==="action")return null;
    if(key==="email"||type==="email")return EXAMPLE_EMAIL;
    if(key==="phone"||type==="tel")return EXAMPLE_PHONE;
    if(type==="url")return EXAMPLES[key]||"https://example.com/fictional-business";
    if(type==="number"){
      const examples={quantity:"3",width:"48",height:"60",unit_price:"749",amount:"1250",deposit:"1250"};
      const val=examples[key]||"1";
      return el.min&&Number(el.min)>Number(val)?String(el.min):val;
    }
    if(type==="search")return EXAMPLES[key]||"window";
    return EXAMPLES[key]||("Example "+readableLabel(el).toLowerCase());
  }
  function describe(el,kind){
    if((el.type||"").toLowerCase()==="file")return "Choose a local sample file manually (browsers do not allow auto-filling uploads).";
    const key=keyFor(el),v=example(el,kind);
    if(v===null||v===undefined)return null;
    if(el.type==="checkbox")return "Example: "+(v?"enabled":"disabled");
    if(el.type==="password")return null;
    if(el.tagName==="SELECT"){
      const option=[...el.options].find(o=>o.value===String(v));
      return "Example: "+(option?.textContent.trim()||String(v));
    }
    if(typeof v==="string"&&v.length>110)return "Example: "+v.slice(0,106)+"…";
    return "Example: "+String(v);
  }
  function setValue(el,value){
    if(value===null||value===undefined)return false;
    const t=(el.type||"").toLowerCase();
    if(t==="checkbox"){el.checked=Boolean(value);}
    else if(t==="radio"){return false;}
    else{
      const descriptor=Object.getOwnPropertyDescriptor(el.tagName==="TEXTAREA"?HTMLTextAreaElement.prototype:el.tagName==="SELECT"?HTMLSelectElement.prototype:HTMLInputElement.prototype,"value");
      if(descriptor?.set)descriptor.set.call(el,String(value));
      else el.value=String(value);
    }
    el.dispatchEvent(new Event("input",{bubbles:true}));
    el.dispatchEvent(new Event("change",{bubbles:true}));
    return true;
  }
  function buttonFor(form){
    const b=document.createElement("button");
    b.type="button";b.className="sample-load-button";
    b.textContent="Load Test Data";
    b.setAttribute("aria-label","Load fictional example values into this form");
    b.dataset.sampleLoad="1";
    return b;
  }
  function decorate(form){
    if(form.dataset.samplesReady==="1"||!FORM_TYPES.has(form.id)||!containsInteractive(form))return;
    // The real sign-in form is intentionally excluded: fictional credentials cannot authenticate.
    form.dataset.samplesReady="1";
    const kind=contextFor(form);
    const toolbar=document.createElement("div");
    toolbar.className="sample-load-toolbar";
    const button=buttonFor(form);
    const msg=document.createElement("span");
    msg.className="sample-load-copy";msg.textContent="Fictional examples · review before saving";
    const feedback=document.createElement("span");
    feedback.className="sample-load-feedback";
    feedback.setAttribute("role","status");feedback.setAttribute("aria-live","polite");
    toolbar.append(button,msg,feedback);
    if(form.id==="ops-guide-form"){
      // Keep the tiny chat input/send layout intact.
      form.parentElement.insertBefore(toolbar,form);
      toolbar.classList.add("sample-load-chat-toolbar");
    }else{
      const footer=form.querySelector(".modal-actions,.st-form-actions,.sim-form-actions,.bs-actions");
      const heading=form.querySelector(":scope > h3");
      if(footer)form.insertBefore(toolbar,footer);
      else if(heading)heading.after(toolbar);
      else form.prepend(toolbar);
    }
    for(const el of form.querySelectorAll("input,select,textarea")){
      if(!isEditable(el)||el.type==="hidden"||el.type==="password")continue;
      const hint=describe(el,kind);
      if(!hint)continue;
      if((el.type==="text"||el.type==="email"||el.type==="tel"||el.type==="number"||el.type==="search"||el.type==="url"||el.tagName==="TEXTAREA")&&(!el.placeholder||el.placeholder==="Enter details")){
        const e=example(el,kind);
        if(typeof e==="string"&&e.length<=120)el.placeholder=e;
      }
      if(el.type==="file"){el.title=hint;continue;}
      if(el.type==="date"||el.tagName==="SELECT")el.title=hint;
      if(el.id==="ops-guide-input")continue;
      // Show sample beneath the field even when the control lacks native placeholder support.
      const wrapper=el.closest(".form-field,.ops-field,.bs-platform,label");
      if(!wrapper)continue;
      const note=document.createElement("small");note.className="sample-field-hint";note.textContent=hint;
      // Avoid changing labels or their control associations: hints are non-interactive.
      if(wrapper.classList.contains("bs-platform"))el.insertAdjacentElement("afterend",note);
      else wrapper.append(note);
    }
    button.addEventListener("click",()=>{
      let count=0,files=0;
      // Work on snapshot: a consumer might re-render when it receives a change event.
      const fields=[...form.querySelectorAll("input,select,textarea")].filter(isEditable);
      for(const el of fields){
        if(el.type==="file"){files++;continue;}
        if(!el.isConnected)continue;
        if(setValue(el,example(el,kind)))count++;
      }
      feedback.textContent=count+" sample "+(count===1?"field":"fields")+" filled"+(files?"; select "+files+" file manually":"")+". Not submitted.";
    });
  }
  function decorateSingle(id){
    const el=document.getElementById(id);
    if(!el||el.dataset.samplesSingle==="1"||el.closest("form")||!isEditable(el))return;
    el.dataset.samplesSingle="1";
    const parent=el.parentElement;if(!parent)return;
    const toolbar=document.createElement("div");toolbar.className="sample-load-toolbar sample-load-single";
    const b=document.createElement("button");b.type="button";b.className="sample-load-button";b.textContent="Load Test Data";
    const msg=document.createElement("span");msg.className="sample-load-feedback";msg.setAttribute("role","status");msg.setAttribute("aria-live","polite");
    toolbar.append(b,msg);
    parent.insertAdjacentElement("afterend",toolbar);
    el.title="Example: "+example(el,"");
    b.addEventListener("click",()=>{setValue(el,example(el,""));msg.textContent="Sample search entered.";});
  }
  let pending=false;
  function scan(){
    pending=false;
    document.querySelectorAll("form[id]").forEach(decorate);
    SINGLE_INPUTS.forEach(decorateSingle);
  }
  function schedule(){
    if(pending)return;
    pending=true;
    queueMicrotask(scan);
  }
  function init(){
    scan();
    new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();
