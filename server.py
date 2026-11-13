#!/usr/bin/env python3
"""FrameOps operations server and fictional portfolio demo."""
from __future__ import annotations
import base64
import json
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from uuid import uuid4
from accounts import DEMO, SESSION_SECONDS, initialize_accounts, identity, session_key, sign_in
from operations import initialize_ops, dashboard as ops_dashboard, job_operations, mutation as ops_mutation, guide as ops_guide, sync_milestone, printable_invoice

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DB_PATH = Path(os.getenv("DB_PATH", str(ROOT / "data" / "frameops.db")))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT / "data" / "uploads")))
PUBLIC_DEMO = DEMO
ROLES = ["Admin", "Front Desk", "Sales", "Measurement Tech", "Accountant", "Vendor", "Installation Manager", "Service Tech", "Homeowner", "Financing", "Customer Service", "Warranty Coordinator"]
STAGES = ["New Lead", "Qualified", "Measurement Scheduled", "Measurements Complete", "Proposal Sent", "Proposal Approved", "Contract Signed", "Funding Cleared", "Materials Ordered", "Materials Received", "Installation Scheduled", "Installed", "QA Passed", "Closed"]
STAGE_IDX = {s:i for i,s in enumerate(STAGES)}
ALLOWED_ACTIONS = {
    "add_opening": ["Sales", "Measurement Tech"],
    "qualify": ["Front Desk", "Sales"],
    "schedule_measurement": ["Front Desk", "Sales"],
    "complete_measurement": ["Measurement Tech"],
    "send_proposal": ["Sales"],
    "accept_proposal": ["Sales", "Homeowner"],
    "sign_contract": ["Sales", "Homeowner"],
    "finance_update": ["Accountant", "Financing"],
    "record_payment": ["Accountant"],
    "clear_funding": ["Accountant"],
    "place_order": ["Installation Manager"],
    "materials_received": ["Vendor", "Installation Manager"],
    "schedule_install": ["Installation Manager"],
    "installation_complete": ["Service Tech", "Installation Manager"],
    "qa_passed": ["Service Tech", "Installation Manager"],
    "close_job": ["Accountant"],
    "insurance_update": ["Installation Manager", "Accountant"],
    "permit_update": ["Installation Manager"],
    "service_request": ["Homeowner", "Front Desk", "Service Tech", "Customer Service", "Warranty Coordinator"],
    "note": ROLES,
    "set_priority": ["Front Desk", "Sales"],
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def date_offset(days=0):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    return con


def rowdict(row):
    return dict(row) if row else None


def initialize():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, homeowner TEXT NOT NULL, phone TEXT, email TEXT, address TEXT NOT NULL,
            lead_source TEXT, service_type TEXT, priority TEXT DEFAULT 'Normal', stage TEXT DEFAULT 'New Lead',
            assigned_sales TEXT DEFAULT 'Unassigned', lead_notes TEXT DEFAULT '', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, quote_total REAL DEFAULT 0, deposit_required REAL DEFAULT 0,
            financing_status TEXT DEFAULT 'Not requested', financing_type TEXT DEFAULT 'Customer pay',
            contractor_insurance TEXT DEFAULT 'Not required', permit_status TEXT DEFAULT 'Not required',
            vendor_name TEXT DEFAULT '', vendor_order TEXT DEFAULT '', vendor_eta TEXT DEFAULT '',
            materials_received INTEGER DEFAULT 0, install_date TEXT DEFAULT '', install_notes TEXT DEFAULT '',
            measurement_notes TEXT DEFAULT '', contract_status TEXT DEFAULT 'Not sent',
            qa_status TEXT DEFAULT 'Not started', warranty_status TEXT DEFAULT 'Not active',
            warranty_terms TEXT DEFAULT '', close_date TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS openings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
            room TEXT NOT NULL, product_type TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 1,
            width REAL NOT NULL, height REAL NOT NULL, frame TEXT DEFAULT '', glazing TEXT DEFAULT '',
            unit_price REAL NOT NULL DEFAULT 0, notes TEXT DEFAULT '', created_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, role TEXT NOT NULL,
            title TEXT NOT NULL, detail TEXT DEFAULT '', status TEXT DEFAULT 'Open',
            code TEXT NOT NULL, due_date TEXT, created_at TEXT NOT NULL, completed_at TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, label TEXT NOT NULL,
            detail TEXT DEFAULT '', actor TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, role TEXT NOT NULL,
            title TEXT NOT NULL, detail TEXT DEFAULT '', created_at TEXT NOT NULL, read_at TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, amount REAL NOT NULL,
            kind TEXT, method TEXT, reference TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, doc_type TEXT NOT NULL,
            name TEXT NOT NULL, stored_name TEXT, created_at TEXT NOT NULL, added_by TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_role ON tasks(role,status);
        CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_notify_role ON notifications(role,read_at);
        """)
        n = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        if not n:
            seed(con)
        initialize_ops(con)
        initialize_accounts(con, ROLES)


def task(con, job_id, role, title, code, detail="", days=2):
    existing=con.execute("SELECT id FROM tasks WHERE job_id=? AND code=?",(job_id,code)).fetchone()
    if existing: return
    con.execute("INSERT INTO tasks(job_id,role,title,detail,code,due_date,created_at) VALUES(?,?,?,?,?,?,?)",
                (job_id,role,title,detail,code,date_offset(days),now()))


def finish_task(con, job_id, code):
    con.execute("UPDATE tasks SET status='Done', completed_at=? WHERE job_id=? AND code=? AND status='Open'",(now(),job_id,code))


def event(con, job_id, label, detail, actor, roles=()):
    con.execute("INSERT INTO events(job_id,label,detail,actor,created_at) VALUES(?,?,?,?,?)",(job_id,label,detail,actor,now()))
    for role in set(roles):
        if role in ROLES:
            con.execute("INSERT INTO notifications(job_id,role,title,detail,created_at) VALUES(?,?,?,?,?)",(job_id,role,label,detail,now()))


def move(con, job_id, stage):
    previous = STAGES[STAGE_IDX[stage] - 1]
    updated = con.execute("UPDATE jobs SET stage=?,updated_at=? WHERE id=? AND stage=?",
                          (stage, now(), job_id, previous))
    require(updated.rowcount == 1, f"Complete {previous} before advancing to {stage}")


def paid_total(con, job_id):
    return float(con.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE job_id=?",(job_id,)).fetchone()[0])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_active_appointment(con, job_id, kind):
    appointment = con.execute('SELECT status FROM appointments WHERE job_id=? AND kind=? ORDER BY id DESC LIMIT 1',
                              (job_id, kind)).fetchone()
    require(not appointment or appointment['status'] not in ('Cancelled', 'Delayed'),
            f'Reconfirm the {kind.lower()} appointment before completion')


def do_action(con, job_id, action, payload, actor):
    job = rowdict(con.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone())
    require(job is not None,"Job not found")
    require(actor in ROLES,"Unknown role")
    require(action in ALLOWED_ACTIONS,"Unknown action")
    require(actor == "Admin" or actor in ALLOWED_ACTIONS[action], f"{actor} cannot perform this action. Switch to the responsible role.")
    stage=job['stage']; detail=''; label=''
    def at(s): return stage==s
    if action == 'add_opening':
        require(STAGE_IDX[stage] <= STAGE_IDX['Measurements Complete'],
                'Proposal has already been issued. Use a formal change-order workflow to modify signed or priced scope.')
        room=str(payload.get('room','')).strip()
        product=str(payload.get('product_type','Window'))
        require(room, 'Room / location is required')
        require(product in ('Window','Exterior door','Patio door','Other'), 'Choose a supported opening type')
        qty=int(payload.get('quantity') or 1)
        width=float(payload.get('width') or 0); height=float(payload.get('height') or 0)
        price=float(payload.get('unit_price') or 0)
        require(1<=qty<=100, 'Quantity must be 1–100')
        require(1<=width<=300 and 1<=height<=300,'Opening width and height must be entered in inches')
        require(0<=price<=1000000,'Invalid estimated unit price')
        frame=str(payload.get('frame',''))[:120]; glazing=str(payload.get('glazing',''))[:120]
        notes=str(payload.get('notes',''))[:500]
        con.execute('INSERT INTO openings(job_id,room,product_type,quantity,width,height,frame,glazing,unit_price,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (job_id,room,product,qty,width,height,frame,glazing,round(price,2),notes,now()))
        label='Opening specification added'; detail=f'{qty} × {product} · {room} · {width:g} × {height:g} in'; roles=['Sales','Measurement Tech']
    elif action == 'qualify':
        require(at('New Lead'),"Lead must be new to qualify")
        move(con,job_id,'Qualified'); finish_task(con,job_id,'qualify')
        task(con,job_id,'Sales','Schedule an on-site measurement','schedule_measurement','Contact homeowner and confirm measurement window',1)
        label='Lead qualified'; detail='Homeowner needs confirmed; sales handoff created'; roles=['Sales']
    elif action == 'schedule_measurement':
        require(at('Qualified'),"Qualify lead before scheduling measurement")
        dt=str(payload.get('date','')).strip(); require(dt,"Measurement date is required")
        con.execute("UPDATE jobs SET measurement_notes=? WHERE id=?",(f"Visit scheduled: {dt}",job_id))
        move(con,job_id,'Measurement Scheduled'); finish_task(con,job_id,'schedule_measurement')
        task(con,job_id,'Measurement Tech','Complete field measurements','complete_measurement',f'On-site appointment: {dt}',1)
        label='Measurement visit scheduled'; detail=f'Measurement technician assigned for {dt}'; roles=['Measurement Tech','Front Desk']
    elif action == 'complete_measurement':
        require(at('Measurement Scheduled'),"Schedule measurement first")
        require_active_appointment(con,job_id,'Measurement')
        notes=str(payload.get('notes','')).strip(); require(len(notes)>=5,'Enter measurements, opening count, or field notes')
        con.execute("UPDATE jobs SET measurement_notes=? WHERE id=?",(notes,job_id))
        move(con,job_id,'Measurements Complete'); finish_task(con,job_id,'complete_measurement')
        task(con,job_id,'Sales','Prepare and send homeowner proposal','send_proposal','Use confirmed opening sizes, product selection and vendor pricing',1)
        label='Measurements completed'; detail=notes[:160]; roles=['Sales','Installation Manager']
    elif action == 'send_proposal':
        require(at('Measurements Complete'),"Final measurements must be recorded before a proposal")
        total=float(payload.get('amount') or 0); require(0 < total < 10000000,"Enter a valid proposal amount")
        con.execute("UPDATE jobs SET quote_total=? WHERE id=?",(round(total,2),job_id))
        move(con,job_id,'Proposal Sent'); finish_task(con,job_id,'send_proposal')
        task(con,job_id,'Sales','Follow up on proposal approval','accept_proposal','Confirm homeowner has reviewed price and scope',2)
        label='Proposal sent'; detail=f'Proposed project total ${total:,.2f}'; roles=['Front Desk','Homeowner']
    elif action == 'accept_proposal':
        require(at('Proposal Sent'),"Send a proposal before approval")
        move(con,job_id,'Proposal Approved'); finish_task(con,job_id,'accept_proposal')
        task(con,job_id,'Sales','Prepare contract and obtain signature','sign_contract','Confirm scope, exclusions, warranty and payment terms',1)
        label='Proposal approved'; detail='Homeowner acceptance recorded in this prototype'; roles=['Sales','Accountant','Homeowner']
    elif action == 'sign_contract':
        require(at('Proposal Approved'),"Proposal must be approved before contracting")
        deposit=float(payload.get('deposit') or 0); require(0<=deposit<=float(job['quote_total']),"Deposit must be between $0 and proposal total")
        financing=str(payload.get('financing_type','Customer pay'))
        require(financing in ('Customer pay','Financing requested'),"Invalid payment plan")
        status='Pending' if financing=='Financing requested' else 'Not requested'
        con.execute("UPDATE jobs SET deposit_required=?,financing_type=?,financing_status=?,contract_status='Recorded as signed (demo)' WHERE id=?",
                    (round(deposit,2),financing,status,job_id))
        con.execute("INSERT INTO documents(job_id,doc_type,name,created_at,added_by) VALUES(?,?,?,?,?)",
                    (job_id,'Contract','Contract acceptance record (demo only)',now(),actor))
        move(con,job_id,'Contract Signed'); finish_task(con,job_id,'sign_contract')
        task(con,job_id,'Accountant','Verify deposit or financing','funding','Confirm cleared funds or financing approval before releasing procurement',1)
        label='Contract accepted'; detail=f'Contract acceptance recorded; deposit requirement ${deposit:,.2f}; {financing.lower()}'; roles=['Accountant','Installation Manager','Homeowner']
        if financing == 'Financing requested':
            roles.append('Financing')
    elif action == 'clear_funding':
        require(at('Contract Signed'), 'Funding can only be cleared after signing')
        require(job['financing_type'] == 'Customer pay' and job['deposit_required'] == 0,
                'Record the required deposit or financing approval')
        move(con, job_id, 'Funding Cleared')
        finish_task(con, job_id, 'funding')
        task(con, job_id, 'Installation Manager', 'Place purchase order with vendor', 'place_order',
             'No deposit required under the signed contract', 1)
        label = 'Funding cleared'; detail = 'No deposit required'; roles = ['Installation Manager']
    elif action == 'finance_update':
        require(at('Contract Signed'), 'Financing decisions can be recorded while funding is pending')
        require(job['financing_type']=='Financing requested',"This job is not configured for financing")
        status=str(payload.get('status',''))
        require(status in ('Pending','Approved','Declined'),"Choose financing status")
        if status == job['financing_status']:
            return {'ok':True,'message':'Financing status already recorded'}
        con.execute("UPDATE jobs SET financing_status=? WHERE id=?",(status,job_id))
        label='Financing updated'; detail=f'Financing status: {status} (external decision recorded manually)'; roles=['Sales','Installation Manager','Homeowner']
        if status=='Approved' and stage=='Contract Signed':
            move(con,job_id,'Funding Cleared'); finish_task(con,job_id,'funding')
            task(con,job_id,'Installation Manager','Place purchase order with vendor','place_order','Funding approval recorded; verify lender conditions',1)
    elif action == 'record_payment':
        require(STAGE_IDX['Contract Signed'] <= STAGE_IDX[stage] < STAGE_IDX['Closed'], 'Payments require a signed and open job')
        amount=float(payload.get('amount') or 0); require(0 < amount < 10000000,"Enter a valid positive payment amount")
        kind=str(payload.get('kind','Payment')); method=str(payload.get('method','Manual record'))
        reference=str(payload.get('reference','')).strip()
        if reference:
            require(not con.execute('SELECT 1 FROM payments WHERE job_id=? AND reference=?',
                                    (job_id, reference)).fetchone(), 'Payment reference already recorded')
        require(paid_total(con,job_id)+amount <= float(job['quote_total'])+0.009,"Payment would exceed contract total")
        con.execute("INSERT INTO payments(job_id,amount,kind,method,reference,created_at) VALUES(?,?,?,?,?,?)",
                    (job_id,round(amount,2),kind,method,reference,now()))
        label='Payment recorded'; detail=f'${amount:,.2f} {kind.lower()} via {method}; reference {reference or "not entered"} (manual ledger)'; roles=['Sales','Installation Manager','Homeowner']
        if (at('Contract Signed') and job['deposit_required'] > 0
                and paid_total(con,job_id)+0.009>=float(job['deposit_required'])):
            move(con,job_id,'Funding Cleared'); finish_task(con,job_id,'funding')
            task(con,job_id,'Installation Manager','Place purchase order with vendor','place_order','Deposit threshold satisfied',1)
        if paid_total(con,job_id)+0.009 >=float(job['quote_total']):
            finish_task(con, job_id, 'final_balance')
            if at('QA Passed'):
                roles.append('Accountant')
                task(con,job_id,'Accountant','Close out job and issue warranty','close_job','Final payment and QA are complete',1)
    elif action == 'place_order':
        require(stage=='Funding Cleared',"Verify deposit or financing before placing vendor order")
        vendor=str(payload.get('vendor','')).strip(); require(vendor,'Vendor name is required')
        po=str(payload.get('po','')).strip(); require(po,'Purchase order reference is required')
        eta=str(payload.get('eta','')).strip(); require(eta,'Expected delivery date is required')
        con.execute("UPDATE jobs SET vendor_name=?,vendor_order=?,vendor_eta=? WHERE id=?",(vendor,po,eta,job_id))
        move(con,job_id,'Materials Ordered'); finish_task(con,job_id,'place_order')
        task(con,job_id,'Vendor','Confirm material delivery / receipt','materials_received',f'PO {po}; ETA {eta}',3)
        label='Vendor purchase order placed'; detail=f'{vendor} · PO {po} · ETA {eta}'; roles=['Vendor','Installation Manager','Sales']
    elif action=='materials_received':
        require(at('Materials Ordered'),"Materials must be ordered before receipt")
        require_active_appointment(con,job_id,'Vendor delivery')
        con.execute("UPDATE jobs SET materials_received=1 WHERE id=?",(job_id,))
        move(con,job_id,'Materials Received'); finish_task(con,job_id,'materials_received')
        task(con,job_id,'Installation Manager','Schedule installation crew','schedule_install','Confirm availability, permits, insurance and homeowner access',1)
        label='Materials received'; detail='Order receipt confirmed; installation scheduling unblocked'; roles=['Installation Manager','Front Desk','Homeowner']
    elif action=='schedule_install':
        require(at('Materials Received'),"Confirm material receipt before scheduling")
        if job['permit_status'] not in ('Not required','Approved'):
            raise ValueError('Permit is pending. Update the permit to Approved before scheduling.')
        if job['contractor_insurance'] not in ('Not required','Verified'):
            raise ValueError('Insurance verification is pending. Verify before scheduling.')
        dt=str(payload.get('date','')).strip(); require(dt,'Installation date is required')
        con.execute("UPDATE jobs SET install_date=? WHERE id=?",(dt,job_id))
        move(con,job_id,'Installation Scheduled'); finish_task(con,job_id,'schedule_install')
        task(con,job_id,'Service Tech','Complete installation and field report','installation_complete',f'Scheduled for {dt}',1)
        label='Installation scheduled'; detail=f'Installation planned for {dt}'; roles=['Service Tech','Front Desk','Sales','Homeowner']
    elif action=='installation_complete':
        require(at('Installation Scheduled'),"Installation must be scheduled first")
        require_active_appointment(con,job_id,'Installation')
        notes=str(payload.get('notes','')).strip(); require(len(notes)>=4,'Add installation completion details')
        con.execute("UPDATE jobs SET install_notes=?,qa_status='Pending inspection' WHERE id=?",(notes,job_id))
        move(con,job_id,'Installed'); finish_task(con,job_id,'installation_complete')
        task(con,job_id,'Service Tech','Complete QA walkthrough and punch list','qa_passed','Check operations, trim, seal, cleanup, photos and homeowner sign-off',1)
        if float(job['quote_total'])-paid_total(con,job_id)>0.009:
            task(con,job_id,'Accountant','Collect outstanding final balance','final_balance','Confirm homeowner invoice and payment receipt',2)
        label='Installation completed'; detail=notes[:160]; roles=['Service Tech','Accountant','Installation Manager','Homeowner']
    elif action=='qa_passed':
        require(at('Installed'),"Complete installation before QA inspection")
        require_active_appointment(con,job_id,'QA inspection')
        notes=str(payload.get('notes','')).strip(); require(len(notes)>=4,'Add field inspection notes')
        con.execute("UPDATE jobs SET qa_status='Passed' WHERE id=?",(job_id,))
        move(con,job_id,'QA Passed'); finish_task(con,job_id,'qa_passed')
        if float(job['quote_total']) - paid_total(con, job_id) <= 0.009:
            task(con,job_id,'Accountant','Close out job and issue warranty','close_job','Final payment and QA are complete',1)
        label='Quality walkthrough passed'; detail=notes[:160]; roles=['Accountant','Sales','Homeowner']
    elif action=='close_job':
        require(at('QA Passed'),"Quality walkthrough must pass before closeout")
        balance=round(float(job['quote_total'])-paid_total(con,job_id),2)
        require(balance<=0.009,f'Outstanding balance ${balance:,.2f} must be recorded first')
        terms=str(payload.get('terms','')).strip(); require(len(terms)>=6,'Specify warranty terms from the signed agreement')
        con.execute("UPDATE jobs SET warranty_status='Active',warranty_terms=?,close_date=? WHERE id=?",(terms,date_offset(),job_id))
        move(con,job_id,'Closed'); finish_task(con,job_id,'close_job'); finish_task(con,job_id,'final_balance')
        con.execute("INSERT INTO documents(job_id,doc_type,name,created_at,added_by) VALUES(?,?,?,?,?)",
                    (job_id,'Warranty','Warranty handover record (demo only)',now(),actor))
        label='Job closed; warranty activated'; detail=terms[:160]; roles=['Homeowner','Front Desk','Service Tech','Sales','Warranty Coordinator','Customer Service']
    elif action=='insurance_update':
        status=str(payload.get('status',''))
        require(status in ('Not required','Pending','Verified'),"Choose insurance verification status")
        con.execute("UPDATE jobs SET contractor_insurance=? WHERE id=?",(status,job_id))
        label='Insurance requirement updated'; detail=f'Contractor / subcontractor COI: {status}'; roles=['Installation Manager','Sales']
    elif action=='permit_update':
        status=str(payload.get('status',''))
        require(status in ('Not required','Pending','Approved'),"Choose permit status")
        con.execute("UPDATE jobs SET permit_status=? WHERE id=?",(status,job_id))
        label='Permit updated'; detail=f'Permit readiness: {status}'; roles=['Installation Manager','Front Desk']
    elif action=='service_request':
        require(at('Closed'),"Warranty service requests are available for closed jobs")
        notes=str(payload.get('notes','')).strip(); require(len(notes)>=8,'Describe the warranty or service issue')
        return ops_mutation(con, '/api/ops/tickets', {'actor':actor,'job_id':job_id,
                            'category':'Warranty','subject':'Warranty service request','detail':notes}, do_action)
    elif action=='note':
        notes=str(payload.get('notes','')).strip(); require(len(notes)>=3,'Enter a note')
        label='Team note added'; detail=notes[:240]; roles=[x for x in ROLES if x not in ('Homeowner','Vendor')]
    elif action=='set_priority':
        p=str(payload.get('priority','')); require(p in ('Normal','High','Urgent'),"Unknown priority")
        con.execute("UPDATE jobs SET priority=? WHERE id=?",(p,job_id))
        label='Priority updated'; detail=f'Priority: {p}'; roles=['Sales','Front Desk']
    event(con,job_id,label,detail,actor,roles)
    if action in ('complete_measurement', 'installation_complete', 'qa_passed', 'materials_received'):
        kind = {'complete_measurement': 'Measurement', 'installation_complete': 'Installation',
                'qa_passed': 'QA inspection', 'materials_received': 'Vendor delivery'}[action]
        con.execute("UPDATE appointments SET status='Completed',updated_at=? WHERE job_id=? AND kind=?",
                    (now(), job_id, kind))
    sync_milestone(con,job_id,action,payload,actor)
    con.execute('UPDATE jobs SET updated_at=? WHERE id=?',(now(),job_id))
    return {'ok':True,'message':label}


def seed(con):
    demo=[
    ('F-1001','Sarah Mitchell','(555) 010-1001','sarah@example.com','101 Sample Way, West Hills, CA','Website','4 windows','High','New Lead','Jordan Lee',0,0,'Not requested','Customer pay','Not required','Not required','','','','','', '', 'Not sent','Not started','Not active','', ''),
    ('F-1002', 'David Chen', '(555) 010-1002', 'david@example.com', '202 Example Court, Chatsworth, CA', 'Referral', 'Sliding patio door', 'Normal', 'Measurement Scheduled', 'Avery Kim', 0, 0, 'Not requested', 'Customer pay', 'Not required', 'Not required', '', '', '', '', '', 'Visit scheduled: ' + date_offset(1), 'Not sent', 'Not started', 'Not active', '', ''),
    ('F-1003', 'Elena Rivera', '(555) 010-1003', 'elena@example.com', '303 Test Street, Calabasas, CA', 'Google Search', '8 replacement windows', 'High', 'Measurements Complete', 'Jordan Lee', 0, 0, 'Not requested', 'Customer pay', 'Not required', 'Not required', '', '', '', '', '', '8 openings measured; two upstairs; tempered glass at stair landing.', 'Not sent', 'Not started', 'Not active', '', ''),
    ('F-1004', 'Marcus Johnson', '(555) 010-1004', 'marcus@example.com', '404 Placeholder Drive, Woodland Hills, CA', 'Showroom', 'Entry door + sidelights', 'Normal', 'Contract Signed', 'Avery Kim', 7600, 2280, 'Not requested', 'Customer pay', 'Not required', 'Pending', '', '', '', '', '', '', 'Recorded as signed (demo)', 'Not started', 'Not active', '', ''),
    ('F-1005', 'Priya Nair', '(555) 010-1005', 'priya@example.com', '505 Sample Lane, Simi Valley, CA', 'Referral', '12 windows + 2 doors', 'High', 'Materials Ordered', 'Jordan Lee', 18250, 5500, 'Approved', 'Financing requested', 'Verified', 'Approved', 'Pacific Window Supply', 'PO-2408', date_offset(5), '', '', '12 openings measured; 2 exterior doors.', 'Recorded as signed (demo)', 'Not started', 'Not active', '', ''),
    ('F-1006','Robert Davis','(555) 010-1006','robert@example.com','606 Example Road, Thousand Oaks, CA','Website','3 patio doors','Normal','Installation Scheduled','Avery Kim',11900,3500,'Not requested','Customer pay','Verified','Approved','West Coast Doors','PO-2381',date_offset(-1),date_offset(3),'3-door replacement and haul-away.','Final measurements confirmed.','Recorded as signed (demo)','Not started','Not active','',''),
    ('F-1007','Amanda Patel','(555) 010-1007','amanda@example.com','707 Demo Avenue, Northridge, CA','Partner','6 windows','Urgent','Installed','Jordan Lee',9400,2800,'Not requested','Customer pay','Not required','Not required','Pacific Window Supply','PO-2290',date_offset(-8),date_offset(-1),'Install complete; caulk and cleanup finished.','6 windows measured and verified.','Recorded as signed (demo)','Pending inspection','Not active','',''),
    ('F-1008','Olivia Brooks','(555) 010-1008','olivia@example.com','808 Sample Court, Tarzana, CA','Referral','Front entry door','Normal','Closed','Avery Kim',5200,1500,'Not requested','Customer pay','Verified','Not required','West Coast Doors','PO-2120',date_offset(-22),date_offset(-16),'Installed and signed off.','Entry door measurement verified.','Recorded as signed (demo)','Passed','Active','Product and labor coverage per signed agreement; exclusions apply.',date_offset(-14)),
    ]
    fields=['id','homeowner','phone','email','address','lead_source','service_type','priority','stage','assigned_sales','quote_total','deposit_required','financing_status','financing_type','contractor_insurance','permit_status','vendor_name','vendor_order','vendor_eta','install_date','install_notes','measurement_notes','contract_status','qa_status','warranty_status','warranty_terms','close_date']
    for n,vals in enumerate(demo):
        assert len(vals)==len(fields), f'Invalid demo job tuple length: {vals[0]}'
        data=dict(zip(fields,vals)); data['lead_notes']='This is a fictional example job for evaluating the workflow.'
        data['created_at']=(datetime.now(timezone.utc)-timedelta(days=18-n*2)).isoformat(timespec='seconds')
        data['updated_at']=(datetime.now(timezone.utc)-timedelta(days=7-n)).isoformat(timespec='seconds')
        k=list(data.keys()); q=','.join('?' for _ in k)
        con.execute(f"INSERT INTO jobs({','.join(k)}) VALUES({q})",list(data.values()))
        event(con,data['id'],'Lead created',f"{data['service_type']} · {data['lead_source']}",'Front Desk',[])
    task(con,'F-1001','Front Desk','Qualify homeowner inquiry','qualify','Confirm address, scope, urgency and best contact time',0)
    task(con,'F-1002','Measurement Tech','Measure patio door opening','complete_measurement','Visit scheduled '+date_offset(1),1)
    task(con,'F-1003','Sales','Prepare and send proposal','send_proposal','Include glass types and disposal costs',0)
    task(con,'F-1004','Accountant','Collect and verify deposit','funding','$2,280 deposit required before procurement',0)
    task(con,'F-1005','Vendor','Confirm order status and materials receipt','materials_received','PO-2408 expected '+date_offset(5),3)
    task(con,'F-1006','Service Tech','Complete installation report','installation_complete','Crew appointment '+date_offset(3),3)
    task(con,'F-1007','Service Tech','Complete walkthrough and punch list','qa_passed','Confirm homeowner sign-off',0)
    task(con,'F-1007','Accountant','Collect final balance','final_balance','Open balance $6,600',2)
    task(con,'F-1008','Service Tech','Review warranty follow-up','service_seed','Check homeowner inquiry about handle adjustment',1)
    demo_openings=[
        ('F-1002','Family room','Patio door',1,72,80,'Vinyl','Low-E',0,'Sliding configuration'),
        ('F-1003','Living room','Window',3,36,48,'Vinyl','Low-E',980,'Retrofit'),
        ('F-1003','Bedrooms','Window',5,40,52,'Vinyl','Low-E',890,'Tempered glass at landing to confirm'),
        ('F-1004','Front entry','Exterior door',1,36,80,'Fiberglass','Clear',5600,'Two sidelights under separate quote'),
        ('F-1005','Living / bedrooms','Window',12,40,58,'Vinyl','Low-E',1050,'White frames'),
        ('F-1005','Exterior entry','Exterior door',2,36,80,'Fiberglass','Low-E',2400,'Supplier finish match'),
        ('F-1006','Rear patio','Patio door',3,72,80,'Aluminum','Low-E',3000,'Multi-panel patio doors'),
        ('F-1007','Bedrooms','Window',6,36,50,'Vinyl','Low-E',1250,'Installation complete'),
        ('F-1008','Front entry','Exterior door',1,38,82,'Fiberglass','Clear',5200,'Service request for handle')]
    for record in demo_openings:
        con.execute('INSERT INTO openings(job_id,room,product_type,quantity,width,height,frame,glazing,unit_price,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(*record,now()))
    for job_id,amount,kind in [('F-1005',5500,'Financing disbursement'),('F-1006',3500,'Deposit'),('F-1007',2800,'Deposit'),('F-1008',1500,'Deposit'),('F-1008',3700,'Final')]:
        con.execute('INSERT INTO payments(job_id,amount,kind,method,reference,created_at) VALUES(?,?,?,?,?,?)',
                    (job_id,amount,kind,'Manual record','SEED-DEMO',now()))
    for job_id, typ, name in [('F-1003','Measurements','Field measurement worksheet'),('F-1004','Contract','Contract acceptance record (demo)'),('F-1005','Purchase order','PO-2408 supplier order'),('F-1006','Permit','Local permit review record'),('F-1007','Photos','Installation photo checklist'),('F-1008','Warranty','Warranty handover record (demo)')]:
        con.execute('INSERT INTO documents(job_id,doc_type,name,created_at,added_by) VALUES(?,?,?,?,?)',(job_id,typ,name,now(),'Admin'))
    event(con,'F-1007','Installation completed','Awaiting final site walkthrough','Service Tech',['Accountant','Installation Manager'])
    event(con,'F-1005','Vendor order placed','PO-2408 · awaiting receipt','Installation Manager',['Vendor'])


def list_jobs(con):
    rows=con.execute('''SELECT j.*, COALESCE((SELECT SUM(amount) FROM payments p WHERE p.job_id=j.id),0) AS paid,
      (SELECT COUNT(*) FROM tasks t WHERE t.job_id=j.id AND t.status='Open') AS open_tasks
      FROM jobs j ORDER BY j.updated_at DESC''').fetchall()
    return [dict(x) for x in rows]


def job_detail(con,id):
    j=con.execute('SELECT * FROM jobs WHERE id=?',(id,)).fetchone()
    if not j:return None
    data=dict(j)
    data['paid']=paid_total(con,id)
    data['balance']=round(max(0,float(data['quote_total'])-data['paid']),2)
    data['tasks']=[dict(x) for x in con.execute('SELECT * FROM tasks WHERE job_id=? ORDER BY CASE status WHEN \'Open\' THEN 0 ELSE 1 END,due_date,id',(id,))]
    data['events']=[dict(x) for x in con.execute('SELECT * FROM events WHERE job_id=? ORDER BY id DESC LIMIT 60',(id,))]
    data['payments']=[dict(x) for x in con.execute('SELECT * FROM payments WHERE job_id=? ORDER BY id DESC',(id,))]
    data['documents']=[dict(x) for x in con.execute('SELECT id,job_id,doc_type,name,stored_name,created_at,added_by FROM documents WHERE job_id=? ORDER BY id DESC',(id,))]
    data['openings']=[dict(x) for x in con.execute('SELECT * FROM openings WHERE job_id=? ORDER BY id',(id,))]
    return data


def customer_job(job):
    return {key: job[key] for key in ('id','homeowner','stage','quote_total','paid',
            'service_type','address','install_date','warranty_status','warranty_terms')}


class Handler(BaseHTTPRequestHandler):
    server_version='FrameOpsDemo/1.0'
    def log_message(self, fmt,*args):
        if os.getenv('QUIET')!='1':super().log_message(fmt,*args)
    def headers_common(self,content_type='application/json',length=None):
        self.send_header('Content-Type',content_type)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        if length is not None:self.send_header('Content-Length',str(length))
    def send_json(self,obj,status=200,cookie=None):
        b=json.dumps(obj,ensure_ascii=False,default=str).encode()
        self.send_response(status); self.headers_common(length=len(b))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers(); self.wfile.write(b)
    def account(self):
        with db() as con:
            return identity(con, self.headers.get('Cookie', ''))
    def session_cookie(self, token='', max_age=0):
        secure = '; Secure' if os.getenv('RENDER') or os.getenv('FRAMEOPS_SECURE_COOKIE') == '1' else ''
        return f'frameops_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}{secure}'
    def payload(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>8000000: raise ValueError('Request too large (8 MB maximum)')
        return json.loads(self.rfile.read(size) or b'{}')
    def do_GET(self):
        p=unquote(urlparse(self.path).path)
        try:
            account = self.account() if p.startswith('/api/') and not PUBLIC_DEMO else None
            if p.startswith('/api/') and not PUBLIC_DEMO and not account:
                return self.send_json({'error':'Sign in to FrameOps'},401)
            if account and account['role'] == 'Homeowner' and p not in (
                '/api/bootstrap', '/api/jobs/' + account['job_id']
            ):
                return self.send_json({'error':'This view is unavailable for your account'},403)
            if p=='/api/ops/dashboard':
                with db() as con: payload = ops_dashboard(con)
                return self.send_json(payload)
            m=re.fullmatch(r'/api/ops/jobs/(F-\d+)',p)
            if m:
                with db() as con: data=job_operations(con,m.group(1))
                return self.send_json(data)
            m=re.fullmatch(r'/api/ops/invoices/(\d+)/print',p)
            if m:
                with db() as con: html=printable_invoice(con,m.group(1))
                if html is None:return self.send_json({'error':'Invoice not found'},404)
                payload=html.encode('utf-8')
                self.send_response(200);self.headers_common('text/html; charset=utf-8',len(payload));self.end_headers();self.wfile.write(payload);return
            if p=='/api/bootstrap':
                with db() as con:
                    jobs=list_jobs(con)
                    tasks=[dict(x) for x in con.execute("SELECT t.*,j.homeowner,j.address,j.stage FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.status='Open' ORDER BY t.due_date LIMIT 120")]
                    ns=[dict(x) for x in con.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 150')]
                    events=[dict(x) for x in con.execute('SELECT e.*,j.homeowner FROM events e JOIN jobs j ON j.id=e.job_id ORDER BY e.id DESC LIMIT 24')]
                    operations=ops_dashboard(con)
                role = account['role'] if account else 'Admin'
                if account and role != 'Admin':
                    ns = [n for n in ns if n['role'] == role]
                    tasks = [t for t in tasks if t['role'] == role]
                    operations['tasks'] = [t for t in operations['tasks'] if t['role'] == role]
                if account and role == 'Homeowner':
                    own = account['job_id']
                    jobs = [customer_job(j) for j in jobs if j['id'] == own]
                    tasks, events, operations = [], [], {}
                    ns = [n for n in ns if n['job_id'] == own]
                return self.send_json({'jobs':jobs,'tasks':tasks,'notifications':ns,'events':events,
                    'roles':ROLES if PUBLIC_DEMO else [role],'stages':STAGES,'demo':PUBLIC_DEMO,
                    'role':role,'homeownerId':account.get('job_id') if account else None,'operations':operations})
            m=re.fullmatch(r'/api/jobs/(F-\d+)',p)
            if m:
                with db() as con: j=job_detail(con,m.group(1))
                if j and account and account['role'] == 'Homeowner':
                    j = customer_job(j)
                return self.send_json(j) if j else self.send_json({'error':'Job not found'},404)
            m=re.fullmatch(r'/api/documents/(\d+)',p)
            if m:
                with db() as con:doc=con.execute('SELECT * FROM documents WHERE id=?',(m.group(1),)).fetchone()
                if not doc or not doc['stored_name']:
                    return self.send_json({'error':'Document record has no uploaded file'},404)
                f=UPLOAD_DIR / doc['stored_name']
                if not f.is_file():return self.send_json({'error':'File unavailable'},404)
                content=f.read_bytes()
                self.send_response(200)
                self.headers_common(mimetypes.guess_type(doc['name'])[0] or 'application/octet-stream',len(content))
                safe_name=re.sub('[^A-Za-z0-9_.-]','_',doc['name'])
                self.send_header('Content-Disposition',f'attachment; filename="{safe_name}"')
                self.end_headers();self.wfile.write(content);return
            if p=='/health':return self.send_json({'status':'ok'})
            if p=='/':p='/index.html'
            requested=(PUBLIC / p.lstrip('/')).resolve()
            if not requested.is_relative_to(PUBLIC.resolve()) or not requested.is_file():
                return self.send_json({'error':'Not found'},404)
            b=requested.read_bytes();typ=mimetypes.guess_type(requested.name)[0] or 'application/octet-stream'
            self.send_response(200);self.headers_common(typ,len(b));self.end_headers();self.wfile.write(b)
        except Exception as e:
            self.send_json({'error':str(e)},500)
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            data=self.payload()
            if p == '/api/session' and not PUBLIC_DEMO:
                with db() as con:
                    token = sign_in(con, str(data.get('username','')), str(data.get('password','')))
                if not token:
                    return self.send_json({'error':'Invalid username or password'},401)
                return self.send_json({'ok':True},cookie=self.session_cookie(token, SESSION_SECONDS))
            if p == '/api/session/logout' and not PUBLIC_DEMO:
                with db() as con:
                    con.execute('DELETE FROM sessions WHERE token_hash=?',
                                (session_key(self.headers.get('Cookie','')),))
                return self.send_json({'ok':True},cookie=self.session_cookie())
            account = self.account() if not PUBLIC_DEMO else None
            if not PUBLIC_DEMO and not account:
                return self.send_json({'error':'Sign in to FrameOps'},401)
            actor = account['role'] if account else str(data.get('actor','Front Desk'))
            if account and actor == 'Homeowner':
                own = account['job_id']
                allowed = (p == f'/api/jobs/{own}/action' or p == '/api/notifications/read'
                           or (p in ('/api/ops/tickets','/api/ops/feedback','/api/ops/review')
                               and data.get('job_id') == own))
                if not allowed:
                    return self.send_json({'error':'This action is unavailable for your account'},403)
            if p=='/api/ops/guide':
                return self.send_json(ops_guide(data.get('question',''),data.get('context',''),actor))
            if p.startswith('/api/ops/'):
                with db() as con:
                    con.execute('BEGIN IMMEDIATE')
                    result=ops_mutation(con,p,{**data,'actor':actor},do_action)
                return self.send_json(result,201 if p in ('/api/ops/appointments','/api/ops/invoices','/api/ops/tickets') else 200)
            if p=='/api/jobs':
                require(actor in ('Admin','Front Desk','Sales','Homeowner'), 'This role cannot create a lead')
                homeowner=str(data.get('homeowner','')).strip(); address=str(data.get('address','')).strip()
                require(homeowner and address,'Homeowner name and address are required')
                with db() as con:
                    con.execute('BEGIN IMMEDIATE')
                    if PUBLIC_DEMO:
                        n_jobs = con.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
                        require(n_jobs < 40, 'This shared public demo has reached its lead limit. Reset the demo to continue.')
                    n=int(con.execute('SELECT COALESCE(MAX(CAST(SUBSTR(id,3) AS INTEGER)),1000)+1 FROM jobs').fetchone()[0])
                    id=f'F-{n}'
                    con.execute('''INSERT INTO jobs(id,homeowner,phone,email,address,lead_source,service_type,priority,stage,assigned_sales,lead_notes,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (id,homeowner,str(data.get('phone',''))[:100],str(data.get('email',''))[:150],address,
                        str(data.get('lead_source','Website'))[:100],str(data.get('service_type','Windows / doors'))[:150],
                        str(data.get('priority','Normal')) if data.get('priority') in ('Normal','High','Urgent') else 'Normal',
                        'New Lead',str(data.get('assigned_sales','Unassigned'))[:100],str(data.get('notes',''))[:1500],now(),now()))
                    task(con,id,'Front Desk','Qualify homeowner inquiry','qualify','Confirm contact details, scope and appointment',0)
                    event(con,id,'New lead created',f"{data.get('service_type','Windows / doors')} · {data.get('lead_source','Website')}",actor,['Front Desk'])
                return self.send_json({'ok':True,'id':id},201)
            m=re.fullmatch(r'/api/jobs/(F-\d+)/action',p)
            if m:
                try:
                    with db() as con:
                        con.execute('BEGIN IMMEDIATE')
                        result=do_action(con,m.group(1),str(data.get('action','')),data.get('fields') or {},actor)
                    return self.send_json(result)
                except (ValueError,TypeError) as e:return self.send_json({'error':str(e)},400)
            m=re.fullmatch(r'/api/jobs/(F-\d+)/upload',p)
            if m:
                require(not PUBLIC_DEMO, 'File uploads are disabled in the public demo. Use fictional data only.')
                name=Path(str(data.get('name',''))).name[:140]
                doc_type=str(data.get('doc_type','Other'))[:80]
                require(actor in ('Admin','Sales','Front Desk','Accountant','Measurement Tech','Installation Manager','Service Tech','Warranty Coordinator'), 'This role cannot upload documents')
                require(bool(name),'File name required')
                contents=base64.b64decode(data.get('base64',''),validate=True)
                require(0<len(contents)<=4000000,'File must be 1 byte to 4 MB')
                require(Path(name).suffix.lower() in ('.pdf','.png','.jpg','.jpeg','.docx','.txt','.csv'), 'Allowed: PDF, PNG, JPG, DOCX, TXT or CSV')
                stored=uuid4().hex+Path(name).suffix.lower()
                with db() as con:
                    require(con.execute('SELECT 1 FROM jobs WHERE id=?',(m.group(1),)).fetchone() is not None,'Job not found')
                    (UPLOAD_DIR/stored).write_bytes(contents)
                    con.execute('INSERT INTO documents(job_id,doc_type,name,stored_name,created_at,added_by) VALUES(?,?,?,?,?,?)',
                                (m.group(1),doc_type,name,stored,now(),actor))
                    event(con,m.group(1),'Document uploaded',f'{doc_type}: {name}',actor,['Sales','Installation Manager','Accountant'])
                return self.send_json({'ok':True})
            if p=='/api/notifications/read':
                require(actor in ROLES,'Invalid role')
                with db() as con:
                    if actor=='Admin':con.execute('UPDATE notifications SET read_at=? WHERE read_at IS NULL',(now(),))
                    elif account and actor == 'Homeowner':
                        con.execute("UPDATE notifications SET read_at=? WHERE role=? AND job_id=? AND read_at IS NULL",
                                    (now(),actor,account['job_id']))
                    else:con.execute('UPDATE notifications SET read_at=? WHERE role=? AND read_at IS NULL',(now(),actor))
                return self.send_json({'ok':True})
            return self.send_json({'error':'Endpoint not found'},404)
        except (ValueError,TypeError,KeyError) as e:
            self.send_json({'error':str(e)},400)
        except Exception as e:
            self.send_json({'error':f'Unexpected server error: {str(e)}'},500)

if __name__=='__main__':
    initialize()
    port=int(os.getenv('PORT', '10000'))
    print(f'FrameOps ready: http://localhost:{port} | DB: {DB_PATH}')
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
