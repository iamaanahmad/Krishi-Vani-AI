# Live demo: phone test, localhost, and static preview

Mentor request, in plain terms: a strong demo with a live link is best, so a
mentor can test it on a phone. Localhost remains the full, judged demo.

## Best choice: use both, and label which is which

1. **Phone preview (static link, when deployed):** the same three scenarios —
   Supported, Uncertain, Unknown upload — with the same confidence gate
   (0.72), the same citation list, and the same fail-closed rule. It is
   clearly labelled in the page as a phone preview. It does NOT run the
   Python server and does NOT run Llama on the phone.
2. **Full demo (localhost, for the finale):** `./demo.sh`, then open
   http://127.0.0.1:8787. This runs the real Python pipeline, the real
   validators, and, when enabled, the real local Llama 3.2 1B path.
   This is the version to show a jury.

Do not present the static preview as the server demo, and do not present
the localhost demo as a live public service. The label on the page is
part of the honesty story, not a footnote to hide.

## Test it on a phone, same Wi-Fi (no deployment needed)

On the computer running the demo:

```bash
KRISHI_HOST=0.0.0.0 KRISHI_PORT=8787 ./demo.sh
```

On the phone, on the same Wi-Fi, open:

```
http://<computer-IP-address>:8787
```

Replace `<computer-IP-address>` with the computer's local IP. This is a
local-network test only — it is not a public link, and it stops when the
demo server stops. Do not expose this port to the public internet without
a reverse proxy, authentication, and a review of the event endpoint.

## Static phone preview deployment (Vercel, static only)

Deploy only the static files, with this layout at the deployment root:

- `index.html`, `app.js`, `styles.css`, `favicon.svg`, `fonts/`
- `fixtures/` (the four fixture files)
- `data/knowledge.json`

When `/api/triage` is unavailable, `app.js` falls back to the labelled
static preview. When the local server is running, the real API is used
first and the preview banner stays hidden.

The live Llama path cannot run on a static host. It needs Ollama on a
machine you control, started with:

```bash
ollama pull llama3.2:1b
OLLAMA_MODEL=llama3.2:1b KRISHI_LLM_MODE=ollama OLLAMA_TIMEOUT_SECONDS=180 ./demo.sh
```

Do not pull a model during a judged demo. Preload it, and keep the
deterministic fallback as the backup if Ollama is slow or unavailable.

## Three-scenario judge script (2 minutes, phone or laptop)

1. **Supported:** one cited, non-chemical next step. Point to the
   confidence breakdown (speech 0.96, vision 0.88, combined 0.88),
   the 5 cited records, and the LLM validation note.
2. **Uncertain:** confidence 0.41, below the 0.72 gate. No citations are
   invented. The answer is a clearer photo plus KVK review.
3. **Unknown upload:** confidence 0.0. This is the fail-closed proof —
   an upload the system has never seen gets no advice at all.

## What changed in this improvement round

- Evidence grew from 2 records to 5 cited ICAR/IRRI records.
- The result now exposes speech confidence, vision confidence, and
  combined confidence, so a jury can see the gate is a minimum, not an
  average.
- The Unknown upload scenario was added to the UI.
- The static phone preview was added, clearly labelled, so a mentor can
  test the three scenarios on a phone without a server.
- Tests grew from 34 to 37, all passing locally. Live Ollama
  re-verification for the 5-record version is still to be run before
  the finale (see docs/OLLAMA_PROOF.md note below).
