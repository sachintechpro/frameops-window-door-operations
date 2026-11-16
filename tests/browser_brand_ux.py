"""Cross-workspace visual and responsive checks for the Field Notes brand.

The test launches FrameOps locally with an isolated temporary SQLite database.
No HTTP mutation is performed against any public service.
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
BASE = "http://127.0.0.1:18995"
ARTIFACTS = ROOT / "artifacts" / "field-notes-brand"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(320, 700), (390, 844), (768, 1024), (1440, 900)]


def no_overflow(page, screen, label):
    widths = page.evaluate("""() => ({
        client: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
        body: document.body.scrollWidth
    })""")
    assert widths["content"] <= widths["client"] + 2, (
        f"{label} overflow at {screen}px: {widths}"
    )


def screenshot(page, name, width):
    if width in (390, 1440):
        page.screenshot(path=str(ARTIFACTS / f"{name}-{width}.png"), full_page=True)


def assess_brand(page, width, height):
    context = page.context
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=30000)
    page.locator(".ops-metric").first.wait_for(timeout=20000)
    assert page.locator(".ops-metric").count() >= 5
    assert "Every job. Every handoff. One view." in page.locator(".ops-welcome h1").inner_text()
    assert page.locator('link[href="/styles.css"]').count() == 1
    assert page.locator('link[href="/field-notes.css"]').count() == 1
    assert page.locator('a[href="/fde-implementation.html"]').count() == 1
    assert page.evaluate("getComputedStyle(document.querySelector('.sidebar')).backgroundColor") == "rgb(30, 57, 49)"
    assert "Newsreader" in page.locator(".ops-welcome h1").evaluate(
        "(el) => getComputedStyle(el).fontFamily"
    )
    assert page.locator(".ops-welcome").evaluate(
        "(el) => getComputedStyle(el, ':after').backgroundImage.includes('field-notes-elevation.svg')"
    )
    no_overflow(page, width, "Overview")
    screenshot(page, "overview", width)

    # Preserve the original navigation, storefront, and role behavior.
    if width <= 800:
        page.locator("#mobile-menu").click()
        page.locator('.sidebar [data-nav="storefront"]').click()
    else:
        page.locator('.sidebar [data-nav="storefront"]').click()
    page.locator(".st-hero h1").first.wait_for(timeout=15000)
    assert page.locator(".st-product").count() >= 1
    assert "Newsreader" in page.locator(".st-hero h1").evaluate(
        "(el) => getComputedStyle(el).fontFamily"
    )
    no_overflow(page, width, "Storefront")
    screenshot(page, "storefront", width)
    assert not errors, f"Operations JS errors at {width}px: {errors}"

    # New tab, same service and independent QA Bench (no test content changed).
    qa = context.new_page()
    qa_errors = []
    qa.on("pageerror", lambda error: qa_errors.append(str(error)))
    qa.goto(BASE + "/qa-bench.html", wait_until="domcontentloaded", timeout=30000)
    qa.locator("#project-title").wait_for(timeout=15000)
    assert "FrameOps QA Bench" in qa.locator("#project-title").inner_text()
    assert qa.locator('link[href="/field-notes.css"]').count() == 1
    assert qa.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(244, 241, 232)"
    assert "Newsreader" in qa.locator("#project-title").evaluate(
        "(el) => getComputedStyle(el).fontFamily"
    )
    assert qa.locator('button[data-tab="requirements"]').count() == 1
    qa.locator('button[data-tab="cases"]').click()
    assert qa.locator('button[data-tab="cases"]').get_attribute("aria-selected") == "true"
    qa.locator('button[data-tab="requirements"]').click()
    no_overflow(qa, width, "QA Bench")
    screenshot(qa, "qa-bench", width)
    assert not qa_errors, f"QA Bench JS errors at {width}px: {qa_errors}"
    qa.close()
    print(f"PASS theme: {width}x{height}; overview, storefront, QA; original navigation, tabs, no overflow")


def main():
    with tempfile.TemporaryDirectory(prefix="frameops-brand-") as temp:
        env = os.environ.copy()
        env.update({"PUBLIC_DEMO": "1", "PORT": "18995",
                    "DB_PATH": str(Path(temp) / "frameops.db"),
                    "UPLOAD_DIR": str(Path(temp) / "uploads")})
        server = subprocess.Popen(
            [sys.executable, "server.py"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError(f"isolated server exited: {server.returncode}")
                try:
                    with urlopen(BASE + "/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(.5)
            else:
                raise RuntimeError("isolated server did not start")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    for width, height in VIEWPORTS:
                        context = browser.new_context(
                            viewport={"width": width, "height": height},
                            device_scale_factor=1, reduced_motion="reduce",
                        )
                        try:
                            assess_brand(context.new_page(), width, height)
                        finally:
                            context.close()
                finally:
                    browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    main()
