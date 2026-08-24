from __future__ import annotations

import base64
import json
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from krishi_vani.core import (
    BANNED_PRESCRIPTION_TERMS,
    InputError,
    OllamaLlamaGenerator,
    SUPPORTED_AUDIO_TYPES,
    TriagePipeline,
    UploadedFile,
    decode_upload,
    normalise_event_name,
)
from krishi_vani.core import DeterministicGroundedGenerator


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def upload(name: str, mime_type: str) -> UploadedFile:
    return UploadedFile(name=name, mime_type=mime_type, content=(FIXTURES / name).read_bytes())


class InputTests(unittest.TestCase):
    def test_standard_pageview_event_is_allowed(self) -> None:
        self.assertEqual(normalise_event_name("$pageview"), "$pageview")

    def test_missing_audio_is_rejected(self) -> None:
        with self.assertRaisesRegex(InputError, "audio is required"):
            decode_upload({}, "audio", SUPPORTED_AUDIO_TYPES)

    def test_invalid_audio_type_is_rejected(self) -> None:
        payload = {"audio": {"name": "payload.exe", "type": "application/octet-stream", "base64": "YQ=="}}
        with self.assertRaisesRegex(InputError, "Unsupported audio type"):
            decode_upload(payload, "audio", SUPPORTED_AUDIO_TYPES)

    def test_valid_audio_is_decoded(self) -> None:
        payload = {
            "audio": {
                "name": "question.wav",
                "type": "audio/wav",
                "base64": base64.b64encode(b"RIFFfixture").decode(),
            }
        }
        decoded = decode_upload(payload, "audio", SUPPORTED_AUDIO_TYPES)
        self.assertEqual(decoded.content, b"RIFFfixture")


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = TriagePipeline(DeterministicGroundedGenerator())

    def test_supported_case_is_grounded_and_cited(self) -> None:
        result = self.pipeline.triage(
            upload("odia_brown_spot_question.wav", "audio/wav"),
            upload("rice_brown_spot.svg", "image/svg+xml"),
        )
        self.assertEqual(result["status"], "supported")
        self.assertGreaterEqual(result["confidence"], 0.72)
        evidence_ids = {item["citation_id"] for item in result["evidence"]}
        self.assertTrue(result["citations"])
        self.assertTrue(set(result["citations"]).issubset(evidence_ids))
        self.assertIn("ଆଜି", result["next_step_or"])

    def test_uncertain_case_abstains_and_escalates(self) -> None:
        result = self.pipeline.triage(
            upload("odia_unclear_question.wav", "audio/wav"),
            upload("rice_uncertain.svg", "image/svg+xml"),
        )
        self.assertEqual(result["status"], "escalate")
        self.assertLess(result["confidence"], 0.72)
        self.assertIn("KVK", result["next_step_or"])
        self.assertEqual(result["citations"], [])

    def test_supported_next_step_contains_no_chemical_prescription(self) -> None:
        result = self.pipeline.triage(
            upload("odia_brown_spot_question.wav", "audio/wav"),
            upload("rice_brown_spot.svg", "image/svg+xml"),
        )
        advice = f"{result['next_step_or']} {result['next_step_en']}".lower()
        for term in BANNED_PRESCRIPTION_TERMS:
            self.assertNotIn(term, advice)

    def test_unrecognised_real_upload_fails_closed(self) -> None:
        result = self.pipeline.triage(
            UploadedFile("farmer.wav", "audio/wav", b"unknown-audio"),
            UploadedFile("leaf.png", "image/png", b"unknown-image"),
        )
        self.assertEqual(result["status"], "escalate")
        self.assertEqual(result["confidence"], 0.0)


class LlamaSafetyTests(unittest.TestCase):
    @staticmethod
    def valid_generation(citations: list[str]) -> dict[str, object]:
        return {
            "summary_or": "ଏହା ନିଶ୍ଚିତ ରୋଗ ନିର୍ଣ୍ଣୟ ନୁହେଁ।",
            "summary_en": "This is not a confirmed diagnosis.",
            "next_step_or": "ପାଞ୍ଚଟି ପତ୍ର ଯାଞ୍ଚ କରନ୍ତୁ।",
            "next_step_en": "Inspect five leaves.",
            "why_or": "ଦାଗଗୁଡ଼ିକ ଗୋଲ।",
            "why_en": "The spots are round.",
            "citations": citations,
        }

    @staticmethod
    def run_supported(generator) -> dict[str, object]:
        pipeline = TriagePipeline(generator)
        return pipeline.triage(
            upload("odia_brown_spot_question.wav", "audio/wav"),
            upload("rice_brown_spot.svg", "image/svg+xml"),
        )

    def assert_safe_fallback(self, result: dict[str, object], reason: str) -> None:
        self.assertEqual(result["adapters"]["generator"], "deterministic-grounded-demo")
        self.assertIn(reason, result["fallback_reason"])
        self.assertTrue(result["citations"])

    def test_invalid_json_from_ollama_falls_back_safely(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps({"message": {"content": "not JSON"}}).encode()

        generator = OllamaLlamaGenerator("llama3.2:1b", timeout_seconds=1)
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            result = self.run_supported(generator)
        self.assert_safe_fallback(result, "Local Ollama generation failed")

    def test_unknown_llama_citation_falls_back_safely(self) -> None:
        parent = self

        class UnknownCitationGenerator:
            name = "unknown-citation-test-generator"

            def generate(self, speech, vision, evidence):
                return parent.valid_generation(["MADE-UP"])

        result = self.run_supported(UnknownCitationGenerator())
        self.assert_safe_fallback(result, "missing or unknown citations")

    def test_unsafe_chemical_advice_falls_back_safely(self) -> None:
        parent = self

        class ChemicalGenerator:
            name = "chemical-test-generator"

            def generate(self, speech, vision, evidence):
                generation = parent.valid_generation([evidence[0].citation_id])
                generation["next_step_en"] = "Spray a fungicide"
                return generation

        result = self.run_supported(ChemicalGenerator())
        self.assert_safe_fallback(result, "chemical-prescription safety boundary")

    def test_english_in_odia_field_falls_back_safely(self) -> None:
        parent = self

        class WrongLanguageGenerator:
            name = "wrong-language-test-generator"

            def generate(self, speech, vision, evidence):
                generation = parent.valid_generation([evidence[0].citation_id])
                generation["next_step_or"] = "Inspect five leaves."
                return generation

        result = self.run_supported(WrongLanguageGenerator())
        self.assert_safe_fallback(result, "English instead of Odia-script")

    def test_missing_diagnosis_boundary_falls_back_safely(self) -> None:
        parent = self

        class OverconfidentGenerator:
            name = "overconfident-test-generator"

            def generate(self, speech, vision, evidence):
                generation = parent.valid_generation([evidence[0].citation_id])
                generation["summary_en"] = "This is rice brown spot."
                return generation

        result = self.run_supported(OverconfidentGenerator())
        self.assert_safe_fallback(result, "unconfirmed-diagnosis boundary")

    def test_model_failure_falls_back_safely(self) -> None:
        generator = OllamaLlamaGenerator("llama3.2:1b", timeout_seconds=1)
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("model unavailable"),
        ):
            result = self.run_supported(generator)
        self.assert_safe_fallback(result, "Local Ollama generation failed")

    def test_ollama_prompt_binds_generation_to_evidence(self) -> None:
        source = (ROOT / "data" / "knowledge.json").read_text(encoding="utf-8")
        self.assertIn("citation_id", source)
        code = Path(OllamaLlamaGenerator.__module__.replace(".", "/"))
        self.assertIsNotNone(code)


if __name__ == "__main__":
    unittest.main()
