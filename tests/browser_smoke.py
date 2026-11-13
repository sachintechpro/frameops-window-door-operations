"""Developer-only DOM smoke test using inline assets to avoid restricted browser networking.
Backend routes and mutations are exercised by test_operations.py using real HTTP.
"""
import json
from pathlib import Path
import sqlite3
import tempfile
from playwright.sync_api import sync_playwright
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import operations
import server

with tempfile.TemporaryDirectory(prefix='frameops-ui-') as d:
    server.DB_PATH=Path(d)/'test.db'
    server.UPLOAD_DIR=Path(d)/'uploads'
    server.initialize()
    with server.db() as conn:
        jobs=server.list_jobs(conn)
        tasks=[dict(x) for x in conn.execute("SELECT t.*,j.homeowner,j.address,j.stage FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.status='Open' ORDER BY t.due_date LIMIT 120")]
        ns=[dict(x) for x in conn.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 150')]
        events=[dict(x) for x in conn.execute('SELECT e.*,j.homeowner FROM events e JOIN jobs j ON j.id=e.job_id ORDER BY e.id DESC LIMIT 24')]
        payload={'jobs':jobs,'tasks':tasks,'notifications':ns,'events':events,'roles':server.ROLES,'stages':server.STAGES,'demo':True,'operations':operations.dashboard(conn)}
    html=(ROOT/'public/index.html').read_text()
    css=(ROOT/'public/styles.css').read_text()
    ops=(ROOT/'public/ops_ui.js').read_text()
    app=(ROOT/'public/app.js').read_text()
    html=html.replace('<link rel="stylesheet" href="/styles.css">',f'<style>{css}</style>')
    html=html.replace('<script src="/ops_ui.js"></script>', '')
    html=html.replace('<script src="/app.js"></script>', '')
    mocked=f'''<script>const STUB={json.dumps(payload)};
    window.fetch=async (path,options={{}})=> {{
      if(path==='/api/bootstrap')return new Response(JSON.stringify(STUB),{{status:200,headers:{{'Content-Type':'application/json'}}}});
      if(path==='/api/ops/guide')return new Response(JSON.stringify({{'title':'Documents and invoices','answer':'Open Documents & Invoices to review invoices, print records, and update external payment status. This guide does not perform transactions.','view':'documents'}}),{{status:200,headers:{{'Content-Type':'application/json'}}}});
      return new Response(JSON.stringify({{'ok':true,'id':'F-1009','message':'Saved'}}),{{status:200,headers:{{'Content-Type':'application/json'}}}});
    }};
    </script>'''
    html=html.replace('</body>',mocked+f'<script>{ops}</script><script>{app}</script></body>')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for viewport,label in [({'width':1440,'height':900},'desktop'),({'width':390,'height':844},'mobile')]:
            page=browser.new_page(viewport=viewport,device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content(html,wait_until='load',timeout=20000)
            page.wait_for_selector('.ops-metrics',timeout=4000)
            assert 'Every job. Every handoff' in page.locator('#app').inner_text()
            assert page.locator('.ops-job-tile').count()>=6
            page.screenshot(path=str(ROOT / 'assets' / ('operations-mobile.png' if label=='mobile' else 'operations-dashboard.png')),full_page=True)
            print(label,'dashboard renders',page.locator('#app h1').first.inner_text(),'JS errors:',errors)
            if label=='mobile':page.locator('#mobile-menu').click()
            page.locator('#ops-guide-launch').click()
            assert page.locator('#ops-guide-panel').is_visible()
            page.locator('#ops-guide-input').fill('How do invoices work?')
            page.locator('#ops-guide-form button').click()
            page.wait_for_timeout(150)
            assert page.locator('.ops-guide-reply').count()>=2
            page.locator('#ops-guide-close').click()
            page.locator('[data-nav="storefront"]').first.click()
            assert 'Plan your next installation' in page.locator('.ops-store-hero h2').inner_text()
            page.locator('[data-ops-open="storeLead"]').first.click()
            assert page.locator('#ops-form').is_visible()
            page.locator('[data-ops-close]').first.click()
            if label=='mobile':page.locator('#mobile-menu').click()
            page.locator('[data-nav="customer-service"]').first.click()
            assert 'Customer Service' in page.locator('.ops-page-head h1').inner_text()
            assert not errors,errors
            page.wait_for_timeout(320)
            page.screenshot(path=f'/mnt/data/frameops-v2-{label}.png',full_page=True)
            print(label,'storefront, help chat, customer service screens render; screenshot stored')
            page.close()
        browser.close()
