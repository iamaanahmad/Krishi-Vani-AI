const state = {
  scenario: "supported",
  audio: null,
  image: null,
  e2eRun: new URLSearchParams(location.search).get("e2e_run") || "",
};

const fixturePaths = {
  supported: {
    audio: "/fixtures/odia_brown_spot_question.wav",
    image: "/fixtures/rice_brown_spot.svg",
  },
  uncertain: {
    audio: "/fixtures/odia_unclear_question.wav",
    image: "/fixtures/rice_uncertain.svg",
  },
};

function encodeBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunk));
  }
  return btoa(binary);
}

async function filePayload(file) {
  return {
    name: file.name,
    type: file.type,
    base64: encodeBase64(await file.arrayBuffer()),
  };
}

async function fixturePayload(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Fixture could not load: ${path}`);
  const blob = await response.blob();
  return {
    name: path.split("/").at(-1),
    type: blob.type.split(";")[0],
    base64: encodeBase64(await blob.arrayBuffer()),
  };
}

async function track(event, status = "") {
  try {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event,
        status,
        is_e2e_test: Boolean(state.e2eRun),
        e2e_run: state.e2eRun,
      }),
    });
  } catch (_) {
    // Analytics must never block the local crop-triage result.
  }
}

document.querySelectorAll(".scenario-button").forEach((button) => {
  button.addEventListener("click", () => {
    state.scenario = button.dataset.scenario;
    state.audio = null;
    state.image = null;
    document.querySelectorAll(".scenario-button").forEach((candidate) => {
      const active = candidate === button;
      candidate.classList.toggle("active", active);
      candidate.setAttribute("aria-pressed", String(active));
    });
    document.querySelector("#audio-input").value = "";
    document.querySelector("#image-input").value = "";
    document.querySelector("#audio-state").textContent = "Guided sample ready";
    document.querySelector("#image-state").textContent = "Guided sample ready";
    track("fixture_selected", state.scenario);
  });
});

function bindFileInput(id, stateKey, labelId) {
  document.querySelector(id).addEventListener("change", (event) => {
    state[stateKey] = event.target.files[0] || null;
    document.querySelector(labelId).textContent = state[stateKey]?.name || "Guided sample ready";
  });
}

bindFileInput("#audio-input", "audio", "#audio-state");
bindFileInput("#image-input", "image", "#image-state");

function citationMarkup(item) {
  const link = document.createElement("a");
  link.className = "citation";
  link.href = item.url;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = `[${item.citation_id}] ${item.title}`;
  const publisher = document.createElement("span");
  publisher.textContent = item.publisher;
  link.append(publisher);
  return link;
}

function renderResult(result) {
  const region = document.querySelector("#result-region");
  const status = document.querySelector("#result-status");
  status.className = `result-status ${result.status}`;
  status.querySelector("strong").textContent = result.status === "supported" ? "Evidence-supported triage" : "Expert check needed";
  document.querySelector("#confidence-value").textContent = `${Math.round(result.confidence * 100)}%`;
  document.querySelector("#result-title").textContent = result.next_step_or;
  document.querySelector("#result-title-en").textContent = result.next_step_en;
  document.querySelector("#transcript").textContent = result.transcript_or || result.transcript_en;
  document.querySelector("#safety-copy").textContent = result.safety;
  document.querySelector("#why-copy").textContent = result.why_or || result.why_en;

  const citations = document.querySelector("#citations");
  citations.replaceChildren();
  if (result.evidence.length) {
    result.evidence.forEach((item) => citations.append(citationMarkup(item)));
  } else {
    const empty = document.createElement("p");
    empty.textContent = "No evidence was strong enough to cite. The system stopped safely.";
    citations.append(empty);
  }

  const adapters = document.querySelector("#adapters");
  adapters.replaceChildren();
  Object.entries(result.adapters).forEach(([key, value]) => {
    const term = document.createElement("dt");
    term.textContent = key;
    const description = document.createElement("dd");
    description.textContent = value;
    adapters.append(term, description);
  });
  region.hidden = false;
  region.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.querySelector("#triage-button").addEventListener("click", async () => {
  const button = document.querySelector("#triage-button");
  const original = button.innerHTML;
  button.disabled = true;
  button.querySelector("span").textContent = "ଯାଞ୍ଚ ଚାଲିଛି…";
  await track("triage_submitted", state.scenario);
  try {
    const selected = fixturePaths[state.scenario];
    const audio = state.audio ? await filePayload(state.audio) : await fixturePayload(selected.audio);
    const image = state.image ? await filePayload(state.image) : await fixturePayload(selected.image);
    const response = await fetch("/api/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio, image }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Triage failed");
    renderResult(result);
    await track("triage_completed", result.status);
  } catch (error) {
    alert(error.message);
    await track("triage_failed", "error");
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
});

fetch("/api/health")
  .then((response) => response.json())
  .then((health) => {
    document.querySelector("#mode-status").lastChild.textContent = health.llm.includes("ollama") ? " Local Llama 3" : " Offline demo";
  })
  .catch(() => {});

track("demo_loaded");

// Deterministic browser proof mode for CI/review screenshots. It uses the same
// controls and API path as a judge clicking the guided fixtures by hand.
const proofScenario = new URLSearchParams(window.location.search).get("proof");
if (["supported", "uncertain"].includes(proofScenario)) {
  document.querySelector(`[data-scenario="${proofScenario}"]`).click();
  document.querySelector("#triage-button").click();
}
