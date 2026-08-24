# 5–7 minute judge walkthrough

## 0:00–0:40 — the farmer problem

Open the app and stay on the hero. Explain: an Odia-speaking rice farmer sends a voice question and leaf photo. Krishi-Vani returns one understandable next step only when the evidence is strong enough. Otherwise it stops and escalates.

## 0:40–1:20 — honest demo boundaries

Point to **Offline demo** and **Uses labelled synthetic fixtures**. Say that the demo media adapters are deterministic so the walkthrough works without credentials. AIKosh and AI4Bharat are production adapter targets, not claimed integrations.

## 1:20–2:40 — supported case

Keep **Supported** selected and click **ଧାନ ଯାଞ୍ଚ କରନ୍ତୁ**.

Show:

1. the Odia voice transcript;
2. confidence above the abstention threshold;
3. exactly one next step: inspect five leaves and check water/nutrient balance;
4. the ICAR and IRRI citation links;
5. the explicit “not a confirmed diagnosis” and no-pesticide boundary.

Open **Demo adapters** to identify the deterministic ASR/vision adapter and grounded generator.

## 2:40–3:50 — uncertain case

Scroll back to the workbench, select **Uncertain**, and run the check again.

Show that confidence drops below `0.72`, no citation is fabricated, and the answer asks for a clearer close-up plus KVK/extension review. This is the responsible-AI moment: the system knows when not to answer.

## 3:50–5:10 — meaningful Llama 3 role

Open `krishi_vani/core.py` at `OllamaLlamaGenerator`. Explain that local Llama 3 receives the fixture transcript, vision cues, and retrieved evidence, then generates a grounded English summary and reason plus citation selection under a strict JSON schema. The application adds reviewed Odia wording and one safe next step. Citation IDs are checked against retrieval, chemical prescriptions are rejected, and failures fall back safely.

If Ollama and a model are already available, restart with:

```bash
OLLAMA_MODEL=llama3.2:1b KRISHI_LLM_MODE=ollama OLLAMA_TIMEOUT_SECONDS=180 ./demo.sh
```

Do not pull a model during the judged demo.

## 5:10–6:10 — engineering proof

Run `make check`. Call out the automated coverage for input validation, evidence grounding, citation integrity, abstention, invalid JSON, wrong-language output, unsafe chemical advice, model failure, the API, and E2E event read-back. The real-model evidence is reproducible with `python3 -m scripts.verify_ollama` and recorded in `docs/OLLAMA_PROOF.md`.

## 6:10–6:40 — production path

Close with the narrow plan: replace the same adapter interfaces with verified Odia ASR and AIKosh-trained rice vision, evaluate on Odisha field data with agronomists, then pilot through a KVK. The current prototype proves the safe product loop without overstating readiness.
