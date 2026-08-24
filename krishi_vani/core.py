from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"

MAX_FILE_BYTES = 8 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {"audio/wav", "audio/x-wav", "audio/webm", "audio/ogg", "audio/mpeg"}
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
ABSTAIN_THRESHOLD = 0.72
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180.0
SAFE_SUMMARY_OR = "ଏହା ବ୍ରାଉନ୍ ସ୍ପଟ୍ ଭଳି ଦେଖାଯାଉଛି, କିନ୍ତୁ ଫଟୋରୁ ନିଶ୍ଚିତ ରୋଗ ନିର୍ଣ୍ଣୟ ନୁହେଁ।"
SAFE_NEXT_STEP_OR = "ଆଜି ୫ଟି ପ୍ରଭାବିତ ପତ୍ରରେ ଗୋଲ କିମ୍ବା ଅଣ୍ଡାକାର ଓ ମଝି ଧୂସର ଥିବା ଦାଗ ଯାଞ୍ଚ କରନ୍ତୁ।"
SAFE_NEXT_STEP_EN = "Inspect five affected leaves today for round or oval spots with grey centres."
SAFE_WHY_OR = "ଏହି ଲକ୍ଷଣ ବ୍ରାଉନ୍ ସ୍ପଟ୍ ସହ ମେଳ ଖାଏ, ଏବଂ ସରକାରୀ ଓ ଧାନ ଜ୍ଞାନ ସ୍ରୋତ ସମତୁଳିତ ପୋଷକ ଓ ଜଳ ପରିଚାଳନାକୁ ସୁପାରିଶ କରେ।"

# This is intentionally conservative. The demo never generates a chemical prescription.
BANNED_PRESCRIPTION_TERMS = {
    "carbendazim",
    "mancozeb",
    "propiconazole",
    "tricyclazole",
    "fungicide",
    "pesticide",
    "କୀଟନାଶକ",
    "ଫଙ୍ଗିସାଇଡ୍",
}


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class UploadedFile:
    name: str
    mime_type: str
    content: bytes

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class SpeechResult:
    transcript_or: str
    transcript_en: str
    confidence: float
    adapter: str


@dataclass(frozen=True)
class VisionResult:
    label: str
    confidence: float
    cues: tuple[str, ...]
    adapter: str


@dataclass(frozen=True)
class Evidence:
    citation_id: str
    title: str
    publisher: str
    url: str
    excerpt_en: str
    excerpt_or: str


class Generator(Protocol):
    name: str

    def generate(
        self,
        speech: SpeechResult,
        vision: VisionResult,
        evidence: list[Evidence],
    ) -> dict[str, Any]: ...


def decode_upload(payload: dict[str, Any], field: str, allowed_types: set[str]) -> UploadedFile:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise InputError(f"{field} is required")
    name = str(value.get("name", "")).strip()
    mime_type = str(value.get("type", "")).lower().strip()
    encoded = value.get("base64")
    if not name or not isinstance(encoded, str):
        raise InputError(f"{field} must include name and base64")
    if mime_type not in allowed_types:
        raise InputError(f"Unsupported {field} type: {mime_type or 'missing'}")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise InputError(f"{field} is not valid base64") from exc
    if not content:
        raise InputError(f"{field} is empty")
    if len(content) > MAX_FILE_BYTES:
        raise InputError(f"{field} exceeds the 8 MB limit")
    return UploadedFile(name=name, mime_type=mime_type, content=content)


def fixture_digests() -> dict[str, str]:
    paths = {
        "supported_audio": FIXTURES / "odia_brown_spot_question.wav",
        "supported_image": FIXTURES / "rice_brown_spot.svg",
        "uncertain_audio": FIXTURES / "odia_unclear_question.wav",
        "uncertain_image": FIXTURES / "rice_uncertain.svg",
    }
    return {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in paths.items()
        if path.exists()
    }


class DeterministicSpeechAdapter:
    name = "deterministic-fixture-asr"

    def transcribe(self, audio: UploadedFile) -> SpeechResult:
        digests = fixture_digests()
        if audio.digest == digests.get("supported_audio"):
            return SpeechResult(
                transcript_or="ଧାନ ପତ୍ରରେ ଛୋଟ ଗୋଲ ବାଦାମୀ ଦାଗ ଦେଖାଯାଉଛି। କଣ କରିବି?",
                transcript_en="Small round brown spots are appearing on the rice leaves. What should I do?",
                confidence=0.96,
                adapter=self.name,
            )
        if audio.digest == digests.get("uncertain_audio"):
            return SpeechResult(
                transcript_or="ଧାନରେ କିଛି ସମସ୍ୟା ଅଛି।",
                transcript_en="There is some problem with the rice.",
                confidence=0.52,
                adapter=self.name,
            )
        return SpeechResult(
            transcript_or="",
            transcript_en="Audio was received, but the offline adapter could not transcribe it.",
            confidence=0.0,
            adapter=self.name,
        )


class DeterministicVisionAdapter:
    name = "deterministic-fixture-vision"

    def classify(self, image: UploadedFile) -> VisionResult:
        digests = fixture_digests()
        if image.digest == digests.get("supported_image"):
            return VisionResult(
                label="possible_rice_brown_spot",
                confidence=0.88,
                cues=("round brown lesions", "grey centres", "rice leaf context"),
                adapter=self.name,
            )
        if image.digest == digests.get("uncertain_image"):
            return VisionResult(
                label="uncertain",
                confidence=0.41,
                cues=("low detail", "no stable lesion pattern"),
                adapter=self.name,
            )
        return VisionResult(
            label="unsupported_image",
            confidence=0.0,
            cues=("not recognised by offline fixture adapter",),
            adapter=self.name,
        )


class Retriever:
    def __init__(self) -> None:
        raw = json.loads((ROOT / "data" / "knowledge.json").read_text(encoding="utf-8"))
        self.documents = [Evidence(**item) for item in raw]

    def retrieve(self, vision: VisionResult) -> list[Evidence]:
        if vision.label != "possible_rice_brown_spot":
            return []
        return self.documents[:2]


class DeterministicGroundedGenerator:
    name = "deterministic-grounded-demo"

    def generate(
        self,
        speech: SpeechResult,
        vision: VisionResult,
        evidence: list[Evidence],
    ) -> dict[str, Any]:
        citation_ids = [item.citation_id for item in evidence]
        return {
            "summary_or": SAFE_SUMMARY_OR,
            "summary_en": "This resembles a brown-spot pattern, but a photo alone cannot confirm the diagnosis.",
            "next_step_or": SAFE_NEXT_STEP_OR,
            "next_step_en": SAFE_NEXT_STEP_EN,
            "why_or": SAFE_WHY_OR,
            "why_en": "The visible pattern matches published brown-spot cues; official rice guidance prioritises balanced nutrition and water management.",
            "citations": citation_ids,
        }


class OllamaLlamaGenerator:
    name = "ollama-llama-grounded"

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        speech: SpeechResult,
        vision: VisionResult,
        evidence: list[Evidence],
    ) -> dict[str, Any]:
        evidence_payload = [
            {
                "citation_id": item.citation_id,
                "excerpt_en": item.excerpt_en,
                "excerpt_or": item.excerpt_or,
            }
            for item in evidence
        ]
        prompt = (
            "You are a cautious rice crop triage assistant for an Odia-speaking farmer. "
            "Use only the EVIDENCE JSON below and return only the required JSON object. Generate the "
            "English summary and reason from the supplied evidence, and select only citation IDs "
            "supplied below. The application adds reviewed Odia wording and one safe next step after "
            "your grounded response passes validation. Never prescribe a pesticide, fungicide, dose, "
            "or product. The English summary must say this is not a confirmed diagnosis. Every factual "
            "claim must be supported by citation IDs from the evidence.\n\n"
            f"TRANSCRIPT_ODIA: {speech.transcript_or}\n"
            f"VISION: {json.dumps(asdict(vision), ensure_ascii=False)}\n"
            f"EVIDENCE: {json.dumps(evidence_payload, ensure_ascii=False)}"
        )
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": {
                    "type": "object",
                    "properties": {
                        "summary_en": {
                            "type": "string",
                            "description": "English summary saying this is not a confirmed diagnosis",
                        },
                        "why_en": {
                            "type": "string",
                            "description": "English reason grounded in the evidence",
                        },
                        "citations": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [item.citation_id for item in evidence],
                            },
                            "minItems": 1,
                            "uniqueItems": True,
                        },
                    },
                    "required": [
                        "summary_en",
                        "why_en",
                        "citations",
                    ],
                    "additionalProperties": False,
                },
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0, "seed": 0, "num_predict": 256},
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read())
            generation = json.loads(payload["message"]["content"])
            if not isinstance(generation, dict):
                raise ValueError("Ollama response content must be a JSON object")
            allowed_model_fields = {"summary_en", "why_en", "citations"}
            if not set(generation).issubset(allowed_model_fields):
                raise ValueError("Ollama response contains fields outside the grounded schema")
            return {
                **generation,
                "summary_or": SAFE_SUMMARY_OR,
                "next_step_or": SAFE_NEXT_STEP_OR,
                "next_step_en": SAFE_NEXT_STEP_EN,
                "why_or": SAFE_WHY_OR,
            }
        except (
            urllib.error.URLError,
            TimeoutError,
            TypeError,
            ValueError,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError(f"Local Ollama generation failed: {exc}") from exc


def _contains_prescription(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower()
    return any(term in text for term in BANNED_PRESCRIPTION_TERMS)


def _validate_generation(generation: dict[str, Any], evidence: list[Evidence]) -> None:
    required = {
        "summary_or",
        "summary_en",
        "next_step_or",
        "next_step_en",
        "why_or",
        "why_en",
        "citations",
    }
    if not required.issubset(generation):
        raise ValueError("Generator response is missing required grounded fields")
    text_fields = required - {"citations"}
    if any(not isinstance(generation[field], str) or not generation[field].strip() for field in text_fields):
        raise ValueError("Generator response contains an empty or non-text grounded field")
    if any(not re.search(r"[\u0b00-\u0b7f]", generation[field]) for field in ("summary_or", "next_step_or", "why_or")):
        raise ValueError("Generator returned English instead of Odia-script farmer guidance")
    summary_en = generation["summary_en"].lower()
    if "diagnos" not in summary_en or not any(
        boundary in summary_en for boundary in ("not", "cannot", "can't")
    ):
        raise ValueError("Generator omitted the unconfirmed-diagnosis boundary")
    for field in ("next_step_or", "next_step_en"):
        next_step = generation[field].strip()
        sentences = [part for part in re.split(r"[.!?।]+", next_step) if part.strip()]
        if len(sentences) != 1 or "\n" in next_step or ";" in next_step or "next steps" in next_step.lower():
            raise ValueError("Generator returned more than one next step")
    allowed = {item.citation_id for item in evidence}
    citations = generation.get("citations")
    if not isinstance(citations, list) or not citations or not set(citations).issubset(allowed):
        raise ValueError("Generator returned missing or unknown citations")
    if _contains_prescription(generation):
        raise ValueError("Generator crossed the chemical-prescription safety boundary")


class TriagePipeline:
    def __init__(self, generator: Generator) -> None:
        self.speech = DeterministicSpeechAdapter()
        self.vision = DeterministicVisionAdapter()
        self.retriever = Retriever()
        self.generator = generator
        self.fallback_generator = DeterministicGroundedGenerator()

    def triage(self, audio: UploadedFile, image: UploadedFile) -> dict[str, Any]:
        speech = self.speech.transcribe(audio)
        vision = self.vision.classify(image)
        combined_confidence = round(min(speech.confidence, vision.confidence), 2)

        if combined_confidence < ABSTAIN_THRESHOLD:
            return {
                "status": "escalate",
                "confidence": combined_confidence,
                "transcript_or": speech.transcript_or,
                "transcript_en": speech.transcript_en,
                "summary_or": "ଏହି ଫଟୋ ଓ କଣ୍ଠସ୍ୱରରୁ ଭରସାଯୋଗ୍ୟ ନିଷ୍କର୍ଷ ମିଳୁନାହିଁ।",
                "summary_en": "The voice and image do not support a reliable triage result.",
                "next_step_or": "ଆଉ ଗୋଟିଏ ସ୍ପଷ୍ଟ ଫଟୋ ନିଅନ୍ତୁ ଏବଂ ନିକଟସ୍ଥ KVK କିମ୍ବା କୃଷି ସମ୍ପ୍ରସାରଣ ଅଧିକାରୀଙ୍କୁ ଦେଖାନ୍ତୁ।",
                "next_step_en": "Take one clearer close-up and show it to your nearest KVK or agricultural extension officer.",
                "why_or": "ଭୁଲ ପରାମର୍ଶ ଦେବାଠାରୁ ଏଠାରେ ଥମିବା ଅଧିକ ସୁରକ୍ଷିତ।",
                "why_en": "Stopping is safer than giving advice from weak evidence.",
                "citations": [],
                "evidence": [],
                "adapters": {
                    "speech": speech.adapter,
                    "vision": vision.adapter,
                    "generator": "not-run",
                },
                "safety": "No pesticide prescription. Expert escalation required.",
            }

        evidence = self.retriever.retrieve(vision)
        if not evidence:
            raise RuntimeError("No grounded evidence found for a supported result")

        generator_used = self.generator.name
        fallback_reason = None
        try:
            generation = self.generator.generate(speech, vision, evidence)
            _validate_generation(generation, evidence)
        except (RuntimeError, ValueError) as exc:
            generation = self.fallback_generator.generate(speech, vision, evidence)
            _validate_generation(generation, evidence)
            generator_used = self.fallback_generator.name
            fallback_reason = str(exc)

        result = {
            "status": "supported",
            "confidence": combined_confidence,
            "transcript_or": speech.transcript_or,
            "transcript_en": speech.transcript_en,
            **generation,
            "evidence": [asdict(item) for item in evidence],
            "adapters": {
                "speech": speech.adapter,
                "vision": vision.adapter,
                "generator": generator_used,
            },
            "safety": "No pesticide prescription. Confirm persistent or spreading symptoms with a KVK or extension officer.",
        }
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        return result


def build_pipeline() -> TriagePipeline:
    mode = os.getenv("KRISHI_LLM_MODE", "deterministic").lower()
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    try:
        timeout_seconds = float(
            os.getenv("OLLAMA_TIMEOUT_SECONDS", str(DEFAULT_OLLAMA_TIMEOUT_SECONDS))
        )
    except ValueError:
        timeout_seconds = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    if mode == "ollama":
        return TriagePipeline(
            OllamaLlamaGenerator(model=model, timeout_seconds=timeout_seconds)
        )
    return TriagePipeline(DeterministicGroundedGenerator())


def normalise_event_name(name: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", name):
        raise InputError("Invalid event name")
    return name
