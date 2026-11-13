"""Developer browser smoke test for the fictional catalog and client-side social configuration.
Requires Playwright + system Chromium; uses inline assets and API stubs (no network).
Run: python tests/browser_storefront_smoke.py
"""
from pathlib import Path
import json
import sys
import tempfile
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server
import operations

with tempfile.TemporaryDirectory(prefix='frameops-browser-store-') as td:
    server.DB_PATH=Path(td)/'test.db';server.UPLOAD_DIR=Path(td)/'uploads';server.initialize()
    with server.db() as conn:
        jobs=server.list_jobs(conn)
        tasks=[dict(x) for x in conn.execute("SELECT t.*,j.homeowner,j.address,j.stage FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.status='Open' ORDER BY t.due_date LIMIT 120")]
        ns=[dict(x) for x in conn.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 150')]
        events=[dict(x) for x in conn.execute('SELECT e.*,j.homeowner FROM events e JOIN jobs j ON j.id=e.job_id ORDER BY e.id DESC LIMIT 24')]
        data={'jobs':jobs,'tasks':tasks,'notifications':ns,'events':events,'roles':server.ROLES,'stages':server.STAGES,'demo':True,'operations':operations.dashboard(conn)}
    html=(ROOT/'public/index.html').read_text()
    css=(ROOT/'public/styles.css').read_text()
    html=html.replace('<link rel="stylesheet" href="/styles.css">',f'<style>{css}</style>')
    scripts=['catalog','demo_journey','storefront','business_settings','quick_checkout','ops_ui','app']
    for name in scripts:html=html.replace(f'<script src="/{name}.js"></script>','')
    preload="""<script>
window.__demoStore = Object.create(null);
Object.defineProperty(window,'localStorage',{configurable:true,value:{
  getItem:key=>Object.prototype.hasOwnProperty.call(window.__demoStore,key)?window.__demoStore[key]:null,
  setItem:(key,value)=>{window.__demoStore[key]=String(value)},
  removeItem:key=>{delete window.__demoStore[key]},clear:()=>{window.__demoStore=Object.create(null)}
}});
"""
    preload+='const MOCK='+json.dumps(data)+';\n'
    preload+='''window.fetch=async(path,opts={})=>{
      if(path==='/api/bootstrap')return new Response(JSON.stringify(MOCK),{status:200,headers:{'Content-Type':'application/json'}});
      if(path==='/api/ops/guide')return new Response(JSON.stringify({title:'Guide',answer:'Use the business settings for your social links.',view:'business-settings'}),{status:200,headers:{'Content-Type':'application/json'}});
      return new Response(JSON.stringify({ok:true,id:'F-1009',message:'Saved'}),{status:200,headers:{'Content-Type':'application/json'}});
    };</script>'''
    scripts_html=''.join('<script>'+ (ROOT/'public'/f'{n}.js').read_text()+'</script>' for n in scripts)
    html=html.replace('</body>',preload+scripts_html+'</body>')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1360,'height':880})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='load',timeout=25000)
        page.wait_for_selector('.q-hero',timeout=5000)
        page.evaluate("go('business-settings')")
        assert 'Business & social settings' in page.locator('h1').first.inner_text()
        assert page.locator('.bs-platform').count()==7
        page.locator('#bs-facebook').fill('https://facebook.com.evil.example/test')
        page.locator('input[name="facebook-enabled"]').check()
        page.locator('#social-settings-form button[type="submit"]').click()
        assert page.locator('#bs-error').is_visible(),page.locator('#bs-error').inner_text()
        page.locator('#bs-facebook').fill('')
        page.locator('input[name="facebook-enabled"]').uncheck()
        page.locator('#bs-instagram').fill('https://www.instagram.com/westhaven_test')
        page.locator('input[name="instagram-enabled"]').check()
        page.locator('#bs-linkedin').fill('https://www.linkedin.com/company/westhaven-test')
        page.locator('input[name="linkedin-enabled"]').check()
        page.locator('#social-settings-form button[type="submit"]').click()
        assert page.locator('.bs-preview a.st-social-link').count()==2
        page.evaluate("go('storefront')")
        page.wait_for_selector('.q-product')
        assert page.locator('.q-product').count()==17,page.locator('.q-product').count()
        assert page.locator('#st-social-header a.st-social-link').count()==2
        assert page.locator('#st-social-footer a.st-social-link').count()==2
        assert page.locator('#st-social-header a').first.get_attribute('target')=='_blank'
        assert 'noopener' in page.locator('#st-social-header a').first.get_attribute('rel')
        # Change simulated localStorage settings and dispatch the same storage event a sibling tab would.
        page.evaluate('''() => {const x=JSON.parse(localStorage.getItem('frameops-business-social-links-v1'));
          x.instagram.enabled=false;localStorage.setItem('frameops-business-social-links-v1',JSON.stringify(x));
          window.dispatchEvent(new StorageEvent('storage',{key:'frameops-business-social-links-v1'}));}''')
        assert page.locator('#st-social-header a').count()==1
        assert 'LinkedIn' in page.locator('#st-social-header').inner_text()
        # Customer-facing store now progresses to the fast quote and paperless portal.
        page.locator('[data-q-add="CV-210"]').first.click()
        page.evaluate("go('quick-quote')")
        assert page.locator('#q-checkout-form').is_visible()
        assert page.evaluate('FrameOpsCheckout.pricing().compliant')
        assert not errors,errors
        # Mobile: menu, business settings, social URL field all accessible.
        page.set_viewport_size({'width':390,'height':844})
        page.evaluate("go('business-settings')")
        assert page.locator('#social-settings-form').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'), 'Mobile horizontal overflow'
        page.screenshot(path=str(ROOT/'assets/business-social-settings-mobile.png'),full_page=True)
        page.evaluate("go('storefront')")
        page.screenshot(path=str(ROOT/'assets/storefront-products-mobile.png'),full_page=True)
        print('PASS: 17 catalog products, seven social platforms, URL rejection, saved and linked settings, instant quote, mobile layout, no JS errors')
        browser.close()
