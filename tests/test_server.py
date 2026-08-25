from __future__ import annotations

import base64
import http.client
import json
import re
import threading
import unittest
from pathlib import Path

from krishi_vani.server import EVENTS, EVENTS_LOCK, make_server


ROOT = Path(__file__).resolve().parents[1]
PROJECT_TITLE = "Krishi-Vani AI: Open-source rice-triage prototype for Odia farmers"
PROJECT_DESCRIPTION = (
    "Krishi-Vani AI is an open-source rice-triage challenge prototype for Odia-speaking "
    "farmers that uses two labelled audio-and-leaf fixture pairs to demonstrate one cited "
    "non-chemical next step or a KVK/extension escalation."
)
PROJECT_LEGAL_STATUS = (
    "Krishi-Vani AI is an open-source project; no separate incorporated legal entity is published."
)


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

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        body = json.dumps(payload).encode() if payload is not None else None
        request_headers = dict(headers or {})
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=request_headers)
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
        status, content_type, data = self.request(
            "GET",
            "/",
            headers={"Host": "krishi-vani.example", "X-Forwarded-Proto": "https"},
        )
        page = data.decode()
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn('lang="or"', page)
        self.assertEqual(page.count('class="primary-action"'), 1)
        self.assertIn('href="mailto:unleashllm@mail.tin.computer"', page)
        self.assertIn("Farmer media is not interpreted yet", page)
        self.assertNotIn('type="file"', page)
        self.assertIn('<meta name="robots" content="index, follow">', page)
        self.assertIn(f"<title>{PROJECT_TITLE}</title>", page)
        self.assertIn(f'<meta name="description" content="{PROJECT_DESCRIPTION}">', page)
        self.assertIn('<link rel="canonical" href="https://krishi-vani.example/">', page)
        self.assertNotIn("__CANONICAL_URL__", page)
        self.assertNotIn("__STRUCTURED_DATA__", page)

    def test_result_has_one_compact_feedback_prompt(self) -> None:
        status, _, data = self.request("GET", "/")
        page = data.decode()
        self.assertEqual(status, 200)
        self.assertEqual(page.count('id="feedback-prompt"'), 1)
        self.assertEqual(page.count('data-rating="thumbs_up"'), 1)
        self.assertEqual(page.count('data-rating="thumbs_down"'), 1)
        self.assertIn('id="feedback-form" hidden', page)
        self.assertIn('class="ph-mask" maxlength="280"', page)

    def test_homepage_structured_data_is_valid_and_matches_visible_copy(self) -> None:
        status, _, data = self.request(
            "GET",
            "/",
            headers={"Host": "krishi-vani.example", "X-Forwarded-Proto": "https"},
        )
        page = data.decode()
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            page,
            flags=re.DOTALL,
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(match)
        structured_data = json.loads(match.group(1))
        self.assertEqual(structured_data["@context"], "https://schema.org")
        entities = {entity["@type"]: entity for entity in structured_data["@graph"]}
        self.assertEqual(
            set(entities),
            {"SoftwareApplication", "SoftwareSourceCode", "FAQPage"},
        )
        self.assertEqual(entities["SoftwareApplication"]["description"], PROJECT_DESCRIPTION)
        self.assertEqual(entities["SoftwareApplication"]["dateCreated"], "2026-08-24")
        self.assertEqual(
            entities["SoftwareApplication"]["disambiguatingDescription"],
            PROJECT_LEGAL_STATUS,
        )
        self.assertEqual(
            entities["SoftwareApplication"]["sameAs"],
            ["https://github.com/iamaanahmad/Krishi-Vani-AI"],
        )
        self.assertEqual(
            entities["SoftwareSourceCode"]["codeRepository"],
            "https://github.com/iamaanahmad/Krishi-Vani-AI",
        )
        self.assertNotIn("offers", entities["SoftwareApplication"])
        self.assertNotIn("aggregateRating", entities["SoftwareApplication"])
        for question in entities["FAQPage"]["mainEntity"]:
            self.assertIn(question["name"], page)
            self.assertIn(question["acceptedAnswer"]["text"], page)

    def test_open_source_proof_page_is_indexable_and_honest(self) -> None:
        status, content_type, data = self.request(
            "GET",
            "/open-source-agriculture-ai/",
            headers={"Host": "krishi-vani.example", "X-Forwarded-Proto": "https"},
        )
        page = data.decode()
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(f"<title>{PROJECT_TITLE}</title>", page)
        self.assertIn(f'<meta name="description" content="{PROJECT_DESCRIPTION}">', page)
        self.assertIn(
            '<link rel="canonical" href="https://krishi-vani.example/open-source-agriculture-ai/">',
            page,
        )
        self.assertIn("interpretation of arbitrary farmer speech or photos", page)
        self.assertIn("does not prove", page)
        self.assertIn("24 August 2026, based on the first repository commit.", page)
        self.assertIn(PROJECT_LEGAL_STATUS, page)
        self.assertIn('href="/">Run the labelled demo</a>', page)
        self.assertNotIn("__CANONICAL_URL__", page)
        self.assertNotIn("__STRUCTURED_DATA__", page)

        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            page,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        structured_data = json.loads(match.group(1))
        self.assertEqual(structured_data["@type"], "TechArticle")
        self.assertEqual(
            structured_data["url"],
            "https://krishi-vani.example/open-source-agriculture-ai/",
        )
        self.assertEqual(structured_data["headline"], PROJECT_TITLE)
        self.assertEqual(structured_data["description"], PROJECT_DESCRIPTION)
        self.assertEqual(structured_data["dateCreated"], "2026-08-24")
        self.assertEqual(structured_data["disambiguatingDescription"], PROJECT_LEGAL_STATUS)

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
        for event_name in ("$pageview", "demo_loaded", "triage_submitted", "triage_completed", "triage_failed"):
            self.assertIn(event_name, script)
        self.assertIn("$process_person_profile: false", script)
        self.assertIn("eventProperties.is_e2e_test = true", script)
        self.assertIn("eventProperties.e2e_run = state.e2eRun", script)

    def test_client_analytics_covers_first_contact_and_masks_replay(self) -> None:
        status, _, data = self.request("GET", "/app.js")
        script = data.decode()
        self.assertEqual(status, 200)
        for event_name in ("value_reached", "error_shown", "empty_state_shown", "feedback_submitted"):
            self.assertIn(event_name, script)
        self.assertIn('person_profiles: "identified_only"', script)
        self.assertIn("maskAllInputs: true", script)
        self.assertIn('maskTextSelector: ".ph-mask"', script)
        self.assertIn('blockSelector: "audio, video, canvas, .ph-no-capture"', script)
        self.assertIn("capture_performance: false", script)
        self.assertIn("enable_recording_console_log: false", script)
        self.assertIn("disable_session_recording: false", script)
        self.assertIn("rageclick: true", script)
        self.assertIn("capture_dead_clicks: true", script)
        self.assertNotIn(".identify(", script)

    def test_client_analytics_classifies_ai_referrers_without_raw_attribution(self) -> None:
        status, _, data = self.request("GET", "/app.js")
        script = data.decode()
        self.assertEqual(status, 200)
        for host in (
            "chatgpt.com",
            "chat.openai.com",
            "openai.com",
            "claude.ai",
            "perplexity.ai",
            "gemini.google.com",
            "copilot.microsoft.com",
        ):
            self.assertIn(f'"{host}"', script)
        self.assertIn('return "ai_assistant"', script)
        self.assertIn('"$pageview": ["referrer_channel"]', script)
        self.assertIn('demo_loaded: ["referrer_channel"]', script)
        self.assertIn('value_reached: ["outcome", "referrer_channel"]', script)
        self.assertIn("localStorage.getItem(FIRST_REFERRER_CHANNEL_KEY)", script)
        self.assertIn("localStorage.setItem(FIRST_REFERRER_CHANNEL_KEY", script)
        self.assertNotIn("ai_prompt_text", script)
        self.assertNotIn("signup_source", script)

    def test_feedback_behavior_caps_comment_and_submits_once(self) -> None:
        status, _, data = self.request("GET", "/app.js")
        script = data.decode()
        self.assertEqual(status, 200)
        self.assertIn('.value.trim().slice(0, 280)', script)
        self.assertIn('document.querySelector("#feedback-form").hidden = false', script)
        self.assertIn('document.querySelector("#feedback-form").hidden = true', script)
        self.assertIn("button.disabled = true", script)
        self.assertIn('document.querySelector("#feedback-thanks").hidden = false', script)

    def test_discovery_files_use_request_origin(self) -> None:
        headers = {"Host": "krishi-vani.example", "X-Forwarded-Proto": "https"}
        status, content_type, data = self.request("GET", "/robots.txt", headers=headers)
        self.assertEqual(status, 200)
        self.assertIn("text/plain", content_type)
        self.assertEqual(
            data.decode(),
            "User-agent: *\nAllow: /\nDisallow: /api/\n"
            "Sitemap: https://krishi-vani.example/sitemap.xml\n",
        )

        status, content_type, data = self.request("GET", "/sitemap.xml", headers=headers)
        self.assertEqual(status, 200)
        self.assertIn("application/xml", content_type)
        self.assertIn("<loc>https://krishi-vani.example/</loc>", data.decode())
        self.assertIn(
            "<loc>https://krishi-vani.example/open-source-agriculture-ai/</loc>",
            data.decode(),
        )

        status, content_type, data = self.request("GET", "/llms.txt", headers=headers)
        self.assertEqual(status, 200)
        self.assertIn("text/plain", content_type)
        llms_text = data.decode()
        self.assertIn(PROJECT_DESCRIPTION, llms_text)
        self.assertIn("Founded: 24 August 2026", llms_text)
        self.assertIn(PROJECT_LEGAL_STATUS, llms_text)
        self.assertIn("Canonical demo: https://krishi-vani.example/", llms_text)
        self.assertIn("https://github.com/iamaanahmad/Krishi-Vani-AI", llms_text)
        self.assertIn("Does not interpret arbitrary farmer recordings or photographs", llms_text)

    def test_api_responses_are_not_indexable(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request("GET", "/api/health")
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.getheader("X-Robots-Tag"), "noindex, nofollow")
        connection.close()

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
            {
                "event": "triage_completed",
                "is_e2e_test": True,
                "e2e_run": run,
                "properties": {"route": "/", "outcome": "supported"},
            },
        )
        self.assertEqual(status, 202)
        status, _, data = self.request("GET", f"/api/events?run={run}")
        events = json.loads(data)["events"]
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["is_e2e_test"])
        self.assertEqual(events[0]["properties"], {"route": "/", "outcome": "supported"})

    def test_feedback_event_keeps_only_deliberate_approved_fields(self) -> None:
        with EVENTS_LOCK:
            EVENTS.clear()
        status, _, _ = self.request(
            "POST",
            "/api/events",
            {
                "event": "feedback_submitted",
                "properties": {
                    "route": "/",
                    "rating": "thumbs_down",
                    "feedback": "x" * 320,
                    "transcript": "private transcript",
                    "image": "private crop",
                    "identity": "farmer@example.com",
                },
            },
        )
        self.assertEqual(status, 202)
        with EVENTS_LOCK:
            properties = EVENTS[-1]["properties"]
        self.assertEqual(set(properties), {"route", "rating", "feedback"})
        self.assertEqual(len(properties["feedback"]), 280)

    def test_referrer_channel_is_coarse_and_limited_to_load_and_value_events(self) -> None:
        with EVENTS_LOCK:
            EVENTS.clear()
        for event, extra in (
            ("$pageview", {}),
            ("demo_loaded", {}),
            ("value_reached", {"outcome": "supported"}),
        ):
            status, _, _ = self.request(
                "POST",
                "/api/events",
                {
                    "event": event,
                    "properties": {
                        "route": "/",
                        "referrer_channel": "ai_assistant",
                        "referrer": "https://chatgpt.com/private/path?prompt=private",
                        "utm_source": "chatgpt.com",
                        **extra,
                    },
                },
            )
            self.assertEqual(status, 202)

        status, _, _ = self.request(
            "POST",
            "/api/events",
            {
                "event": "triage_completed",
                "properties": {
                    "route": "/",
                    "outcome": "supported",
                    "referrer_channel": "ai_assistant",
                },
            },
        )
        self.assertEqual(status, 202)

        with EVENTS_LOCK:
            events = list(EVENTS)
        for event in events[:3]:
            self.assertEqual(event["properties"]["referrer_channel"], "ai_assistant")
            self.assertNotIn("referrer", event["properties"])
            self.assertNotIn("utm_source", event["properties"])
        self.assertNotIn("referrer_channel", events[3]["properties"])

    def test_referrer_channel_rejects_raw_or_unknown_values(self) -> None:
        with EVENTS_LOCK:
            EVENTS.clear()
        status, _, _ = self.request(
            "POST",
            "/api/events",
            {
                "event": "demo_loaded",
                "properties": {
                    "route": "/",
                    "referrer_channel": "https://chatgpt.com/?prompt=private",
                },
            },
        )
        self.assertEqual(status, 202)
        with EVENTS_LOCK:
            properties = EVENTS[-1]["properties"]
        self.assertEqual(properties, {"route": "/"})

    def test_unapproved_event_is_rejected(self) -> None:
        status, _, data = self.request(
            "POST", "/api/events", {"event": "crop_uploaded", "properties": {"route": "/"}}
        )
        self.assertEqual(status, 400)
        self.assertIn("not approved", json.loads(data)["error"])


if __name__ == "__main__":
    unittest.main()
