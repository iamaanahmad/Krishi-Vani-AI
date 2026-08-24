# Verified local Ollama path

This repository completed both committed scenarios through a real local Llama-family model on 24 August 2026. The supported path used Ollama; the uncertain path abstained before generation.

## Exact model and runtime

- Ollama `0.32.15`, local HTTP API at `http://127.0.0.1:11434`
- `llama3.2:1b`, Ollama model ID `baf6a787fdff`
- Llama architecture, 1.2B parameters, Q8_0 quantization, 1.3 GB local model
- CPU-only verification host; no paid API or cloud model credential

## Repeat the proof

Install Ollama using its official platform instructions, then run from the repository root:

```bash
ollama serve
ollama pull llama3.2:1b
python3 -m scripts.verify_ollama --model llama3.2:1b --timeout 180
```

To run the browser demo on the same adapter:

```bash
OLLAMA_MODEL=llama3.2:1b \
KRISHI_LLM_MODE=ollama \
OLLAMA_TIMEOUT_SECONDS=180 \
./demo.sh
```

`scripts.verify_ollama` exits non-zero unless the supported result names `ollama-llama-grounded` with no fallback, all citation IDs belong to the retrieved evidence, no banned chemical term appears, and the uncertain result abstains before generation.

## Observed result

One CPU-only verification run produced:

```json
{
  "model": "llama3.2:1b",
  "supported": {
    "latency_seconds": 26.383,
    "status": "supported",
    "confidence": 0.88,
    "generator": "ollama-llama-grounded",
    "citations": ["ICAR-KHARIF-2025-RICE-BS", "IRRI-RKB-BLAST-DIFF"],
    "fallback_reason": null
  },
  "uncertain": {
    "latency_seconds": 0.003,
    "status": "escalate",
    "confidence": 0.41,
    "generator": "not-run",
    "citations": [],
    "fallback_reason": null
  },
  "passed": true
}
```

Latency is machine-dependent and is not a field-readiness claim. The 26.383-second supported measurement used an already-loaded model; an earlier CPU run took 86.047 seconds. The first cold CPU attempt exposed the previous fixed 45-second timeout and fell back safely at 45.222 seconds. The adapter now defaults to 180 seconds and accepts `OLLAMA_TIMEOUT_SECONDS` for slower local hosts.

## Safety failure proof

`make check` runs 20 tests. Independent tests force each relevant failure and confirm the supported result returns `deterministic-grounded-demo` with approved citations and a `fallback_reason`:

- invalid JSON from Ollama;
- an unknown citation ID;
- unsafe chemical advice;
- English in an Odia farmer-guidance field;
- omission of the unconfirmed-diagnosis boundary;
- local model/network failure.

The uncertain fixture remains below the `0.72` confidence threshold, returns no citations, and never calls the model.

## Honest evidence boundary

The real Llama model performs a narrow role: it receives the deterministic fixture transcript, deterministic vision cues, and two curated ICAR/IRRI excerpts, then generates the English summary and reason and selects citations under a JSON schema. Application policy supplies the reviewed Odia wording and the single safe observation step before final validation. This run does not prove Odia generation quality, real ASR, real vision, AIKosh use, agronomic accuracy, field latency, or farmer readiness.
