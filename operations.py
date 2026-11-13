"""FrameOps operational extensions for the fictional-data showcase.

Scheduling, invoices, service tickets, alerts, satisfaction, and guided help.
NOT a production identity, payment, or messaging system. Role selection is simulated.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from html import escape
from urllib.parse import urlparse


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def day(delta=0):
    return (datetime.now(timezone.utc).date() + timedelta(days=delta)).isoformat()


def rows(con, query, args=()):
    return [dict(r) for r in con.execute(query, args).fetchall()]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def ensure_date(value, label='Date'):
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValueError(f'{label} must be YYYY-MM-DD')
    return parsed.isoformat()


def notify(con, job_id, title, detail, roles=('Admin', 'Front Desk', 'Customer Service')):
    t = stamp()
    for role in roles:
        con.execute('INSERT INTO notifications(job_id,role,title,detail,created_at) VALUES(?,?,?,?,?)',
                    (job_id, role, title, detail[:300], t))
    con.execute('INSERT INTO events(job_id,label,detail,actor,created_at) VALUES(?,?,?,?,?)',
                (job_id, title, detail[:500], 'Operations', t))


def ensure_job(con, job_id):
    j = con.execute('SELECT id,homeowner,stage,quote_total FROM jobs WHERE id=?', (job_id,)).fetchone()
    check(j is not None, 'Job not found')
    return dict(j)


def role_check(actor, allowed):
    check(actor == 'Admin' or actor in allowed, 'Select the responsible operational role to perform this action')


def initialize_ops(con):
    con.executescript('''
        CREATE TABLE IF NOT EXISTS appointments (
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
          kind TEXT NOT NULL, scheduled_date TEXT NOT NULL, time_window TEXT DEFAULT 'To confirm',
          owner_role TEXT NOT NULL, assignee TEXT DEFAULT 'Unassigned', status TEXT NOT NULL DEFAULT 'Scheduled',
          eta_date TEXT DEFAULT '', delay_reason TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES jobs(id));
        CREATE TABLE IF NOT EXISTS invoices (
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, number TEXT NOT NULL UNIQUE,
          category TEXT NOT NULL, amount REAL NOT NULL, due_date TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Draft', notes TEXT DEFAULT '', created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(id));
        CREATE TABLE IF NOT EXISTS service_tickets (
          id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, category TEXT NOT NULL,
          subject TEXT NOT NULL, detail TEXT NOT NULL, assignee TEXT NOT NULL DEFAULT 'Customer Service',
          status TEXT NOT NULL DEFAULT 'Open', target_date TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES jobs(id));
        CREATE TABLE IF NOT EXISTS satisfaction (
          job_id TEXT PRIMARY KEY, rating INTEGER, feedback TEXT DEFAULT '',
          contact_permission INTEGER DEFAULT 0, review_status TEXT NOT NULL DEFAULT 'Not requested',
          updated_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(id));
        CREATE INDEX IF NOT EXISTS idx_appointments_due ON appointments(scheduled_date,status);
        CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date,status);
        CREATE INDEX IF NOT EXISTS idx_tickets_due ON service_tickets(target_date,status);
    ''')
    if not con.execute('SELECT 1 FROM appointments LIMIT 1').fetchone():
        demos = [
          ('F-1002', 'Measurement', day(1), '9 AM – 11 AM', 'Measurement Tech', 'Site technician', 'Scheduled', day(1)),
          ('F-1005', 'Vendor delivery', day(5), 'Delivery window pending', 'Vendor', 'Pacific Window Supply', 'Scheduled', day(5)),
          ('F-1006', 'Installation', day(3), '8 AM – 4 PM', 'Installation Manager', 'Installation crew A', 'Scheduled', day(3)),
          ('F-1007', 'QA inspection', day(1), '1 PM – 3 PM', 'Service Tech', 'Quality inspector', 'Scheduled', day(1)),
          ('F-1008', 'Warranty service', day(4), '10 AM – 12 PM', 'Customer Service', 'Service coordinator', 'Scheduled', day(4)),
        ]
        for j,k,d,window,role,assignee,status,eta in demos:
            con.execute('INSERT INTO appointments(job_id,kind,scheduled_date,time_window,owner_role,assignee,status,eta_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (j,k,d,window,role,assignee,status,eta,stamp(),stamp()))
    if not con.execute('SELECT 1 FROM invoices LIMIT 1').fetchone():
        for j,num,category,amount,due,status in [
          ('F-1004','INV-DEMO-1004','Deposit',2280,day(2),'Sent'),
          ('F-1007','INV-DEMO-1007','Final balance',6600,day(3),'Draft'),
          ('F-1008','INV-DEMO-1008','Final payment',3700,day(-14),'Paid — manually verified')]:
            con.execute('INSERT INTO invoices(job_id,number,category,amount,due_date,status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                        (j,num,category,amount,due,status,'Fictional sample invoice, no payment processing',stamp(),stamp()))
    if not con.execute('SELECT 1 FROM service_tickets LIMIT 1').fetchone():
        con.execute('INSERT INTO service_tickets(job_id,category,subject,detail,assignee,status,target_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    ('F-1008','Warranty','Door handle adjustment','Check handle alignment after installation','Service Tech','Open',day(4),stamp(),stamp()))


def sync_milestone(con, job_id, action, fields, actor):
    """Persist a scheduled milestone from the legacy end-to-end workflow."""
    if action not in ('schedule_measurement', 'schedule_install'):
        return
    kind = 'Measurement' if action == 'schedule_measurement' else 'Installation'
    date_value = ensure_date(fields.get('date'), 'Appointment date')
    role = 'Measurement Tech' if kind == 'Measurement' else 'Installation Manager'
    con.execute('INSERT INTO appointments(job_id,kind,scheduled_date,time_window,owner_role,assignee,status,eta_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (job_id,kind,date_value,'Time to confirm',role,'Unassigned','Scheduled',date_value,stamp(),stamp()))


def dashboard(con):
    jobs=rows(con, 'SELECT * FROM jobs ORDER BY updated_at DESC')
    tasks=rows(con, "SELECT t.*,j.homeowner FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.status='Open' ORDER BY t.due_date ASC LIMIT 250")
    appointments=rows(con, 'SELECT a.*,j.homeowner,j.stage FROM appointments a JOIN jobs j ON j.id=a.job_id ORDER BY a.scheduled_date ASC,a.id DESC')
    invoices=rows(con, 'SELECT i.*,j.homeowner,j.stage FROM invoices i JOIN jobs j ON j.id=i.job_id ORDER BY i.due_date ASC,i.id DESC')
    tickets=rows(con, 'SELECT s.*,j.homeowner,j.stage FROM service_tickets s JOIN jobs j ON j.id=s.job_id ORDER BY s.target_date ASC,s.id DESC')
    satisfaction=rows(con, 'SELECT f.*,j.homeowner FROM satisfaction f JOIN jobs j ON j.id=f.job_id ORDER BY f.updated_at DESC')
    docs=rows(con, 'SELECT d.id,d.job_id,d.doc_type,d.name,d.created_at,d.added_by,j.homeowner FROM documents d JOIN jobs j ON j.id=d.job_id ORDER BY d.id DESC LIMIT 120')
    payments=rows(con, 'SELECT job_id,SUM(amount) AS total FROM payments GROUP BY job_id')
    alerts=[]
    def alert(job_id,kind,title,description,priority='warning'):
        alerts.append({'job_id':job_id,'kind':kind,'title':title,'description':description,'priority':priority})
    today=day()
    for a in appointments:
        if a['status']=='Delayed': alert(a['job_id'],'Delay',f"{a['kind']} delayed",a['delay_reason'] or 'Revised ETA required','critical')
        elif a['status']=='Scheduled' and a['scheduled_date']<today: alert(a['job_id'],'Schedule',f"{a['kind']} overdue",f"Scheduled {a['scheduled_date']}; confirmation required",'critical')
        elif a['status']=='Scheduled' and a['scheduled_date']<=day(2): alert(a['job_id'],'Appointment',f"Upcoming {a['kind'].lower()}",f"{a['scheduled_date']} · {a['time_window']}",'info')
    for i in invoices:
        if i['status'] not in ('Paid — manually verified','Void') and i['due_date'] < today:
            alert(i['job_id'],'Invoice','Invoice overdue',f"{i['number']} · due {i['due_date']}",'warning')
    for t in tickets:
        if t['status'] not in ('Resolved','Cancelled') and t['target_date']<today:
            alert(t['job_id'],'Customer service','Service response overdue',t['subject'],'critical')
    for j in jobs:
        if j['stage']=='Contract Signed': alert(j['id'],'Financing','Funding approval pending',f"{j['homeowner']} · verify deposit or financing",'warning')
        if j['stage']=='Materials Ordered' and j['vendor_eta'] and j['vendor_eta'] < today:
            alert(j['id'],'Vendor ETA','Supplier ETA missed',f"PO {j['vendor_order']} · ETA {j['vendor_eta']}",'critical')
        if j['stage']=='Closed' and not any(f['job_id']==j['id'] for f in satisfaction):
            alert(j['id'],'Customer success','Satisfaction follow-up needed',f"Request optional feedback from {j['homeowner']}",'info')
    alerts.sort(key=lambda a: {'critical':0,'warning':1,'info':2}.get(a['priority'],3))
    return {'jobs':jobs,'tasks':tasks,'appointments':appointments,'invoices':invoices,'tickets':tickets,
            'satisfaction':satisfaction,'documents':docs,'payments':payments,'alerts':alerts[:60],
            'review_url':validated_review_url(), 'generated_at':stamp()}


def job_operations(con, job_id):
    ensure_job(con,job_id)
    return {'appointments':rows(con,'SELECT * FROM appointments WHERE job_id=? ORDER BY scheduled_date DESC',(job_id,)),
            'invoices':rows(con,'SELECT * FROM invoices WHERE job_id=? ORDER BY id DESC',(job_id,)),
            'tickets':rows(con,'SELECT * FROM service_tickets WHERE job_id=? ORDER BY id DESC',(job_id,)),
            'satisfaction':rows(con,'SELECT * FROM satisfaction WHERE job_id=?',(job_id,)),
            'review_url':validated_review_url()}


def validated_review_url():
    link = os.getenv('GOOGLE_REVIEW_URL','').strip()
    try:
        p = urlparse(link)
        if p.scheme=='https' and p.hostname and (p.hostname.endswith('.google.com') or p.hostname=='google.com' or p.hostname=='g.page'):
            return link
    except ValueError:
        pass
    return ''


def guide(question, context='',role='Admin'):
    q=' '.join(str(question).lower().split())[:400]
    knowledge = [
      (('storefront','customer inquiry','new lead','intake','lead'), 'New customer inquiry', 'Open Storefront to submit a fictional inquiry, then Front Desk or Leads to qualify it. The system assigns a follow-up task automatically.', 'storefront'),
      (('measure','measurement','size','dimensions'), 'Measurements', 'Qualify the lead, book a site visit, select Measurement Tech, enter verified opening dimensions and site constraints, then mark measurements complete. The next handoff goes to Sales.', 'measurements'),
      (('financ','deposit','funding','approval','loan'), 'Financing and deposits', 'After the contract is recorded, Accounting can record an externally received deposit, or Financing can record a mock lender decision. Procurement is gated until funding clears. This app never processes money.', 'financing'),
      (('vendor','supplier','order','material','eta'), 'Vendor coordination', 'Once funding is cleared, the Installation Manager places the vendor PO. Use Vendor to monitor ETA, delivery delays, and received materials; notify downstream teams when dates change.', 'vendors'),
      (('install','crew','permit','insurance','schedule'), 'Installation scheduling', 'Materials must be received, and applicable insurance and permits approved. Schedule the crew, record installation completion, then conduct the quality walkthrough.', 'installation'),
      (('invoice','document','receipt','billing'), 'Documents and invoices', 'Open Documents & Invoices to locate job records, create a draft invoice, set a due date, mark it sent, or record external payment confirmation. Public file uploads are disabled.', 'documents'),
      (('warrant','aftercare','repair','service request'), 'Warranty aftercare', 'After full payment and QA, close the job and activate warranty terms. The homeowner or Customer Service can open a tracked ticket; a technician resolves it.', 'warranty'),
      (('review','google','satisfaction','rating','feedback'), 'Satisfaction and Google reviews', 'After job closeout, open Customer Service to record voluntary satisfaction feedback. An optional Google review invitation can be tracked, but customers submit their own reviews on Google. Configure the verified business review URL before sending a link.', 'customer-service'),
      (('delay','late','overdue','notification','banner','alert'), 'Delays and alerts', 'Open Installation, Measurements, or Vendor and update the appointment to Delayed with a reason and revised ETA. The dashboard then shows an urgent banner and in-app notices.', 'overview'),
      (('admin','dashboard','overview','metrics','track'), 'Operations command center', 'Open Dashboard to see pipeline, overdue items, upcoming appointments, blocked funding, vendor ETAs, customer service and satisfaction follow-up. Select any job to act on it.', 'overview'),
    ]
    for words,title,answer,view in knowledge:
        if any(k in q for k in words):
            return {'title':title,'answer':answer,'view':view,'suggestions':['Show my next steps','Where are delays?','How do I close a job?']}
    return {'title':'FrameOps guide','answer':f"Working as {role}: start at Dashboard for the full pipeline. Use the left navigation for each department. Open a job to see its current stage, the responsible team, and the next gated action. Ask about leads, measurements, financing, vendors, installation, invoices, delays, warranty or Google reviews.",
            'view':'overview','suggestions':['How do I process a lead?','What happens after installation?','How are invoices managed?']}


def mutation(con, path, data):
    actor=str(data.get('actor','Admin'))[:60]
    now=stamp()
    if path=='/api/ops/appointments':
        role_check(actor,('Front Desk','Sales','Measurement Tech','Installation Manager','Service Tech','Customer Service','Vendor'))
        job_id=str(data.get('job_id','')); ensure_job(con,job_id)
        kind=str(data.get('kind','')).strip()[:80]
        check(kind in ('Measurement','Vendor delivery','Installation','QA inspection','Warranty service','Follow-up call'),'Choose an appointment type')
        scheduled=ensure_date(data.get('scheduled_date'))
        window=str(data.get('time_window','To confirm')).strip()[:80]
        owner=str(data.get('owner_role') or actor)[:80]
        assignee=str(data.get('assignee','Unassigned')).strip()[:100]
        con.execute('INSERT INTO appointments(job_id,kind,scheduled_date,time_window,owner_role,assignee,status,eta_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (job_id,kind,scheduled,window,owner,assignee,'Scheduled',scheduled,now,now))
        ident=con.execute('SELECT last_insert_rowid()').fetchone()[0]
        notify(con,job_id,'Appointment scheduled',f'{kind}: {scheduled} · {window}',('Admin','Front Desk','Customer Service',owner))
        return {'ok':True,'id':ident,'message':'Appointment scheduled and teams notified'}
    m=re.fullmatch(r'/api/ops/appointments/(\d+)/status',path)
    if m:
        role_check(actor,('Front Desk','Measurement Tech','Vendor','Installation Manager','Service Tech','Customer Service'))
        x=con.execute('SELECT * FROM appointments WHERE id=?',(m.group(1),)).fetchone();check(x,'Appointment not found')
        status=str(data.get('status',''));check(status in ('Scheduled','Delayed','Completed','Cancelled'),'Invalid status')
        reason=str(data.get('reason','')).strip()[:500]
        check(status!='Delayed' or len(reason)>=5,'A delay needs a reason (at least five characters)')
        eta=ensure_date(data.get('eta_date') or x['eta_date'] or x['scheduled_date'],'Revised ETA')
        con.execute('UPDATE appointments SET status=?,delay_reason=?,eta_date=?,updated_at=? WHERE id=?',
                    (status,reason if status=='Delayed' else '',eta,now,m.group(1)))
        notify(con,x['job_id'],f'{x["kind"]} {status.lower()}',f'{reason or status} · ETA {eta}',('Admin','Front Desk','Customer Service',x['owner_role']))
        return {'ok':True,'message':'Appointment status and ETA updated'}
    if path=='/api/ops/invoices':
        role_check(actor,('Accountant','Financing'))
        job_id=str(data.get('job_id','')); j=ensure_job(con,job_id)
        category=str(data.get('category','')).strip()[:70];check(category in ('Deposit','Progress','Final balance','Warranty service','Other'),'Select invoice category')
        try: amount=round(float(data.get('amount')),2)
        except (ValueError,TypeError): raise ValueError('Invoice amount is required')
        check(0<amount<=1000000,'Invoice amount must be between $0.01 and $1,000,000')
        due=ensure_date(data.get('due_date'),'Invoice due date')
        notes=str(data.get('notes','')).strip()[:500]
        number='FO-INV-'+datetime.now(timezone.utc).strftime('%y%m%d')+'-'+str(con.execute('SELECT COALESCE(MAX(id),0)+1 FROM invoices').fetchone()[0]).zfill(4)
        con.execute('INSERT INTO invoices(job_id,number,category,amount,due_date,status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (job_id,number,category,amount,due,'Draft',notes,now,now))
        notify(con,job_id,'Invoice drafted',f'{number} · ${amount:,.2f} · due {due}',('Admin','Accountant'))
        return {'ok':True,'message':f'Draft invoice {number} created'}
    m=re.fullmatch(r'/api/ops/invoices/(\d+)/status',path)
    if m:
        role_check(actor,('Accountant',))
        x=con.execute('SELECT * FROM invoices WHERE id=?',(m.group(1),)).fetchone();check(x,'Invoice not found')
        status=str(data.get('status',''));check(status in ('Draft','Sent','Paid — manually verified','Void'),'Invalid invoice status')
        con.execute('UPDATE invoices SET status=?,updated_at=? WHERE id=?',(status,now,m.group(1)))
        notify(con,x['job_id'],'Invoice status updated',f'{x["number"]}: {status}',('Admin','Accountant','Customer Service'))
        return {'ok':True,'message':f'Invoice marked {status.lower()}'}
    if path=='/api/ops/tickets':
        role_check(actor,('Customer Service','Homeowner','Service Tech','Front Desk','Warranty Coordinator'))
        job_id=str(data.get('job_id',''));ensure_job(con,job_id)
        category=str(data.get('category','')).strip();check(category in ('Warranty','Installation concern','Scheduling','Billing question','Other'),'Invalid ticket category')
        subject=str(data.get('subject','')).strip()[:140];detail=str(data.get('detail','')).strip()[:1200]
        check(len(subject)>=4 and len(detail)>=8,'Subject and description are required')
        due=ensure_date(data.get('target_date') or day(2),'Response target')
        con.execute('INSERT INTO service_tickets(job_id,category,subject,detail,assignee,status,target_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (job_id,category,subject,detail,'Customer Service','Open',due,now,now))
        notify(con,job_id,'Customer service case opened',f'{category}: {subject} · target {due}',('Admin','Customer Service','Service Tech','Warranty Coordinator'))
        return {'ok':True,'message':'Customer service ticket opened'}
    m=re.fullmatch(r'/api/ops/tickets/(\d+)/status',path)
    if m:
        role_check(actor,('Customer Service','Service Tech','Warranty Coordinator'))
        x=con.execute('SELECT * FROM service_tickets WHERE id=?',(m.group(1),)).fetchone();check(x,'Ticket not found')
        status=str(data.get('status',''));check(status in ('Open','In progress','Awaiting customer','Resolved','Cancelled'),'Invalid ticket status')
        con.execute('UPDATE service_tickets SET status=?,updated_at=? WHERE id=?',(status,now,m.group(1)))
        notify(con,x['job_id'],'Customer service case updated',f'{x["subject"]} · {status}',('Admin','Customer Service','Warranty Coordinator'))
        return {'ok':True,'message':'Ticket status updated'}
    if path=='/api/ops/feedback':
        role_check(actor,('Homeowner','Customer Service','Warranty Coordinator'))
        job_id=str(data.get('job_id',''));j=ensure_job(con,job_id)
        check(j['stage']=='Closed','Request customer satisfaction feedback after job closeout')
        try:rating=int(data.get('rating'))
        except (ValueError,TypeError):raise ValueError('Select a satisfaction rating')
        check(1<=rating<=5,'Rating must be between 1 and 5')
        notes=str(data.get('feedback','')).strip()[:1000]
        consent=1 if data.get('contact_permission') in (True,'yes','1') else 0
        con.execute('INSERT INTO satisfaction(job_id,rating,feedback,contact_permission,review_status,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET rating=excluded.rating, feedback=excluded.feedback,contact_permission=excluded.contact_permission,updated_at=excluded.updated_at',
                    (job_id,rating,notes,consent,'Not requested',now))
        notify(con,job_id,'Customer satisfaction recorded',f'{rating}/5 · {notes[:150] or "No additional comment"}',('Admin','Customer Service','Warranty Coordinator'))
        if rating<=3:
            con.execute('INSERT INTO service_tickets(job_id,category,subject,detail,assignee,status,target_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                        (job_id,'Installation concern','Satisfaction recovery follow-up',notes or 'Follow up on customer satisfaction','Customer Service','Open',day(1),now,now))
        return {'ok':True,'message':'Satisfaction feedback recorded; follow-up created when needed'}
    if path=='/api/ops/review':
        role_check(actor,('Customer Service','Warranty Coordinator','Homeowner'))
        job_id=str(data.get('job_id',''));j=ensure_job(con,job_id)
        check(j['stage']=='Closed','Review follow-up is available after closeout')
        status=str(data.get('status',''))
        check(status in ('Invited','Opened Google review page','Customer-reported submitted','Declined'),'Invalid review status')
        con.execute("INSERT INTO satisfaction(job_id,review_status,updated_at) VALUES(?,?,?) ON CONFLICT(job_id) DO UPDATE SET review_status=excluded.review_status,updated_at=excluded.updated_at",(job_id,status,now))
        notify(con,job_id,'Optional Google review follow-up',f'Review invitation status: {status}',('Admin','Customer Service'))
        return {'ok':True,'message':'Optional review-invitation status recorded (not a verified Google review)'}
    raise ValueError('Unsupported operations endpoint')


def printable_invoice(con, invoice_id):
    r=con.execute('SELECT i.*,j.homeowner,j.address,j.service_type FROM invoices i JOIN jobs j ON j.id=i.job_id WHERE i.id=?',(invoice_id,)).fetchone()
    if not r:return None
    x=dict(r)
    def e(key):return escape(str(x.get(key) or ''))
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e('number')}</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:760px;margin:44px auto;padding:24px;color:#24324b}}h1{{color:#345bdf}}.muted{{color:#667387}}.item{{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid #ddd;padding:16px 0}}.total{{font-size:24px;font-weight:700}}.notice{{margin-top:28px;padding:15px;background:#fff5df;border-radius:8px;font-size:13px}}@media print{{button{{display:none}}}}</style></head><body><h1>FrameOps · Invoice</h1><p class="muted">Fictional operations demonstration — not a payment request</p><h2>{e('number')}</h2><p><strong>Bill to:</strong> {e('homeowner')}<br>{e('address')}</p><div class="item"><span>Job</span><strong>{e('job_id')}</strong></div><div class="item"><span>Description</span><strong>{e('category')} · {e('service_type')}</strong></div><div class="item"><span>Due date</span><strong>{e('due_date')}</strong></div><div class="item"><span>Status</span><strong>{e('status')}</strong></div><div class="item total"><span>Amount</span><span>${float(x['amount']):,.2f}</span></div><p>{e('notes')}</p><div class="notice">This is a sample invoice for demonstration. Payments are recorded externally and are not processed by FrameOps.</div><button onclick="window.print()">Print invoice</button></body></html>'''
