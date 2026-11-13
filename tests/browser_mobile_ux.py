"""Browser-level mobile UX regression for FrameOps (synthetic isolated data only).

Run in GitHub Actions with Playwright Chromium. No public Render mutations.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18993"
ARTIFACTS = ROOT / "artifacts" / "mobile-ux"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def near(value, expected, margin=3):
    return abs(value-expected) <= margin


def assert_bounded(page, selector, width, message):
    box = page.locator(selector).first.bounding_box()
    assert box, f"{message}: element not rendered"
    assert box["x"] >= -3, f"{message}: left edge {box}"
    assert box["x"]+box["width"] <= width+3, f"{message}: right edge {box} > {width}"
    return box


def inspect_page(browser, width, height):
    context = browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE+"/", wait_until="domcontentloaded", timeout=35000)
    page.wait_for_selector(".ops-metrics .ops-metric",timeout=25000)
    page.wait_for_selector("#app > .sim-mini-banner",timeout=25000)
    assert page.locator(".ops-metric").count() >= 5
    assert page.locator(".ops-welcome h1").first.inner_text() == "Every job. Every handoff. One view."
    assert "Fictional data" in page.locator(".public-demo-note").inner_text()
    assert "Sample workflow:" in page.locator("#app > .sim-mini-banner strong").inner_text()

    actual_width = page.evaluate("document.documentElement.clientWidth")
    document_width = page.evaluate("document.documentElement.scrollWidth")
    assert document_width <= actual_width+2, f"horizontal overflow {document_width}>{actual_width} at viewport {width}"

    sim_box = assert_bounded(page, "#app > .sim-mini-banner", actual_width, "role simulation")
    assert_bounded(page, ".ops-metrics", actual_width, "metric grid")
    assert_bounded(page, ".ops-welcome", actual_width, "welcome summary")
    assert_bounded(page, ".public-demo-note", actual_width, "fictional data notice")

    metric_top=page.locator(".ops-metrics").bounding_box()["y"]
    welcome_top=page.locator(".ops-welcome").bounding_box()["y"]
    assert metric_top < welcome_top, f"metrics should appear before welcome hero: {metric_top}, {welcome_top}"
    assert page.locator(".ops-welcome-actions .button").count() == 2

    if width <= 800:
        assert page.locator(".mobile-menu").is_visible()
        assert_bounded(page, ".topbar .breadcrumb", actual_width, "navigation title")
        assert_bounded(page, ".topbar #top-notifications", actual_width, "notifications")
        assert_bounded(page, ".topbar .role-box", actual_width, "role switcher")
        title=page.locator(".topbar .breadcrumb strong")
        assert title.evaluate("(el)=>el.scrollHeight<=el.clientHeight+2"), "Header title wrapped vertically"
        guide=page.locator("#ops-guide-launch")
        bubble=assert_bounded(page,"#ops-guide-launch",actual_width,"floating guide")
        if width <= 670:
            assert bubble["width"]<=58 and bubble["height"]<=58, f"Guide too large on phone: {bubble}"
        assert page.locator(".ops-guide-button").get_attribute("aria-label") == "Open FrameOps operating guide"
        assert sim_box["y"] > page.locator(".topbar").bounding_box()["y"], "Status banner overlays header"

        # Verify role navigation still works rather than only inspecting CSS.
        page.locator("#mobile-menu").click()
        assert "open" in (page.locator("#sidebar").get_attribute("class") or "")
        # The open navigation intentionally covers the menu; dismiss via backdrop.
        page.mouse.click(width-8, height//2)
        assert "open" not in (page.locator("#sidebar").get_attribute("class") or "")
        guide.click()
        assert page.locator("#ops-guide-panel").is_visible()
        page.locator("#ops-guide-close").click()
        assert not page.locator("#ops-guide-panel").is_visible()

    if width in (390,1440):
        page.screenshot(path=str(ARTIFACTS / f"frameops-{width}.png"), full_page=True)

    assert not errors, f"JavaScript console errors at {width}: {errors}"
    print(f"PASS: {width}x{height}, no overflow, banner aligned, metrics prioritized, mobile controls responsive")
    context.close()


def main():
    with tempfile.TemporaryDirectory(prefix="frameops-mobile-qa-") as tmp:
        env = os.environ.copy()
        env.update({"PUBLIC_DEMO":"1","PORT":"18993",
                    "DB_PATH":str(Path(tmp)/"frameops.db"),
                    "UPLOAD_DIR":str(Path(tmp)/"uploads")})
        server = subprocess.Popen([sys.executable,"server.py"],cwd=ROOT,env=env,
                                  stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
        try:
            for i in range(40):
                if server.poll() is not None:
                    raise RuntimeError(f"Isolated server exited with {server.returncode}")
                try:
                    with urlopen(BASE+"/",timeout=2) as res:
                        if res.status==200: break
                except Exception:
                    time.sleep(.5)
            else:
                raise RuntimeError("Isolated FrameOps server failed to respond")

            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
                try:
                    for width,height in [(320,700),(390,844),(768,1024),(1440,900)]:
                        inspect_page(browser,width,height)
                finally:
                    browser.close()
        finally:
            server.terminate()
            try: server.wait(timeout=8)
            except subprocess.TimeoutExpired: server.kill()


if __name__=="__main__":
    main()
