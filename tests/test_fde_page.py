"""Regression checks for the additive FrameOps FDE portfolio walkthrough."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "public" / "fde-implementation.html"
INDEX = ROOT / "public" / "index.html"
SECTIONS = (
    "discovery", "requirements", "architecture", "engineering",
    "testing", "deployment", "handover", "outcomes",
)


class EvidenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tabs = []
        self.panels = []
        self.probes = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "button" and props.get("role") == "tab":
            self.tabs.append((props.get("data-target"), props.get("aria-controls")))
        if tag == "section" and props.get("role") == "tabpanel":
            self.panels.append(props.get("id"))
        if tag == "button" and props.get("data-probe"):
            self.probes.append(props["data-probe"])
        if tag == "a":
            self.links.append(props.get("href", ""))


class FDEPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.parser = EvidenceParser()
        cls.parser.feed(cls.page)

    def test_all_eight_evidence_areas_have_tab_to_panel_links(self):
        self.assertEqual(len(self.parser.tabs), 8)
        self.assertEqual(self.parser.panels, list(SECTIONS))
        self.assertEqual(self.parser.tabs, [(name, name) for name in SECTIONS])

    def test_safe_read_only_api_evidence(self):
        self.assertEqual(
            set(self.parser.probes),
            {"health", "bootstrap", "dashboard", "missing"},
        )
        self.assertIn("method:'GET'", self.page)
        self.assertIn("cache:'no-store'", self.page)
        self.assertNotIn("method:'POST'", self.page)
        self.assertNotIn("data-action=", self.page)

    def test_existing_application_menu_links_to_evidence(self):
        self.assertIn('href="/fde-implementation.html"', self.index)
        self.assertIn('href="/qa-bench.html"', self.index)
        self.assertIn('target="_blank"', self.index)

    def test_expected_source_artifacts_resolve(self):
        for name in (
            "CASE_STUDY.md", "DESIGN.md", "OPERATING_GUIDE.md",
            "PRODUCTION_READINESS.md", "TESTING.md", "RENDER_SETUP.md",
            "render.yaml", "server.py", "operations.py",
            ".github/workflows/test.yml",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())
        for path in ("CASE_STUDY.md", "DESIGN.md", "OPERATING_GUIDE.md",
                     "PRODUCTION_READINESS.md", "TESTING.md", "RENDER_SETUP.md"):
            with self.subTest(link=path):
                self.assertIn("/blob/main/" + path, self.page)

    def test_no_fake_realtime_outcome_or_payment_integration(self):
        self.assertIn("No improvement percentages are invented", self.page)
        self.assertIn("not connected", self.page)
        self.assertIn("fictional", self.page.lower())
        self.assertIn("not authentication", self.page)
        self.assertNotIn("100% production-ready", self.page)

    def test_mobile_and_keyboard_support(self):
        self.assertIn('name="viewport"', self.page)
        self.assertIn("@media(max-width:600px)", self.page)
        self.assertIn("ArrowRight", self.page)
        self.assertIn("aria-selected", self.page)
        self.assertIn("aria-live", self.page)


if __name__ == "__main__":
    unittest.main()
