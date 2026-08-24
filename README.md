# Krishi-Vani AI

Krishi-Vani AI is a narrow, offline-capable challenge prototype for Odia rice triage. Two labelled audio-and-image fixture pairs demonstrate either one cited, non-chemical next step or a clear KVK/extension escalation.

## Run in one command

Python 3.11+ is the only requirement.

```bash
./demo.sh
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). The guided demo starts with the supported fixture. Switch to **Uncertain** to show the abstention path.

Run all checks with:

```bash
make check
```

## What is real, and what is simulated

The demo is intentionally explicit about its boundaries:

| Part | Demo status | Not yet implemented |
|---|---|---|
| Audio and image transport | Real local browser-to-server transport for the included fixtures | Interpretation of arbitrary farmer media |
| Odia speech recognition | Deterministic SHA-matched fixture adapter | Real speech recognition |
| Rice image triage | Deterministic SHA-matched fixture adapter | Real image classification |
| Retrieval and citations | Retrieval from a small curated ICAR/IRRI knowledge file | A licensed, versioned Odia corpus |
| Response generation | Deterministic adapter by default; local Llama 3.2 1B is implemented and verified | Model-generated Odia guidance |
| Safety | Confidence gate, citation validation, chemical-prescription guard and KVK escalation | Agronomic evaluation, field review and monitoring |

The included SVGs are labelled synthetic illustrations. The WAVs are deterministic audio transport fixtures, not recordings or synthetic speech. Unknown uploads fail closed and are not interpreted.

## Use local Llama 3

Install [Ollama](https://ollama.com/), then pull and verify the tested model:

```bash
ollama pull llama3.2:1b
python3 -m scripts.verify_ollama --model llama3.2:1b --timeout 180
OLLAMA_MODEL=llama3.2:1b KRISHI_LLM_MODE=ollama OLLAMA_TIMEOUT_SECONDS=180 ./demo.sh
```

The model receives the fixture transcript, vision cues, and retrieved evidence. It generates the grounded English summary and reason and selects citation IDs under a strict JSON schema. The application adds reviewed Odia wording and the single safe next step before validating the complete response. Unknown citations, unsafe advice, invalid JSON, wrong-language farmer guidance, or a local model failure trigger the deterministic safe fallback. No paid API or cloud credential is required.

The repeatable measured run, exact model metadata, relevant output, and evidence boundary are recorded in [the Ollama proof](docs/OLLAMA_PROOF.md).

## Safety boundary

- This is triage, not a confirmed diagnosis.
- The demo never prescribes pesticides, fungicides, products, or doses.
- Confidence below `0.72` abstains and sends the farmer to a KVK or agricultural extension officer.
- A supported answer includes citation IDs that must match retrieved evidence.
- Unknown uploads fail closed in offline mode.

See [the architecture](docs/ARCHITECTURE.md), [data and model notes](docs/DATA_AND_MODEL_NOTES.md), and [the 5–7 minute judge walkthrough](docs/JUDGE_WALKTHROUGH.md).

## Repository map

```text
app/                  Odia-first accessible web workbench
krishi_vani/          HTTP server, adapters, retrieval, grounding and safety
data/knowledge.json   Curated cited demonstration evidence
fixtures/             Labelled supported and uncertain fixtures
scripts/              Reproducible fixture generation
tests/                Input, grounding, citation, safety and API checks
docs/                 Architecture, limitations and walkthrough
```

## Contact

Questions about this prototype can go to [unleashllm@mail.tin.computer](mailto:unleashllm@mail.tin.computer).

## License

Code is licensed under the [MIT License](LICENSE). Bundled Noto Oriya fonts use the [SIL Open Font License](app/fonts/OFL.txt). The repository does not redistribute third-party datasets or model files. Linked third-party source material remains under its publisher's terms.
