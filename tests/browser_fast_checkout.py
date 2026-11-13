"""Real Chromium DOM tests for customer-facing quote, paperless portal and role notifications.
Uses fictional bootstrap data and localStorage stub. No network, payments, SMS, or email.
"""
from pathlib import Path
import json,sys,tempfile,base64
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server,operations

with tempfile.TemporaryDirectory(prefix='frameops-fast-checkout-') as d:
    server.DB_PATH=Path(d)/'demo.db';server.UPLOAD_DIR=Path(d)/'uploads';server.initialize()
    with server.db() as con:
        jobs=server.list_jobs(con)
        tasks=[dict(x) for x in con.execute("SELECT t.*,j.homeowner,j.address,j.stage FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.status='Open' ORDER BY t.due_date LIMIT 120")]
        notifications=[dict(x) for x in con.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 150')]
        events=[dict(x) for x in con.execute('SELECT e.*,j.homeowner FROM events e JOIN jobs j ON j.id=e.job_id ORDER BY e.id DESC LIMIT 24')]
        data={'jobs':jobs,'tasks':tasks,'notifications':notifications,'events':events,'roles':server.ROLES,'stages':server.STAGES,'demo':True,'operations':operations.dashboard(con)}
    html=(ROOT/'public/index.html').read_text()
    css=(ROOT/'public/styles.css').read_text()
    html=html.replace('<link rel="stylesheet" href="/styles.css">',f'<style>{css}</style>')
    scripts=['catalog','demo_journey','storefront','business_settings','quick_checkout','ops_ui','app']
    for name in scripts:html=html.replace(f'<script src="/{name}.js"></script>','')
    pre='''<script>
window.__mem={};Object.defineProperty(window,'localStorage',{configurable:true,value:{
  getItem:k=>Object.prototype.hasOwnProperty.call(window.__mem,k)?window.__mem[k]:null,
  setItem:(k,v)=>window.__mem[k]=String(v),removeItem:k=>delete window.__mem[k]}});
const MOCK='''+json.dumps(data)+''';
window.fetch=async(path)=>{
 if(path==='/api/bootstrap')return new Response(JSON.stringify(MOCK),{status:200,headers:{'Content-Type':'application/json'}});
 if(path==='/api/ops/guide')return new Response(JSON.stringify({title:'Demo',answer:'Use the fast quote.',view:'quick-quote'}),{status:200,headers:{'Content-Type':'application/json'}});
 return new Response(JSON.stringify({ok:true,id:'F-1009',message:'Saved'}),{status:200,headers:{'Content-Type':'application/json'}});
};</script>'''
    images={p.stem.upper(): 'data:image/svg+xml;base64,'+base64.b64encode(p.read_bytes()).decode('ascii') for p in (ROOT/'public/images').glob('*.svg')}
    # Serve the original SVG illustrations inline: about:blank browser smoke cannot fetch /images/.
    content=''
    for n in scripts:
        code=(ROOT/'public'/f'{n}.js').read_text()
        if n=='catalog':code+='\nconst INLINE_IMAGES='+json.dumps(images)+';window.FRAMEOPS_CATALOG.products.forEach(p=>p.visual=INLINE_IMAGES[p.sku]||p.visual);'
        content+='<script>'+code+'</script>'
    html=html.replace('</body>',pre+content+'</body>')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for label,width,height in [('desktop',1440,900),('mobile',390,844)]:
            page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
            errors=[];page.on('pageerror',lambda x:errors.append(str(x)))
            page.set_content(html,wait_until='load',timeout=25000)
            page.wait_for_selector('.q-hero',timeout=10000)
            page.wait_for_selector('.q-hero',timeout=5000)
            assert page.locator('.q-product').count()==17
            assert page.locator('body').evaluate('(e)=>e.classList.contains("customer-mode")')
            assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2'), 'Shop horizontal overflow'
            page.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
            page.wait_for_timeout(200)
            page.screenshot(path=str(ROOT/'assets'/f'consumer-storefront-{label}.png'),full_page=True)
            page.locator('[data-q-add="CV-210"]').first.click()
            page.locator('[data-q-add="CV-P220"]').first.click()
            page.locator('.q-site-links [data-nav="quick-quote"]').click()
            page.wait_for_selector('#q-checkout-form')
            page.screenshot(path=str(ROOT/'assets'/f'consumer-fast-quote-{label}.png'),full_page=True)
            assert page.locator('#q-checkout-form').is_visible()
            assert page.locator('.q-item').count()==2
            calculated=page.evaluate("FrameOpsCheckout.pricing()")
            assert calculated['compliant']
            assert calculated['total']>=calculated['minimum']
            page.locator('input[name="name"]').fill('Alex Example')
            page.locator('input[name="email"]').fill('alex@example.com')
            page.locator('input[name="phone"]').fill('555-010-0123')
            page.locator('input[name="address"]').fill('123 Example Street, Sampletown')
            page.locator('input[name="signature"]').fill('Alex Example')
            page.locator('input[name="consent"]').check()
            page.locator('#q-checkout-form button[type="submit"]').click()
            page.wait_for_selector('.q-hub-hero',timeout=5000)
            page.screenshot(path=str(ROOT/'assets'/f'consumer-portal-{label}.png'),full_page=True)
            data_after=page.evaluate('FrameOpsCheckout.read()')
            assert len(data_after['orders'])==1
            order=data_after['orders'][0]
            assert order['payment']['advance']>=round(order['quote']['total']*.1,2)
            assert order['sign']['name']=='Alex Example'
            for name in ['Homeowner','Admin','Measurement Tech','Installation Manager','Accountant']:
                assert any(n['role']==name for n in order['notifications']),name
            assert page.locator('.q-doc').count()==5
            assert page.locator('.q-msg').count()>=2
            # Customer appointment confirmation, followed by a schedule change notification.
            page.locator('[data-q-action="confirm_measurement"]').first.click()
            page.locator('[data-q-dialog="reschedule_installation"]').first.click()
            page.wait_for_selector('#q-action-form')
            page.locator('#q-action-form input[name="date"]').fill(page.evaluate("(()=>{const d=new Date();d.setDate(d.getDate()+24);return d.toISOString().slice(0,10)})()"))
            page.locator('#q-action-form button[type="submit"]').click()
            assert not page.locator('#q-action-form').count(), page.locator('#q-dialog-error').inner_text()
            assert any(x['title']=='Installation rescheduled' for x in page.evaluate('FrameOpsCheckout.read().orders[0].events'))
            # Operations inbox and reminder previews.
            page.evaluate("go('quote-operations')")
            page.wait_for_selector('.q-ops-page')
            page.locator('[data-q-clock="24"]').click()
            assert any(x['kind']=='reminder' for x in page.evaluate('FrameOpsCheckout.read().orders[0].notifications'))
            page.screenshot(path=str(ROOT/'assets'/f'fast-quote-{label}.png'),full_page=True)
            page.evaluate("go('customer-hub')")
            assert page.locator('.q-hub-hero').count()==1
            assert page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2'), 'Portal horizontal overflow'
            assert not errors,errors
            print(label,'shop, instant quote, simulated advance, portal, reschedule and reminders PASS')
            page.close()
        browser.close()
