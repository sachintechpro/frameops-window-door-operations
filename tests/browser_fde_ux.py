"""Browser regression for the presentation-only FrameOps FDE redesign.

Uses a local, isolated public-demo server. No real Render data is mutated.
Validates six viewport widths, eight tab panels, four read-only API probes,
keyboard navigation, and screenshots for visual inspection.
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
BASE = "http://127.0.0.1:18994"
OUTPUT = ROOT / "artifacts" / "fde-ux"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTHS = [(320, 700), (375, 812), (390, 844), (768, 1024), (1024, 768), (1440, 900)]
PANELS = ("discovery", "requirements", "architecture", "engineering",
          "testing", "deployment", "handover", "outcomes")


def bounded(page, selector, width):
    bounds = page.locator(selector).first.bounding_box()
    assert bounds, f"{selector} not visible"
    assert bounds["width"] > 0, f"{selector} zero-width"
    assert bounds["x"] >= -2, f"{selector} outside left edge: {bounds}"
    assert bounds["x"] + bounds["width"] <= width + 2, (
        f"{selector} clipped at {width}px: {bounds}"
    )


def inspect_page(browser, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1,
        reduced_motion="reduce",
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(BASE + "/fde-implementation.html",
              wait_until="domcontentloaded", timeout=30000)
    page.locator(".hero-main h1").wait_for()
    page.locator(".hero-plate svg").wait_for()
    assert "From business problem to working deployment." in page.locator("h1").inner_text()
    assert page.locator("[role=tab]").count() == 8
    assert page.locator("[role=tabpanel]").count() == 8
    assert page.locator("svg #plate-title").inner_text() == "FrameOps assembly drawing"

    client = page.evaluate("document.documentElement.clientWidth")
    scroll = page.evaluate("document.documentElement.scrollWidth")
    assert scroll <= client + 2, f"document overflow at {width}px: {scroll}>{client}"
    for selector in [".hero-main", ".hero-side", ".hero-plate", ".summary",
                     ".tabs", ".section-heading"]:
        bounded(page, selector, client)

    assert page.locator("#discovery").is_visible()
    assert not page.locator("#engineering").is_visible()
    assert page.locator('.tab[aria-selected="true"]').count() == 1
    assert page.locator(".site-header").evaluate(
        "(el) => getComputedStyle(el).backgroundColor"
    ) == "rgb(30, 57, 49)", "custom evergreen palette not applied"

    # Verify actual tab behavior across all panels without changing app data.
    for panel in PANELS:
        page.locator(f'.tab[data-target="{panel}"]').click()
        assert page.locator("#" + panel).is_visible(), f"{panel} not shown at {width}px"
        assert page.locator('.tab[aria-selected="true"]').get_attribute("data-target") == panel

    # Keyboard interactions remain intact.
    page.locator('.tab[data-target="engineering"]').focus()
    page.keyboard.press("ArrowRight")
    assert page.locator("#testing").is_visible(), "ArrowRight should select Testing"

    # Read-only integration checks through live local endpoints, not mocked data.
    page.locator('.tab[data-target="engineering"]').click()
    page.locator('[data-probe="health"]').click()
    output = page.locator("#probe-output")
    output.wait_for()
    assert '"http_status": 200' in output.inner_text(), output.inner_text()
    assert '"service_status": "ok"' in output.inner_text(), output.inner_text()

    page.locator('[data-probe="missing"]').click()
    assert '"http_status": 404' in output.inner_text(), output.inner_text()
    assert "Job not found" in output.inner_text(), output.inner_text()

    page.locator('[data-probe="bootstrap"]').click()
    result = json.loads(output.inner_text())
    assert result["http_status"] == 200, result
    assert result["jobs"] >= 1 and result["workflow_stages"] >= 1, result
    assert "homeowner" not in result and "address" not in result, (
        "Inspector exposed personal record details"
    )

    if width in (320, 390, 768, 1440):
        page.screenshot(path=str(OUTPUT / f"fde-engineering-{width}.png"),
                        full_page=False)
        page.locator('.tab[data-target="discovery"]').click()
        page.screenshot(path=str(OUTPUT / f"fde-home-{width}.png"),
                        full_page=True)
    assert not errors, f"JavaScript exceptions at {width}px: {errors}"
    context.close()
    print(f"PASS FDE: {width}x{height}; no overflow; tabs, keyboard, real GET probes, custom theme")


def main():
    with tempfile.TemporaryDirectory(prefix="frameops-fde-mobile-") as temp:
        env = os.environ.copy()
        env.update({"PUBLIC_DEMO": "1", "PORT": "18994",
                    "DB_PATH": str(Path(temp) / "frameops.db"),
                    "UPLOAD_DIR": str(Path(temp) / "uploads")})
        process = subprocess.Popen(
            [sys.executable, "server.py"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(50):
                if process.poll() is not None:
                    raise RuntimeError(f"server exited early with {process.returncode}")
                try:
                    with urlopen(BASE + "/health", timeout=2) as resp:
                        if resp.status == 200:
                            break
                except Exception:
                    time.sleep(.5)
            else:
                raise RuntimeError("FDE isolated server failed to respond")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    for width, height in WIDTHS:
                        inspect_page(browser, width, height)
                finally:
                    browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
