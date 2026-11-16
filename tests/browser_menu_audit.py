"""Comprehensive FrameOps menu + role + job-tab visual UI regression.

Static navigation audit of every main-menu destination in an isolated
public-demo instance. No form submissions or live server mutations.
Produces per-screen page metrics and screenshots for direct visual review.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18998"
OUT = ROOT / "artifacts" / "full-menu-ui"
OUT.mkdir(parents=True,exist_ok=True)
PAGES = [
    "storefront", "demo-journey", "overview", "business-settings",
    "frontdesk", "leads", "measurements", "vendors", "installation",
    "financing", "accounting", "documents", "warranty", "customer-service",
    "jobs", "tasks", "notifications", "homeowner", "workflow"
]
ROLES = ["Admin", "Front Desk", "Sales", "Measurement Tech", "Accountant",
         "Vendor", "Installation Manager", "Service Tech", "Homeowner",
         "Financing", "Customer Service", "Warranty Coordinator"]
SIZES = [(320,700), (390,844), (768,1024), (1440,900)]
LAYOUTS = {
    ".ops-metrics": "grid",
    ".ops-main": "grid",
    ".ops-record-grid": "grid",
    ".ops-cardgrid": "grid",
    ".ops-split": "grid",
    ".bs-grid": "grid",
    ".st-layout": "grid",
    ".workflow-phases": "grid",
    ".stats-grid": "grid",
    ".sim-summary": "grid",
    ".sim-main": "grid",
    ".sim-actions": "grid",
}


def metrics(page, route, width):
    return page.evaluate("""({route, width}) => {
      const root = document.documentElement;
      const app = document.getElementById('app');
      const title=app.querySelector('h1,h2');
      const rootSurface=app.firstElementChild;
      const cs=el=>getComputedStyle(el);
      const box=el=>{const r=el.getBoundingClientRect();return {x:+r.left.toFixed(1),width:+r.width.toFixed(1),right:+r.right.toFixed(1)}};
      const grids=['.ops-metrics','.ops-record-grid','.ops-cardgrid','.ops-split',
                   '.bs-grid','.st-layout','.workflow-phases','.stats-grid',
                   '.sim-summary','.sim-main','.sim-actions'];
      const bg=(el)=>el ? cs(el).backgroundColor : '';
      const missing=[];
      const layout={};
      for(const selector of grids){
        const el=app.querySelector(selector);
        if(el){layout[selector]={display:cs(el).display,gridTemplateColumns:cs(el).gridTemplateColumns,bounds:box(el)};
          if(cs(el).display!=='grid')missing.push(selector+'='+cs(el).display);
        }
      }
      const visible = Array.from(app.querySelectorAll('button:not([hidden]),a:not([hidden])'))
         .filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0});
      const overflowing = visible.filter(el=>{const r=el.getBoundingClientRect();return r.left< -5 || r.right>root.clientWidth+5})
         .slice(0,8).map(el=>({text:el.textContent.trim().slice(0,60),bounds:box(el)}));
      const sampled=Array.from(app.querySelectorAll('.ops-card,.ops-record,.ops-job-tile,.ops-metric,.stat-card,.panel,.sim-card,.bs-platform')).slice(0,20);
      const transparent=sampled.filter(el=>cs(el).backgroundColor==='rgba(0, 0, 0, 0)'&&cs(el).borderTopWidth==='0px')
         .slice(0,8).map(el=>el.className);
      return {route,width,documentWidth:root.clientWidth,contentWidth:root.scrollWidth,
        routeRendered:!!title,title:title?.textContent?.trim().slice(0,140)||'',
        titleFont:title?cs(title).fontFamily:'',
        baseFont:cs(app).fontFamily,firstClass:rootSurface?.className||'',
        firstWidth:rootSurface?box(rootSurface):null,layout,missingLayout:missing,
        visibleActions:visible.length,offscreenActions:overflowing,
        cardSamples:sampled.length,unstyledCardCandidates:transparent,
        background:bg(rootSurface),hasPaintedPanel:sampled.some(el=>cs(el).backgroundColor!=='rgba(0, 0, 0, 0)')};
    }""",{"route":route,"width":width})


def audit(browser,width,height):
    context=browser.new_context(viewport={"width":width,"height":height},
       device_scale_factor=1,reduced_motion="reduce")
    page=context.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(BASE+"/",wait_until="domcontentloaded",timeout=30000)
    page.locator(".ops-metric").first.wait_for(timeout=25000)
    assert page.locator('.sidebar [data-nav]').count() >= 19

    failures=[]
    report=[]
    for route in PAGES:
        if route=="demo-journey":
            page.evaluate("go('overview')")
            page.locator('#app > .sim-mini-banner [data-nav="demo-journey"]').click()
        else:
            page.evaluate("(view)=>go(view)",route)
        page.locator("#app > *").first.wait_for()
        page.wait_for_timeout(50)
        result=metrics(page,route,width)
        report.append(result)
        if not result["routeRendered"]:failures.append(f"{route}: no heading")
        if result["missingLayout"]:failures.append(f"{route}: grid missing {result['missingLayout']}")
        if result["contentWidth"]>result["documentWidth"]+3:
            failures.append(f"{route}: horizontal overflow {result['contentWidth']}>{result['documentWidth']}")
        if result["offscreenActions"]:
            failures.append(f"{route}: offscreen interactive controls {result['offscreenActions']}")
        if result["visibleActions"]<1:failures.append(f"{route}: no actionable controls")
        if width in (390,1440):
            page.screenshot(path=str(OUT/f"menu-{route}-{width}.png"),full_page=True,timeout=30000)
        print("MENU",width,route,json.dumps({key:result[key] for key in
           ("title","contentWidth","documentWidth","missingLayout","visibleActions","offscreenActions")}),flush=True)

    # Actual job detail and tabs, reached through the existing menu.
    page.evaluate("go('jobs')")
    page.locator('[data-job]').first.click()
    page.locator(".job-tabs .job-tab").first.wait_for(timeout=12000)
    for tab in ["journey","openings","financials","documents","activity"]:
        button=page.locator(f'.job-tabs [data-tab="{tab}"]')
        if button.count() and button.is_visible():
            button.click()
            result=metrics(page,"job-"+tab,width)
            report.append(result)
            if result["contentWidth"]>result["documentWidth"]+3:
                failures.append(f"job-{tab}: overflow")
            if width in (390,1440):
                page.screenshot(path=str(OUT/f"job-{tab}-{width}.png"),full_page=True,timeout=30000)

    # Switch each public-demo role and ensure the default view remains usable.
    page.evaluate("go('overview')")
    for role in ROLES:
        page.locator("#role-select").select_option(label=role)
        role_report=metrics(page,"role-"+role,width)
        report.append(role_report)
        if not role_report["routeRendered"]:failures.append(f"role {role}: no content")
        if role_report["contentWidth"]>role_report["documentWidth"]+3:
            failures.append(f"role {role}: overflow")
        if role_report["offscreenActions"]:
            failures.append(f"role {role}: offscreen controls")
    page.locator("#role-select").select_option(label="Admin")

    path=OUT/f"metrics-{width}.json"
    path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    if errors:failures.append(f"JS page exceptions: {errors}")
    print(f"SCREEN AUDIT {width}px: {len(PAGES)} menu destinations, 5 detail tabs, {len(ROLES)} roles; {len(failures)} failures.",flush=True)
    for failure in failures:print("AUDIT ISSUE",width,failure,flush=True)
    context.close()
    assert not failures, f"{width}px menu audit failures: "+ "; ".join(failures[:12])


def main():
    with tempfile.TemporaryDirectory(prefix="frameops-menu-audit-") as temp:
        env=os.environ.copy()
        env.update({"PUBLIC_DEMO":"1","PORT":"18998",
                    "DB_PATH":str(Path(temp)/"frameops.db"),
                    "UPLOAD_DIR":str(Path(temp)/"uploads")})
        server=subprocess.Popen([sys.executable,"server.py"],cwd=ROOT,env=env,
                                stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                if server.poll() is not None:raise RuntimeError(f"demo server exited {server.returncode}")
                try:
                    with urlopen(BASE+"/health",timeout=2) as resp:
                        if resp.status==200:break
                except Exception:time.sleep(.5)
            else:raise RuntimeError("local demo server failed to start")
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    for width,height in SIZES:audit(browser,width,height)
                finally:browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=8)
            except subprocess.TimeoutExpired:server.kill()


if __name__=="__main__":main()
