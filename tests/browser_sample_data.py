"""One-click sample-input regression using an isolated FrameOps instance.

Verifies actual dynamic input forms at phone and desktop widths. Never submits
forms or sends POST requests to the production Render service.
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
BASE = "http://127.0.0.1:18996"
ARTIFACTS = ROOT / "artifacts" / "sample-inputs"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def expect_no_page_overflow(page, width, name):
    client, scroll = page.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    assert scroll <= client + 2, f"{name} horizontal overflow at {width}px ({scroll}>{client})"


def run_case(browser, width, height):
    ctx = browser.new_context(
        viewport={"width": width, "height": height}, device_scale_factor=1,
        reduced_motion="reduce",
    )
    page = ctx.new_page()
    errors = []
    write_requests = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda req: write_requests.append(req.url)
            if req.method in ("POST", "PUT", "PATCH", "DELETE") else None)
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=30000)
    page.locator(".ops-metric").first.wait_for(timeout=22000)
    assert page.locator('script[src="/sample-data.js"]').count() == 1
    assert not page.locator('#sign-in-form .sample-load-button').count(), (
        "Do not present fake credentials as authentic"
    )

    # The guide's message-entry box should show a button without changing chat send.
    assert page.locator('#ops-guide-form').count() == 1
    page.locator('.sample-load-chat-toolbar .sample-load-button').click(force=True)
    assert "Front Desk" in page.locator('#ops-guide-input').input_value()
    assert page.locator('#ops-guide-form button[type="submit"]').count() == 1

    # Business social settings: seven URL fields and their related toggles.
    if width <= 800:
        page.locator('#mobile-menu').click()
    page.locator('.sidebar [data-nav="business-settings"]').click()
    page.locator('#social-settings-form .sample-load-button').click()
    form = page.locator('#social-settings-form')
    assert form.locator('[name="facebook"]').input_value().startswith("https://www.facebook.com/")
    assert form.locator('[name="youtube"]').input_value().startswith("https://www.youtube.com/")
    assert form.locator('input[type="checkbox"]:checked').count() == 7
    assert form.locator(".sample-load-feedback").inner_text().endswith("Not submitted.")
    expect_no_page_overflow(page, width, "Business settings")
    if width in (390, 1440):
        page.screenshot(path=str(ARTIFACTS / f"social-{width}.png"), full_page=True)

    # Main operations storefront customer inquiry with role access intact.
    if width <= 800:
        page.locator("#mobile-menu").click()
    page.locator('.sidebar [data-nav="storefront"]').click()
    page.locator(".ops-store-hero").wait_for(timeout=15000)
    page.locator('[data-ops-open="storeLead"]').first.click()
    page.locator('#ops-form .sample-load-button').click()
    ops = page.locator("#ops-form")
    assert ops.locator('[name="homeowner"]').input_value() == "Morgan Rivera"
    assert "Example" in ops.locator('[name="address"]').input_value()
    assert ops.locator('[name="email"]').input_value().endswith("@example.com")
    assert ops.locator('[name="notes"]').input_value()
    assert ops.locator('.sample-field-hint').count() >= 4
    assert ops.locator('button[type="submit"]').count() == 1
    if width in (390, 1440):
        page.screenshot(path=str(ARTIFACTS / f"ops-modal-{width}.png"), full_page=True)
    page.locator('[data-ops-close]').first.click()

    # A second kind of operations form: date, select, and optional assignee.
    page.evaluate("opsOpen('appointment')")
    page.locator('#ops-form .sample-load-button').click()
    ops = page.locator("#ops-form")
    assert ops.locator('[name="scheduled_date"]').input_value()
    assert ops.locator('[name="time_window"]').input_value()
    assert ops.locator('[name="kind"]').input_value()
    assert ops.locator('[name="job_id"]').input_value()
    page.locator('[data-ops-close]').first.click()

    # App lifecycle form also receives the same action without submitting.
    page.locator('#role-select').select_option('Front Desk')
    page.evaluate("modal('newLead')")
    page.locator('#action-form .sample-load-button').click()
    act = page.locator("#action-form")
    assert act.locator('[name="homeowner"]').input_value() == "Morgan Rivera"
    assert act.locator('[name="lead_source"]').input_value() == "Website"
    assert act.locator('[name="priority"]').input_value() == "Normal"
    assert act.locator('[name="notes"]').input_value()
    page.locator('[data-modal-close]').first.click()

    # A non-form filter field retains one-click auto-entry.
    page.evaluate("go('jobs')")
    if page.locator("#job-search").count():
        assert page.locator(".sample-load-single .sample-load-button").count() >= 1
        page.locator(".sample-load-single .sample-load-button").first.click()
        assert page.locator("#job-search").input_value() == "F-"
    expect_no_page_overflow(page, width, "Operations")

    # Separate QA Bench: examples must never imply a test has passed.
    qa = ctx.new_page()
    qa_errors = []
    qa.on("pageerror", lambda error: qa_errors.append(str(error)))
    qa.goto(BASE + "/qa-bench.html", wait_until="domcontentloaded", timeout=30000)
    qa.locator("#project-title").wait_for()
    assert qa.locator('script[src="/sample-data.js"]').count() == 1
    qa.locator('button[data-tab="manual"]').click()
    qa.locator('#manual-form .sample-load-button').click()
    manual = qa.locator("#manual-form")
    assert manual.locator('[name="status"]').input_value() == "Blocked"
    assert "SAMPLE ONLY" in manual.locator('[name="actual"]').input_value()
    assert "SAMPLE ONLY" in manual.locator('[name="notes"]').input_value()
    assert manual.locator('.sample-load-feedback').inner_text().endswith("Not submitted.")
    assert manual.locator('button[type="submit"]').count() == 1
    expect_no_page_overflow(qa, width, "QA Bench")
    if width in (390, 1440):
        qa.screenshot(path=str(ARTIFACTS / f"qa-manual-{width}.png"), full_page=True)
    assert not qa_errors, f"QA browser JS errors at {width}: {qa_errors}"
    assert not write_requests, "Input helper must not create server-side records: " + str(write_requests)
    assert not errors, f"App browser JS errors at {width}: {errors}"
    print(f"PASS one-click inputs {width}x{height}: ops, social, lifecycle, guide, QA; no submissions")
    ctx.close()


def main():
    with tempfile.TemporaryDirectory(prefix="frameops-samples-") as tmp:
        env = os.environ.copy()
        env.update({
            "PUBLIC_DEMO": "1", "PORT": "18996",
            "DB_PATH": str(Path(tmp) / "frameops.db"),
            "UPLOAD_DIR": str(Path(tmp) / "uploads"),
        })
        server = subprocess.Popen(
            [sys.executable, "server.py"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(50):
                if server.poll() is not None:
                    raise RuntimeError(f"isolated server exited with {server.returncode}")
                try:
                    with urlopen(BASE + "/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(.5)
            else:
                raise RuntimeError("isolated server did not respond")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    for width, height in [(390, 844), (1440, 900)]:
                        run_case(browser, width, height)
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
