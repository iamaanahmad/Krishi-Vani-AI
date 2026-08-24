# Architecture

The first build is deliberately one process and one crop. That makes the judge path reproducible while keeping every model boundary replaceable.

```text
voice file ──> speech adapter ─┐
                              ├─> confidence gate ─> evidence retrieval
leaf image ──> vision adapter ┘                         │
                                                       v
                               cited next step <─ grounded generator
                                      │
                         citation + chemical-safety validators
                                      │
                         supported answer or KVK escalation
```

## Request contract

`POST /api/triage` accepts JSON with `audio` and `image` objects. Each has a file name, allow-listed MIME type, and base64 content. Each upload is capped at 8 MB. Invalid or missing input returns HTTP 400.

## Offline adapters

The default speech and vision adapters identify the exact committed fixtures by SHA-256. A recognised pair produces an Odia transcript plus brown-spot cues. Unknown bytes get zero confidence and therefore cannot accidentally receive advice. These adapters demonstrate the interfaces and safety orchestration, not model accuracy.

## Open-source LLM path

Set `KRISHI_LLM_MODE=ollama` to use a local Llama 3-family model through Ollama's `/api/chat` interface. The model is used for the core synthesis task: turn retrieved evidence and multimodal adapter outputs into a short Odia/English response.

The generator is constrained in four layers:

1. temperature zero and strict JSON mode;
2. a prompt that allows only supplied evidence and one non-chemical action;
3. citation IDs must be non-empty and a subset of retrieved documents;
4. chemical prescription terms force a safe deterministic fallback.

## Production adapter seams

The next implementation step is to add actual adapters behind the same return types:

- Odia ASR from a verified AI4Bharat/Bhashini-compatible model or API;
- an image classifier trained and evaluated on a licensed AIKosh rice dataset;
- a versioned Odia corpus with per-chunk licences and agronomist review;
- local or hosted open-weight Llama inference with latency and failure telemetry.

No live access to those systems is claimed by this repository.
