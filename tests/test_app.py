"""HTTP integration smoke tests for the FrameOps fictional-data public demo."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class FrameOpsHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="frameops-tests-")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = dict(os.environ, PORT=str(cls.port), PUBLIC_DEMO="1", QUIET="1",
                   DB_PATH=str(Path(cls.temp.name) / "test.db"),
                   UPLOAD_DIR=str(Path(cls.temp.name) / "uploads"))
        cls.proc = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(100):
            if cls.proc.poll() is not None:
                raise RuntimeError("FrameOps server stopped before startup")
            try:
                with urlopen(cls.base + "/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except (URLError, OSError):
                time.sleep(0.05)
        else:
            raise RuntimeError("FrameOps server did not become healthy")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait(timeout=5)
        cls.proc.stderr.close()
        cls.temp.cleanup()

    def request(self, path, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        request = Request(self.base + path, data=payload,
                          headers={"Content-Type": "application/json"} if data is not None else {})
        try:
            with urlopen(request, timeout=3) as response:
                body = response.read()
                return response.status, json.loads(body) if response.headers.get_content_type() == "application/json" else body
        except HTTPError as exc:
            body = exc.read()
            return exc.code, json.loads(body)

    def test_static_assets_and_health(self):
        code, body = self.request("/health")
        self.assertEqual((code, body["status"]), (200, "ok"))
        for path in ("/", "/app.js", "/styles.css"):
            code, body = self.request(path)
            self.assertEqual(code, 200, path)
            self.assertGreater(len(body), 100, path)

    def test_bootstrap_has_fictional_data_and_roles(self):
        code, data = self.request("/api/bootstrap")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(data["jobs"]), 8)
        self.assertIn("Installation Manager", data["roles"])
        self.assertIn("Homeowner", data["roles"])

    def test_create_lead_handoff_and_role_blockers(self):
        code, data = self.request("/api/jobs", {"homeowner": "Test Customer", "address": "Demo House"})
        self.assertEqual(code, 201)
        jid = data["id"]
        code, detail = self.request(f"/api/jobs/{jid}")
        self.assertEqual(code, 200)
        self.assertEqual(detail["stage"], "New Lead")
        self.assertTrue(any(t["code"] == "qualify" for t in detail["tasks"]))
        code, denied = self.request(f"/api/jobs/{jid}/action", {"action": "qualify", "actor": "Vendor"})
        self.assertEqual(code, 400)
        self.assertIn("cannot perform", denied["error"])
        code, response = self.request(f"/api/jobs/{jid}/action", {"action": "qualify", "actor": "Front Desk"})
        self.assertEqual(code, 200)
        code, detail = self.request(f"/api/jobs/{jid}")
        self.assertEqual(detail["stage"], "Qualified")
        self.assertTrue(any(t["code"] == "schedule_measurement" for t in detail["tasks"]))
        self.assertGreaterEqual(len(detail["events"]), 2)
        code, denied = self.request(f"/api/jobs/{jid}/action", {"action": "place_order", "actor": "Installation Manager"})
        self.assertEqual(code, 400)
        self.assertTrue(denied["error"])

    def test_public_demo_rejects_uploads_and_invalid_leads(self):
        code, err = self.request("/api/jobs", {"homeowner": "No Address"})
        self.assertEqual(code, 400)
        self.assertIn("address", err["error"].lower())
        code, err = self.request("/api/jobs/F-1001/upload", {"name": "private.pdf", "base64": "dGVzdA=="})
        self.assertEqual(code, 400)
        self.assertIn("disabled", err["error"].lower())

    def test_unknown_routes_do_not_expose_files(self):
        for path in ("/../server.py", "/unlisted-page", "/api/jobs/F-999999"):
            code, _ = self.request(path)
            self.assertEqual(code, 404, path)


if __name__ == "__main__":
    unittest.main()
