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

Set `KRISHI_LLM_MODE=ollama` to use a local Llama 3-family model through Ollama's `/api/chat` interface. The verified adapter uses Llama for grounded English synthesis and citation selection. It then adds reviewed Odia wording and one policy-controlled next step before validating the complete bilingual result.

The generator is constrained in four layers:

1. temperature zero and a strict JSON schema;
2. only the compact retrieved excerpts and their citation IDs enter the model prompt;
3. reviewed Odia wording and the one safe action are added by application policy;
4. citation IDs must be non-empty and a subset of retrieved documents;
5. invalid JSON, wrong-language farmer guidance, chemical prescription terms, timeouts, and model failures force a safe deterministic fallback.

See [`OLLAMA_PROOF.md`](OLLAMA_PROOF.md) for the exact verified model, command, output, latency, and limitations.

## Production adapter seams

The next implementation step is to add actual adapters behind the same return types:

- Odia ASR from a verified AI4Bharat/Bhashini-compatible model or API;
- an image classifier trained and evaluated on a licensed AIKosh rice dataset;
- a versioned Odia corpus with per-chunk licences and agronomist review;
- local or hosted open-weight Llama inference with latency and failure telemetry.

No live access to those systems is claimed by this repository.
