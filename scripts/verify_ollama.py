#!/usr/bin/env python3
"""Run the two committed scenarios through a real local Ollama model."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from krishi_vani.core import (
    ABSTAIN_THRESHOLD,
    BANNED_PRESCRIPTION_TERMS,
    DEFAULT_OLLAMA_MODEL,
    OllamaLlamaGenerator,
    TriagePipeline,
    UploadedFile,
)


FIXTURES = ROOT / "fixtures"


def upload(name: str, mime_type: str) -> UploadedFile:
    return UploadedFile(name, mime_type, (FIXTURES / name).read_bytes())


def run_scenario(
    pipeline: TriagePipeline,
    audio_name: str,
    image_name: str,
) -> tuple[dict[str, object], float]:
    started = time.monotonic()
    result = pipeline.triage(
        upload(audio_name, "audio/wav"),
        upload(image_name, "image/svg+xml"),
    )
    return result, round(time.monotonic() - started, 3)


def concise_result(result: dict[str, object], latency: float) -> dict[str, object]:
    return {
        "latency_seconds": latency,
        "status": result["status"],
        "confidence": result["confidence"],
        "generator": result["adapters"]["generator"],  # type: ignore[index]
        "citations": result["citations"],
        "next_step_or": result["next_step_or"],
        "next_step_en": result["next_step_en"],
        "fallback_reason": result.get("fallback_reason"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Krishi-Vani's real local Ollama path and abstention boundary"
    )
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    generator = OllamaLlamaGenerator(
        args.model,
        base_url=args.base_url,
        timeout_seconds=args.timeout,
    )
    pipeline = TriagePipeline(generator)

    supported, supported_latency = run_scenario(
        pipeline,
        "odia_brown_spot_question.wav",
        "rice_brown_spot.svg",
    )
    uncertain, uncertain_latency = run_scenario(
        pipeline,
        "odia_unclear_question.wav",
        "rice_uncertain.svg",
    )

    evidence_ids = {item["citation_id"] for item in supported["evidence"]}
    advice = json.dumps(
        [supported["next_step_or"], supported["next_step_en"]],
        ensure_ascii=False,
    ).lower()
    checks = {
        "real_model_generated_supported_answer": (
            supported["adapters"]["generator"] == generator.name  # type: ignore[index]
            and "fallback_reason" not in supported
        ),
        "supported_answer_is_cited": (
            bool(supported["citations"])
            and set(supported["citations"]).issubset(evidence_ids)
        ),
        "supported_advice_has_no_banned_chemical_terms": not any(
            term in advice for term in BANNED_PRESCRIPTION_TERMS
        ),
        "uncertain_case_abstained_before_generation": (
            uncertain["status"] == "escalate"
            and uncertain["confidence"] < ABSTAIN_THRESHOLD
            and uncertain["citations"] == []
            and uncertain["adapters"]["generator"] == "not-run"  # type: ignore[index]
        ),
    }
    report = {
        "model": args.model,
        "base_url": args.base_url,
        "supported": concise_result(supported, supported_latency),
        "uncertain": concise_result(uncertain, uncertain_latency),
        "checks": checks,
        "passed": all(checks.values()),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
