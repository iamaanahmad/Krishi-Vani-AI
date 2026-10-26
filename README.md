# Krishi-Vani AI

> **🏆 Top Finalist — Unleash LLM Innovation Challenge** (IndiaAI × AICTE × Meta, YuvAI Edition)  
> An open-source rice-crop triage prototype for Odia-speaking farmers — one safe, cited next step or an expert escalation, with zero pesticide prescriptions.

[![Top Finalist](https://img.shields.io/badge/Unleash%20LLM-Top%20Finalist-gold.svg)](https://unleashllm.in/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![LLM: Llama 3.2 1B](https://img.shields.io/badge/LLM-Llama%203.2%201B%20(Ollama)-purple.svg)](#-optional-local-llm-ollama--llama-32-1b)
[![Responsible AI](https://img.shields.io/badge/Safety-Zero%20Chemical%20Prescriptions-darkgreen.svg)](#-safety-boundary)

---

## What it does

A farmer speaks an Odia voice question and uploads a leaf photo. The system:

1. **Transcribes** the voice input via a speech adapter.
2. **Classifies** the leaf image via a vision adapter.
3. **Gates on confidence** — abstains below `0.72` and routes the farmer to a KVK or agricultural extension officer.
4. **Retrieves** grounded evidence from a curated ICAR/IRRI knowledge file.
5. **Generates** a bilingual (Odia + English) response with exactly one safe, non-chemical next step and mandatory citation IDs.
6. **Validates** every response: citations must match retrieval, chemical prescriptions are blocked, and wrong-language or invalid output falls back to a deterministic safe answer.

---

## Run in one command

Python 3.11+ is the only requirement — no pip install, no external API keys.

```bash
./demo.sh
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). The guided demo starts on the **Supported** fixture. Switch to **Uncertain** to see the abstention path.

Run all checks with:

```bash
make check
```

---

## Features

### 🌾 Bilingual Odia-first interface

The web workbench is built for Odia-speaking farmers. All farmer-facing guidance — summary, next step, and reason — is delivered in Odia script. English equivalents are shown alongside for verification.

### 🎤 Voice + leaf photo triage

The API accepts an audio file (WAV, WebM, OGG, MP3 — up to 8 MB) and an image (PNG, JPEG, WebP, SVG) together. Both are required; neither alone produces an answer.

### 🔒 Confidence gate

The minimum combined confidence threshold is **0.72**. If either the speech adapter or the vision adapter returns low confidence, the system abstains and routes the farmer to human expertise — it never guesses.

### 📚 Evidence-grounded responses

Every supported answer is backed by retrieved excerpts from `data/knowledge.json`, a manually curated file (5 records) sourced from:

- **ICAR** — *Kharif Agro-Advisories for Farmers 2025* (brown-spot appearance, non-chemical crop management)
- **IRRI** — Rice Knowledge Bank leaf-blast page (distinguishing pointed blast lesions from round brown-spot cues)

Citation IDs are validated against retrieved documents before any response is returned. The supported case now returns all 5 brown-spot records: ICAR Kharif 2025, IRRI blast differentiation, IRRI brown-spot identification, IRRI soil-fertility/resistant-variety care, and IRRI narrow-brown-spot differentiation.

### 🚫 Chemical-prescription guard

A hard-coded blocklist rejects any response containing fungicide or pesticide terms (including Odia-script equivalents). This check runs on every generated response — including Ollama output — before the farmer sees it.

### 🤖 Optional local LLM (Ollama + Llama 3.2 1B)

The default pipeline is fully deterministic and offline. An optional Ollama path uses a local Llama 3.2 1B model for grounded English synthesis and citation selection. The model operates under:

- Temperature zero and a strict JSON schema
- Only compact retrieved excerpts and their citation IDs enter the prompt
- Reviewed Odia wording and the one safe next step are added by application policy after generation
- Invalid JSON, wrong-language output, chemical terms, timeouts, or model failures trigger the deterministic safe fallback automatically

```bash
ollama pull llama3.2:1b
python3 -m scripts.verify_ollama --model llama3.2:1b --timeout 180
OLLAMA_MODEL=llama3.2:1b KRISHI_LLM_MODE=ollama OLLAMA_TIMEOUT_SECONDS=180 ./demo.sh
```

No paid API or cloud credential is required. The exact verified run is recorded in [docs/OLLAMA_PROOF.md](docs/OLLAMA_PROOF.md).

### 🔁 Safe deterministic fallback

If the primary generator fails validation for any reason, the pipeline immediately retries with the `DeterministicGroundedGenerator`. The farmer always receives a safe, validated response or an explicit escalation — never a blank screen or an unsafe answer.

### ✅ Automated test suite

`make check` compiles all modules and runs the full test suite covering:

- Input validation (missing fields, wrong MIME types, oversized files)
- Evidence grounding and citation integrity
- Abstention at the confidence boundary
- Invalid JSON and wrong-language output rejection
- Chemical-prescription blocking
- Ollama model-failure fallback
- HTTP API contract (`POST /api/triage`)
- E2E event read-back

---

## What is real, and what is simulated

| Part | Demo status | Not yet implemented |
|---|---|---|
| Audio and image transport | Real local browser-to-server transport for the included fixtures | Interpretation of arbitrary farmer media |
| Odia speech recognition | Deterministic SHA-256–matched fixture adapter | Real speech recognition |
| Rice image triage | Deterministic SHA-256–matched fixture adapter | Real image classification |
| Retrieval and citations | Retrieval from a curated ICAR/IRRI knowledge file (5 records) | A licensed, versioned Odia corpus |
| Response generation | Deterministic adapter by default; local Llama 3.2 1B verified | Model-generated Odia guidance |
| Safety | Confidence gate, citation validation, chemical-prescription guard, KVK escalation | Agronomic evaluation, field review, monitoring |

The included SVGs are labelled synthetic illustrations. The WAVs are deterministic audio transport fixtures, not recordings or synthetic speech. Unknown uploads fail closed and are not interpreted.

---

## Repository map

```
app/                  Odia-first accessible web workbench (HTML, CSS, JS)
krishi_vani/          HTTP server, adapters, retrieval, grounding, and safety
  core.py             Pipeline, adapters, confidence gate, validation
  server.py           ThreadedHTTPServer, API endpoints, static serving
data/knowledge.json   Curated cited ICAR/IRRI demonstration evidence (5 records)
fixtures/             Labelled supported and uncertain audio + image fixtures
scripts/              Reproducible fixture generation and Ollama verification
tests/                Input, grounding, citation, safety, and API checks
docs/                 Architecture, data notes, Ollama proof, judge walkthrough
```

---

## API

### `POST /api/triage`

**Request** (`application/json`):

```json
{
  "audio": { "name": "question.wav", "type": "audio/wav", "base64": "<base64>" },
  "image": { "name": "leaf.png",     "type": "image/png", "base64": "<base64>" }
}
```

**Response — supported** (`200`):

```json
{
  "status": "supported",
  "confidence": 0.88,
  "transcript_or": "ଧାନ ପତ୍ରରେ ଛୋଟ ଗୋଲ ବାଦାମୀ ଦାଗ...",
  "transcript_en": "Small round brown spots are appearing on the rice leaves...",
  "summary_en": "This resembles a brown-spot pattern, but a photo alone cannot confirm the diagnosis.",
  "next_step_en": "Inspect five affected leaves today for round or oval spots with grey centres.",
  "citations": ["icar-kharif-2025-brown-spot"],
  "evidence": [...],
  "safety": "No pesticide prescription. Confirm persistent symptoms with a KVK or extension officer."
}
```

**Response — escalate** (`200`): returned when `confidence < 0.72` or evidence is absent. Contains `"status": "escalate"` and a KVK next step, no citations.

**Error** (`400`): invalid or missing input. **Error** (`500`): pipeline failure (always safe, never exposes a prescription).

### `GET /api/health`

Returns `{ "status": "ok", "mode": "offline-demo", "llm": "<generator-name>" }`.

---

## Safety boundary

- This is **triage, not a confirmed diagnosis**.
- The demo **never prescribes** pesticides, fungicides, products, or doses.
- Confidence below **0.72** abstains and routes the farmer to a KVK or agricultural extension officer.
- Every supported answer requires citation IDs that must match retrieved evidence.
- Unknown uploads fail closed — they receive zero confidence and cannot accidentally receive advice.

---

## Further reading

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline diagram, adapter seams, LLM constraints |
| [docs/DATA_AND_MODEL_NOTES.md](docs/DATA_AND_MODEL_NOTES.md) | Evidence sources, fixture purpose, field-use requirements |
| [docs/OLLAMA_PROOF.md](docs/OLLAMA_PROOF.md) | Verified Llama 3.2 1B run: command, output, latency |
| [docs/JUDGE_WALKTHROUGH.md](docs/JUDGE_WALKTHROUGH.md) | 5–7 minute guided demo walkthrough |

---

## License

Code is licensed under the [MIT License](LICENSE). Bundled Noto Oriya fonts use the [SIL Open Font License](app/fonts/OFL.txt). The repository does not redistribute third-party datasets or model files. Linked third-party source material remains under its publisher's terms.
