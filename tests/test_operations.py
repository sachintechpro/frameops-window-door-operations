"""End-to-end integration tests for FrameOps 2.0 operational workflows.

All data stays in a temporary SQLite database, with no external services or customers.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]


class OperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='frameops-ops-')
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
        env=dict(os.environ,PORT=str(cls.port),PUBLIC_DEMO='1',QUIET='1',
                 DB_PATH=str(Path(cls.temp.name)/'ops.db'),UPLOAD_DIR=str(Path(cls.temp.name)/'uploads'))
        cls.process=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        cls.base=f'http://127.0.0.1:{cls.port}'
        for _ in range(80):
            if cls.process.poll() is not None: raise RuntimeError(cls.process.stderr.read().decode())
            try:
                if urlopen(cls.base+'/health',timeout=1).status==200:break
            except (OSError,URLError):time.sleep(.05)
        else:raise RuntimeError('FrameOps test server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();cls.process.wait(timeout=5);cls.process.stderr.close();cls.temp.cleanup()

    def call(self,path,data=None):
        request=Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,
                        headers={'Content-Type':'application/json'} if data is not None else {})
        try:
            with urlopen(request,timeout=3) as r:
                content=r.read().decode()
                return r.status,content if r.headers.get_content_type() in ('text/html','text/javascript','text/css','application/javascript') else json.loads(content)
        except HTTPError as e:
            return e.code,json.loads(e.read().decode())

    def action(self,jid,name,actor='Admin',**fields):
        return self.call(f'/api/jobs/{jid}/action',{'action':name,'actor':actor,'fields':fields})

    def test_01_bootstrap_operational_modules_and_assets(self):
        code,data=self.call('/api/bootstrap')
        self.assertEqual(code,200)
        self.assertIn('Customer Service',data['roles'])
        self.assertIn('Financing',data['roles'])
        op=data['operations']
        self.assertGreaterEqual(len(op['appointments']),5)
        self.assertGreaterEqual(len(op['invoices']),3)
        self.assertTrue(any(a['kind']=='Customer success' for a in op['alerts']))
        for path in ['/ops_ui.js','/app.js','/styles.css','/']:
            code,_=self.call(path)
            self.assertEqual(code,200,path)

    def test_02_scheduling_delays_and_notifications(self):
        future=(date.today()+timedelta(days=5)).isoformat()
        code,r=self.call('/api/ops/appointments',{'actor':'Front Desk','job_id':'F-1001','kind':'Follow-up call','scheduled_date':future,'time_window':'10AM–11AM','assignee':'Team A','owner_role':'Front Desk'})
        self.assertEqual(code,201,r)
        appt_id=r['id']
        code,bad=self.call(f'/api/ops/appointments/{appt_id}/status',{'actor':'Admin','status':'Delayed','eta_date':future})
        self.assertEqual(code,400)
        self.assertIn('reason',bad['error'])
        code,good=self.call(f'/api/ops/appointments/{appt_id}/status',{'actor':'Front Desk','status':'Delayed','reason':'Homeowner requested a later visit','eta_date':future})
        self.assertEqual(code,200,good)
        code,d=self.call('/api/ops/dashboard')
        self.assertTrue(any(a['job_id']=='F-1001' and a['kind']=='Delay' for a in d['alerts']))
        code,boot=self.call('/api/bootstrap')
        self.assertTrue(any(n['title']=='Follow-up call delayed' for n in boot['notifications']))

    def test_03_invoice_and_role_gate(self):
        due=(date.today()+timedelta(days=10)).isoformat()
        bad,msg=self.call('/api/ops/invoices',{'actor':'Vendor','job_id':'F-1004','category':'Deposit','amount':250,'due_date':due})
        self.assertEqual(bad,400)
        code,r=self.call('/api/ops/invoices',{'actor':'Accountant','job_id':'F-1004','category':'Deposit','amount':250,'due_date':due})
        self.assertEqual(code,201,r)
        code,d=self.call('/api/ops/dashboard')
        x=next(i for i in d['invoices'] if i['number'].startswith('FO-INV-'))
        code,html=self.call(f'/api/ops/invoices/{x["id"]}/print')
        self.assertEqual(code,200)
        self.assertIn('Fictional operations demonstration',html)
        code,r=self.call(f'/api/ops/invoices/{x["id"]}/status',{'actor':'Accountant','status':'Sent'})
        self.assertEqual(code,200)

    def test_04_complete_customer_to_satisfaction_and_review(self):
        code,new=self.call('/api/jobs',{'homeowner':'Fictional Full Journey','address':'100 Fictional Street','service_type':'Four windows','actor':'Front Desk'})
        self.assertEqual(code,201)
        jid=new['id'];soon=(date.today()+timedelta(days=3)).isoformat()
        steps=[
          ('qualify','Front Desk',{}),
          ('schedule_measurement','Sales',{'date':soon}),
          ('add_opening','Measurement Tech',{'room':'Living room','product_type':'Window','width':48,'height':36,'quantity':4,'unit_price':800}),
          ('complete_measurement','Measurement Tech',{'notes':'Four living room openings measured'}),
          ('send_proposal','Sales',{'amount':5000}),
          ('accept_proposal','Homeowner',{}),
          ('sign_contract','Sales',{'deposit':1200,'financing_type':'Customer pay'}),
          ('record_payment','Accountant',{'amount':1200,'kind':'Deposit'}),
          ('place_order','Installation Manager',{'vendor':'Example Supply','po':'PO-EXAMPLE','eta':soon}),
          ('materials_received','Vendor',{}),
          ('schedule_install','Installation Manager',{'date':soon}),
          ('installation_complete','Service Tech',{'notes':'Four windows installed, all sealed'}),
          ('qa_passed','Service Tech',{'notes':'Operation and cleanup verified'}),
          ('record_payment','Accountant',{'amount':3800,'kind':'Final'}),
          ('close_job','Accountant',{'terms':'Two-year example labor coverage'}),
        ]
        for action,actor,fields in steps:
            code,response=self.action(jid,action,actor,**fields)
            self.assertEqual(code,200,f'{action}: {response}')
        code,j=self.call(f'/api/jobs/{jid}')
        self.assertEqual(j['stage'],'Closed')
        code,ops=self.call(f'/api/ops/jobs/{jid}')
        self.assertEqual(len([a for a in ops['appointments'] if a['kind']=='Installation']),1)
        self.assertEqual(len([a for a in ops['appointments'] if a['kind']=='Measurement']),1)
        code,review=self.call('/api/ops/review',{'actor':'Customer Service','job_id':jid,'status':'Invited'})
        self.assertEqual(code,200,review)
        code,feedback=self.call('/api/ops/feedback',{'actor':'Homeowner','job_id':jid,'rating':2,'feedback':'Please check the window latch','contact_permission':True})
        self.assertEqual(code,200,feedback)
        code,d=self.call('/api/ops/dashboard')
        self.assertTrue(any(t['job_id']==jid and t['subject']=='Satisfaction recovery follow-up' for t in d['tickets']))
        self.assertEqual(next(s for s in d['satisfaction'] if s['job_id']==jid)['review_status'],'Invited')

    def test_05_support_ticket_and_guide(self):
        due=(date.today()+timedelta(days=2)).isoformat()
        code,r=self.call('/api/ops/tickets',{'actor':'Customer Service','job_id':'F-1008','category':'Warranty','subject':'Door adjustment','detail':'Customer reports handle feels loose','target_date':due})
        self.assertEqual(code,201,r)
        d=self.call('/api/ops/dashboard')[1]; ticket=next(t for t in d['tickets'] if t['subject']=='Door adjustment')
        self.assertEqual(self.call(f'/api/ops/tickets/{ticket["id"]}/status',{'actor':'Service Tech','status':'Resolved'})[0],200)
        for q in ['How do I measure windows?', 'What if a vendor delivery is delayed?', 'How do Google reviews work?']:
            code,guide=self.call('/api/ops/guide',{'question':q,'role':'Admin'})
            self.assertEqual(code,200)
            self.assertGreater(len(guide['answer']),80)
            self.assertIn('view',guide)

    def test_06_concurrent_handoff_and_out_of_order_actions(self):
        _, new = self.call('/api/jobs', {'homeowner':'Workflow Test','address':'100 Sample Way','actor':'Front Desk'})
        jid = new['id']
        self.assertEqual(self.action(jid,'close_job','Admin',terms='Example warranty')[0],400)
        warranty = {'actor':'Admin','job_id':jid,'category':'Warranty','subject':'Window latch',
                    'detail':'Check the installed window latch'}
        self.assertEqual(self.call('/api/ops/tickets',warranty)[0],400)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: self.action(jid,'qualify','Front Desk')[0], range(2)))
        self.assertEqual(sorted(outcomes), [200,400])
        _, job = self.call(f'/api/jobs/{jid}')
        self.assertEqual(job['stage'], 'Qualified')
        self.assertEqual([t['code'] for t in job['tasks'] if t['status']=='Open'], ['schedule_measurement'])
        _, boot = self.call('/api/bootstrap')
        self.assertEqual(sum(n['job_id']==jid and n['role']=='Sales' and n['title']=='Lead qualified'
                             for n in boot['notifications']), 1)
        visit = {'actor':'Sales','job_id':jid,'kind':'Measurement',
                 'scheduled_date':(date.today()+timedelta(days=2)).isoformat()}
        self.assertEqual(self.call('/api/ops/appointments',visit)[0],201)
        self.assertEqual(self.call('/api/ops/appointments',visit)[0],400)
        _, job = self.call(f'/api/jobs/{jid}')
        self.assertEqual(job['stage'], 'Measurement Scheduled')
        self.assertEqual([t['code'] for t in job['tasks'] if t['status']=='Open'], ['complete_measurement'])

if __name__=='__main__':unittest.main()
