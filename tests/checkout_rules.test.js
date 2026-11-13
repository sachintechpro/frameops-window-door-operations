const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.join(__dirname,'..');
function load(){
 const records=new Map();
 const w={};
 const sandbox={window:w,Date,Math,Number,Object,Array,String,JSON,console,Intl,
   localStorage:{getItem:k=>records.get(k)||null,setItem:(k,v)=>records.set(k,String(v)),removeItem:k=>records.delete(k)},
   document:{readyState:'loading',addEventListener:()=>{}},setInterval:()=>{},
   FormData:class FormData{constructor(f){this.form=f;}entries(){return Object.entries(this.form)}},
   state:{view:'storefront',role:'Admin',data:{jobs:[]}}};
 vm.createContext(sandbox);
 for(const f of ['catalog.js','quick_checkout.js'])vm.runInContext(fs.readFileSync(path.join(root,'public',f),'utf8'),sandbox,{filename:f});
 return {q:w.FrameOpsCheckout,ctx:sandbox};
}
function future(n){const x=new Date();x.setDate(x.getDate()+n);return `${x.getFullYear()}-${String(x.getMonth()+1).padStart(2,'0')}-${String(x.getDate()).padStart(2,'0')}`;}
test('All fictional catalog products comply with supplier markup and 10% service even at maximum sales discount',()=>{
 const {q,ctx}=load();
 for(const p of ctx.window.FRAMEOPS_CATALOG.products){
   for(const qty of [1,3,40])for(const discount of [0,3,5]){
     const x=q.calculate([{sku:p.sku,quantity:qty}],discount);
     assert.ok(x.compliant,`${p.sku} ${qty} ${discount}`);
     assert.ok(x.total+0.01>=x.supplier*1.35*1.10,`${p.sku} below minimum`);
     assert.ok(x.before>=x.total);
     assert.ok(x.advance>=0.1*x.total-0.011);
   }
 }
 assert.throws(()=>q.calculate([{sku:'CV-210',quantity:1}],5.01));
 assert.throws(()=>q.calculate([{sku:'CV-210',quantity:0}],0));
 assert.throws(()=>q.calculate([{sku:'FAKE',quantity:1}],0));
});
test('Negotiated discount requires a sales/admin role and never exceeds 5%',()=>{
 const {q,ctx}=load();
 ctx.state.view='quote-operations';ctx.state.role='Front Desk';assert.equal(q.internalDiscount(3).ok,false);
 ctx.state.role='Sales';assert.equal(q.internalDiscount(5).ok,true);
 assert.equal(q.internalDiscount(6).ok,false);
});
test('Complete happy path writes advance, e-sign, appointments, customer messages and role-specific notifications',()=>{
 const {q,ctx}=load();
 const f={name:'Alex Example',signature:'Alex Example',email:'alex@example.com',phone:'555-010-0123',address:'10 Fictional Court',consent:'on',measureDate:future(3),measureTime:'09:00',installDate:future(20),installTime:'08:00',depositPct:'10',method:'Demo Visa •••• 4242',projectType:'Replacement'};
 assert.equal(q.submit(f).ok,false);
 const key='frameops-v24-checkout';
 const s=q.read();s.cart.push({sku:'CV-210',quantity:3});ctx.localStorage.setItem(key,JSON.stringify(s));
 const bad=q.submit({...f,signature:'Not the same'});assert.equal(bad.ok,false);
 const badContact=q.submit({...f,email:'some@realmail.com'});assert.equal(badContact.ok,false);
 const good=q.submit(f);assert.equal(good.ok,true);
 const o=q.read().orders[0];
 assert.equal(o.sign.name,f.name);assert.equal(o.measure.date,f.measureDate);assert.equal(o.install.date,f.installDate);
 assert.equal(o.payment.paid,o.payment.advance);
 assert.ok(o.payment.advance>=o.quote.total*.10-.01);
 assert.ok(o.notifications.some(x=>x.role==='Measurement Tech'));
 assert.ok(o.notifications.some(x=>x.role==='Admin'));
 assert.ok(o.notifications.some(x=>x.role==='Homeowner'));
 assert.ok(o.messages.some(x=>x.channel==='SMS preview'));
 assert.ok(o.messages.some(x=>x.channel==='Email preview'));
 assert.ok(o.documents.includes('Invoice'));
 assert.equal(q.orderAction('mark_installed').ok,false);
 assert.equal(q.orderAction('confirm_measurement').ok,true);
});
test('Reschedules impact installation, cancellations suppress reminders, rebook restores schedule',()=>{
 const {q,ctx}=load();const s=q.read();s.cart=[{sku:'CV-210',quantity:1}];ctx.localStorage.setItem('frameops-v24-checkout',JSON.stringify(s));
 const good=q.submit({name:'Test Example',signature:'Test Example',email:'test@example.com',phone:'555-010-0123',address:'1 Example Drive',consent:'on',measureDate:future(3),measureTime:'09:00',installDate:future(20),installTime:'08:00',depositPct:'10',method:'Demo Visa •••• 4242',projectType:'Retrofit'});assert.ok(good.ok);
 const oldInstall=q.read().orders[0].install.date;
 assert.ok(q.orderAction('reschedule_measurement',{date:future(19),time:'09:00'}).ok);
 const o=q.read().orders[0];assert.notEqual(o.install.date,oldInstall);
 assert.ok(o.notifications.some(x=>x.role==='Installation Manager'&&x.title.includes('Installation target moved')));
 assert.ok(q.orderAction('cancel_installation',{reason:'Customer requested pause'}).ok);
 assert.equal(q.read().orders[0].install.status,'Cancelled');
 assert.equal(q.reminderPreview(1).ok,true);
 assert.ok(q.orderAction('reschedule_installation',{date:future(34),time:'08:00'}).ok);
 assert.equal(q.read().orders[0].install.status,'Rescheduled · awaiting confirmation');
});
