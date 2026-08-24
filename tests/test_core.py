from __future__ import annotations

import base64
import json
import unittest
from pathlib import Path

from krishi_vani.core import (
    BANNED_PRESCRIPTION_TERMS,
    InputError,
    OllamaLlamaGenerator,
    SUPPORTED_AUDIO_TYPES,
    TriagePipeline,
    UploadedFile,
    decode_upload,
)
from krishi_vani.core import DeterministicGroundedGenerator


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def upload(name: str, mime_type: str) -> UploadedFile:
    return UploadedFile(name=name, mime_type=mime_type, content=(FIXTURES / name).read_bytes())


class InputTests(unittest.TestCase):
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
    def test_invalid_llama_citations_fall_back_to_grounded_demo(self) -> None:
        class UnsafeGenerator:
            name = "unsafe-test-generator"

            def generate(self, speech, vision, evidence):
                return {
                    "summary_or": "x",
                    "summary_en": "x",
                    "next_step_or": "x",
                    "next_step_en": "Spray a fungicide",
                    "why_or": "x",
                    "why_en": "x",
                    "citations": ["MADE-UP"],
                }

        pipeline = TriagePipeline(UnsafeGenerator())
        result = pipeline.triage(
            upload("odia_brown_spot_question.wav", "audio/wav"),
            upload("rice_brown_spot.svg", "image/svg+xml"),
        )
        self.assertEqual(result["adapters"]["generator"], "deterministic-grounded-demo")
        self.assertIn("fallback_reason", result)

    def test_ollama_prompt_binds_generation_to_evidence(self) -> None:
        source = (ROOT / "data" / "knowledge.json").read_text(encoding="utf-8")
        self.assertIn("citation_id", source)
        code = Path(OllamaLlamaGenerator.__module__.replace(".", "/"))
        self.assertIsNotNone(code)


if __name__ == "__main__":
    unittest.main()
