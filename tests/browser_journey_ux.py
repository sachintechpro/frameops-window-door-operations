"""FrameOps Live Journey Simulator visual regression.

Exercises the exact "Open sample journey" entry point the visitor used,
in an isolated local public-demo instance. Simulator state is browser-local;
no production records or remote services are modified.
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
BASE = "http://127.0.0.1:18997"
SHOT_DIR = ROOT / "artifacts" / "journey-ux"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
SIZES = [(320, 700), (375, 812), (390, 844), (768, 1024), (1024, 768), (1440, 900)]


def bounded(page, selector, width):
    el = page.locator(selector).first
    box = el.bounding_box()
    assert box and box["width"] >= 5 and box["height"] >= 5, f"{selector} not visible: {box}"
    assert box["x"] >= -2, f"{selector} outside left of {width}px: {box}"
    assert box["x"] + box["width"] <= width + 2, f"{selector} clipped right at {width}px: {box}"
    return box


def no_horizontal_page_overflow(page, label):
    result = page.evaluate("""() => ({
       client: document.documentElement.clientWidth,
       scroll: document.documentElement.scrollWidth
    })""")
    assert result["scroll"] <= result["client"] + 2, f"{label}: {result}"


def inspect(browser, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1, reduced_motion="reduce",
        is_mobile=width < 600,
        has_touch=width < 600,
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=30000)
    page.locator(".ops-metric").first.wait_for(timeout=20000)

    banner = page.locator("#app > .sim-mini-banner")
    banner.wait_for()
    banner.locator('button[data-nav="demo-journey"]').click()
    page.locator("#sim-area .sim-summary").wait_for(timeout=12000)

    assert page.locator('link[href="/journey.css"]').count() == 1
    assert page.locator("#sim-area .sim-card").count() >= 5
    assert page.locator("#sim-area .sim-summary > div").count() == 4
    assert page.locator("#sim-area .sim-schedule").count() == 3
    assert page.locator("#sim-area .sim-actions .sim-btn").count() >= 3
    assert page.locator("#sim-area .sim-inbox").count() == 1
    assert "Newsreader" in page.locator("#sim-area h1").evaluate(
        "el => getComputedStyle(el).fontFamily"
    )
    assert page.locator("#sim-area .sim-summary").evaluate(
        "el => getComputedStyle(el).display"
    ) == "grid"
    assert page.locator("#sim-area .sim-main").evaluate(
        "el => getComputedStyle(el).display"
    ) == "grid"
    assert page.locator("#sim-area .sim-actions").evaluate(
        "el => getComputedStyle(el).display"
    ) == "grid"
    assert page.locator("#sim-area .sim-card").first.evaluate(
        "el => getComputedStyle(el).backgroundColor"
    ) == "rgb(255, 253, 248)"

    client = page.evaluate("document.documentElement.clientWidth")
    no_horizontal_page_overflow(page, f"Journey initial {width}")
    for selector in (
        "#sim-area", "#sim-area .sim-top", "#sim-area .sim-title",
        "#sim-area .sim-summary", "#sim-area .sim-main",
        "#sim-area .sim-actions", "#sim-area .sim-schedules",
        "#sim-area .sim-inbox",
    ):
        bounded(page, selector, client)

    for row in page.locator("#sim-area .sim-summary > div").all():
        label = row.locator("span").bounding_box()
        value = row.locator("strong").bounding_box()
        assert label and value and label["y"] + label["height"] <= value["y"] + 3, (
            f"Summary label and value collide at {width}px: {label}, {value}"
        )

    actions = page.locator("#sim-area .sim-actions .sim-btn")
    for index in range(actions.count()):
        bounded(page, f"#sim-area .sim-actions .sim-btn:nth-child({index+1})", client)

    if width <= 580:
        one = actions.first.bounding_box()
        parent = page.locator("#sim-area .sim-actions").bounding_box()
        assert one["width"] >= parent["width"] * .95, (
            f"Phone buttons should form readable full-width rows: {one}, {parent}"
        )
    if width in (320, 390, 768, 1440):
        page.screenshot(path=str(SHOT_DIR / f"journey-before-{width}.png"), full_page=True)

    # Confirm a future-date modal is actually readable and sample autofill still works.
    page.locator('#sim-area [data-sim-action="reschedule_delivery"]').click()
    modal = page.locator(".sim-modal-backdrop .sim-modal")
    modal.wait_for()
    assert modal.locator('input[type="date"]').count() == 1
    assert modal.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(255, 253, 248)"
    assert modal.locator("#sim-form .sample-load-button").count() == 1
    modal.locator("#sim-form .sample-load-button").click()
    assert modal.locator('#sim-form input[name="date"]').input_value()
    no_horizontal_page_overflow(page, f"Simulator modal {width}")
    bounded(page, ".sim-modal-backdrop .sim-modal", client)
    if width in (390, 1440):
        page.screenshot(path=str(SHOT_DIR / f"journey-modal-{width}.png"), full_page=False)
    modal.locator('[data-sim-close]').first.click()

    # A simulated advance is a local-only action and must preserve the journey transitions.
    assert "Awaiting simulated advance" in page.locator("#sim-area .sim-summary").inner_text()
    page.locator('#sim-area [data-sim-action="deposit"]').click()
    modal = page.locator(".sim-modal-backdrop .sim-modal")
    assert modal.is_visible()
    modal.locator('#sim-form button[type="submit"]').click()
    page.locator("#sim-area .sim-receipt").wait_for()
    assert "Simulated advance paid" in page.locator("#sim-area .sim-summary").inner_text()
    no_horizontal_page_overflow(page, f"Journey after action {width}")
    assert not errors, f"Journey JavaScript errors at {width}px: {errors}"
    context.close()
    print(f"PASS journey {width}x{height}: entry, panels, text, actions, modal, simulation and no overflow")


def main():
    with tempfile.TemporaryDirectory(prefix="frameops-journey-") as temp:
        env = os.environ.copy()
        env.update({
            "PUBLIC_DEMO": "1", "PORT": "18997",
            "DB_PATH": str(Path(temp) / "frameops.db"),
            "UPLOAD_DIR": str(Path(temp) / "uploads"),
        })
        server = subprocess.Popen(
            [sys.executable, "server.py"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(50):
                if server.poll() is not None:
                    raise RuntimeError(f"Isolated server exited: {server.returncode}")
                try:
                    with urlopen(BASE + "/health", timeout=2) as resp:
                        if resp.status == 200:
                            break
                except Exception:
                    time.sleep(.5)
            else:
                raise RuntimeError("Isolated demo server failed to respond")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    for width, height in SIZES:
                        inspect(browser, width, height)
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
