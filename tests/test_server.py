from __future__ import annotations

import base64
import http.client
import json
import threading
import unittest
from pathlib import Path

from krishi_vani.server import EVENTS, EVENTS_LOCK, make_server


ROOT = Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = make_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method: str, path: str, payload: dict | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, response.getheader("Content-Type"), data

    def encoded_file(self, name: str, mime_type: str) -> dict[str, str]:
        return {
            "name": name,
            "type": mime_type,
            "base64": base64.b64encode((ROOT / "fixtures" / name).read_bytes()).decode(),
        }

    def test_health_endpoint(self) -> None:
        status, _, data = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["status"], "ok")

    def test_homepage_has_odia_and_single_primary_action(self) -> None:
        status, content_type, data = self.request("GET", "/")
        page = data.decode()
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn('lang="or"', page)
        self.assertEqual(page.count('class="primary-action"'), 1)
        self.assertIn('href="mailto:unleashllm@mail.tin.computer"', page)
        self.assertIn("Farmer media is not interpreted yet", page)
        self.assertNotIn('type="file"', page)

    def test_result_ui_does_not_present_fixture_score_as_accuracy(self) -> None:
        status, _, data = self.request("GET", "/app.js")
        script = data.decode()
        self.assertEqual(status, 200)
        self.assertIn('"Passed" : "Stopped"', script)
        self.assertNotIn("Math.round(result.confidence", script)
        self.assertIn('document.querySelector("#result-region").hidden = true', script)

    def test_client_analytics_has_small_activation_funnel(self) -> None:
        status, content_type, data = self.request("GET", "/app.js")
        script = data.decode()
        self.assertEqual(status, 200)
        self.assertIn("javascript", content_type)
        self.assertIn("/capture/", script)
        for event_name in ("demo_loaded", "triage_submitted", "triage_completed", "triage_failed"):
            self.assertIn(f'track("{event_name}"', script)

    def test_supported_api_case(self) -> None:
        status, _, data = self.request(
            "POST",
            "/api/triage",
            {
                "audio": self.encoded_file("odia_brown_spot_question.wav", "audio/wav"),
                "image": self.encoded_file("rice_brown_spot.svg", "image/svg+xml"),
            },
        )
        result = json.loads(data)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "supported")
        self.assertTrue(result["citations"])

    def test_missing_inputs_return_400(self) -> None:
        status, _, data = self.request("POST", "/api/triage", {})
        self.assertEqual(status, 400)
        self.assertIn("audio is required", json.loads(data)["error"])

    def test_e2e_events_can_be_read_back(self) -> None:
        run = "unit-e2e-run"
        with EVENTS_LOCK:
            EVENTS.clear()
        status, _, _ = self.request(
            "POST",
            "/api/events",
            {"event": "triage_completed", "is_e2e_test": True, "e2e_run": run, "status": "supported"},
        )
        self.assertEqual(status, 202)
        status, _, data = self.request("GET", f"/api/events?run={run}")
        events = json.loads(data)["events"]
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["is_e2e_test"])


if __name__ == "__main__":
    unittest.main()
