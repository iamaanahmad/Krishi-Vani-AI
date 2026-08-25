const state = {
  scenario: "supported",
  e2eRun: new URLSearchParams(location.search).get("e2e_run") || "",
};

const POSTHOG_CONFIG = Object.freeze({
  publicKey: "phc_xZyv8A2BbbYbfAc88biumDotz5AszK3VxrUMmCBubea2",
  host: "https://us.i.posthog.com",
});
const ANALYTICS_SCHEMA = Object.freeze({
  "$pageview": ["referrer_channel"],
  demo_loaded: ["referrer_channel"],
  triage_submitted: ["scenario"],
  triage_completed: ["outcome"],
  triage_failed: ["stage"],
  value_reached: ["outcome", "referrer_channel"],
  error_shown: ["stage"],
  empty_state_shown: ["surface"],
  feedback_submitted: ["rating", "feedback"],
});
const POSTHOG_DISTINCT_ID_KEY = "krishi_vani_posthog_distinct_id";
const FIRST_REFERRER_CHANNEL_KEY = "krishi_vani_first_referrer_channel";
const REFERRER_CHANNELS = new Set(["ai_assistant", "campaign", "referral", "direct"]);
const AI_REFERRER_HOSTS = Object.freeze([
  "chatgpt.com",
  "chat.openai.com",
  "openai.com",
  "claude.ai",
  "perplexity.ai",
  "gemini.google.com",
  "copilot.microsoft.com",
]);
const AI_UTM_SOURCES = new Set([
  "chatgpt",
  "chatgpt.com",
  "chat.openai.com",
  "openai",
  "openai.com",
  "claude",
  "claude.ai",
  "perplexity",
  "perplexity.ai",
  "gemini",
  "gemini.google.com",
  "copilot",
  "copilot.microsoft.com",
]);
let sessionDistinctId = "";
let sessionReferrerChannel = "";
let selectedFeedbackRating = "";

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

function posthogDistinctId() {
  if (sessionDistinctId) return sessionDistinctId;
  try {
    sessionDistinctId = localStorage.getItem(POSTHOG_DISTINCT_ID_KEY) || "";
    if (!sessionDistinctId) {
      sessionDistinctId = globalThis.crypto?.randomUUID?.()
        || `anonymous-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      localStorage.setItem(POSTHOG_DISTINCT_ID_KEY, sessionDistinctId);
    }
  } catch (_) {
    sessionDistinctId = `anonymous-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
  return sessionDistinctId;
}

function isAiReferrerHost(hostname) {
  const host = hostname.toLowerCase().replace(/^www\./, "");
  return AI_REFERRER_HOSTS.some((candidate) => (
    host === candidate || host.endsWith(`.${candidate}`)
  ));
}

function deriveReferrerChannel() {
  let utmSource = "";
  try {
    utmSource = new URLSearchParams(location.search)
      .get("utm_source")
      ?.trim()
      .toLowerCase()
      .replace(/^www\./, "") || "";
  } catch (_) {
    // A malformed URL must not interfere with the product journey.
  }

  if (AI_UTM_SOURCES.has(utmSource)) return "ai_assistant";

  if (document.referrer) {
    try {
      const referrer = new URL(document.referrer);
      if (isAiReferrerHost(referrer.hostname)) return "ai_assistant";
      if (referrer.origin !== location.origin) return utmSource ? "campaign" : "referral";
    } catch (_) {
      // Never retain or send malformed referrer content.
    }
  }

  return utmSource ? "campaign" : "direct";
}

function firstReferrerChannel() {
  if (sessionReferrerChannel) return sessionReferrerChannel;
  try {
    const stored = localStorage.getItem(FIRST_REFERRER_CHANNEL_KEY) || "";
    if (REFERRER_CHANNELS.has(stored)) {
      sessionReferrerChannel = stored;
      return sessionReferrerChannel;
    }
  } catch (_) {
    // Fall back to memory when local storage is unavailable.
  }

  sessionReferrerChannel = deriveReferrerChannel();
  try {
    localStorage.setItem(FIRST_REFERRER_CHANNEL_KEY, sessionReferrerChannel);
  } catch (_) {
    // The coarse channel remains available for this page load.
  }
  return sessionReferrerChannel;
}

function approvedProperties(event, properties = {}) {
  const approved = ANALYTICS_SCHEMA[event];
  if (!approved) return null;
  const clean = { route: location.pathname };
  approved.forEach((key) => {
    if (typeof properties[key] !== "string") return;
    const limit = key === "feedback" ? 280 : 40;
    const value = properties[key].trim().slice(0, limit);
    if (value) clean[key] = value;
  });
  if (approved.includes("referrer_channel")) {
    clean.referrer_channel = firstReferrerChannel();
  }
  if (event === "feedback_submitted" && !["thumbs_up", "thumbs_down"].includes(clean.rating)) {
    delete clean.rating;
  }
  return clean;
}

function capturePostHog(event, properties) {
  const clean = approvedProperties(event, properties);
  if (!clean) return;
  const eventProperties = {
    ...clean,
    $process_person_profile: false,
  };
  if (state.e2eRun) {
    eventProperties.is_e2e_test = true;
    eventProperties.e2e_run = state.e2eRun;
  }
  if (globalThis.posthog?.capture) {
    globalThis.posthog.capture(event, eventProperties);
    return;
  }
  const fallbackProperties = {
    distinct_id: posthogDistinctId(),
    ...eventProperties,
  };
  fetch(`${POSTHOG_CONFIG.host}/capture/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: POSTHOG_CONFIG.publicKey,
      event,
      properties: fallbackProperties,
    }),
    keepalive: true,
  }).catch(() => {});
}

async function track(event, properties = {}) {
  capturePostHog(event, properties);
  try {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event,
        properties: approvedProperties(event, properties) || {},
        is_e2e_test: Boolean(state.e2eRun),
        e2e_run: state.e2eRun,
      }),
    });
  } catch (_) {
    // Analytics must never block the local crop-triage result.
  }
}

function initialisePostHog() {
  if (!globalThis.posthog?.init) return;
  globalThis.posthog.init(POSTHOG_CONFIG.publicKey, {
    api_host: POSTHOG_CONFIG.host,
    ui_host: "https://us.posthog.com",
    defaults: "2026-01-30",
    person_profiles: "identified_only",
    autocapture: false,
    capture_pageview: false,
    capture_pageleave: false,
    capture_exceptions: false,
    disable_surveys: true,
    capture_performance: false,
    enable_recording_console_log: false,
    disable_session_recording: false,
    rageclick: true,
    capture_dead_clicks: true,
    session_recording: {
      maskAllInputs: true,
      maskTextSelector: ".ph-mask",
      blockSelector: "audio, video, canvas, .ph-no-capture",
      recordCrossOriginIframes: false,
      collectFonts: false,
    },
  });
}

document.querySelectorAll(".scenario-button").forEach((button) => {
  button.addEventListener("click", () => {
    state.scenario = button.dataset.scenario;
    document.querySelector("#result-region").hidden = true;
    document.querySelectorAll(".scenario-button").forEach((candidate) => {
      const active = candidate === button;
      candidate.classList.toggle("active", active);
      candidate.setAttribute("aria-pressed", String(active));
    });
  });
});

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
  status.querySelector("strong").textContent = result.status === "supported" ? "Fixture evidence matched" : "Expert check needed";
  document.querySelector("#evidence-gate-value").textContent = result.status === "supported" ? "Passed" : "Stopped";
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
    track("empty_state_shown", { surface: "citations" });
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
  resetFeedbackPrompt();
  track("value_reached", { outcome: result.status });
  if (!new URLSearchParams(location.search).has("proof")) {
    region.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function resetFeedbackPrompt() {
  selectedFeedbackRating = "";
  document.querySelectorAll("[data-rating]").forEach((button) => {
    button.disabled = false;
    button.setAttribute("aria-pressed", "false");
  });
  document.querySelector("#feedback-comment").value = "";
  document.querySelector("#feedback-form").hidden = true;
  document.querySelector("#feedback-thanks").hidden = true;
  document.querySelector("#feedback-prompt").hidden = false;
}

document.querySelectorAll("[data-rating]").forEach((button) => {
  button.addEventListener("click", () => {
    selectedFeedbackRating = button.dataset.rating;
    document.querySelectorAll("[data-rating]").forEach((candidate) => {
      candidate.setAttribute("aria-pressed", String(candidate === button));
    });
    document.querySelector("#feedback-form").hidden = false;
    document.querySelector("#feedback-comment").focus();
  });
});

document.querySelector("#feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!["thumbs_up", "thumbs_down"].includes(selectedFeedbackRating)) return;
  const submit = event.currentTarget.querySelector('button[type="submit"]');
  submit.disabled = true;
  const feedback = document.querySelector("#feedback-comment").value.trim().slice(0, 280);
  await track("feedback_submitted", {
    rating: selectedFeedbackRating,
    feedback,
  });
  document.querySelector("#feedback-form").hidden = true;
  document.querySelectorAll("[data-rating]").forEach((button) => { button.disabled = true; });
  document.querySelector("#feedback-thanks").hidden = false;
  submit.disabled = false;
});

document.querySelector("#triage-button").addEventListener("click", async () => {
  const button = document.querySelector("#triage-button");
  const original = button.innerHTML;
  button.disabled = true;
  button.querySelector("span").textContent = "ଯାଞ୍ଚ ଚାଲିଛି…";
  await track("triage_submitted", { scenario: state.scenario });
  try {
    const selected = fixturePaths[state.scenario];
    const audio = await fixturePayload(selected.audio);
    const image = await fixturePayload(selected.image);
    const response = await fetch("/api/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio, image }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Triage failed");
    renderResult(result);
    await track("triage_completed", { outcome: result.status });
  } catch (error) {
    alert(error.message);
    await track("error_shown", { stage: "triage" });
    await track("triage_failed", { stage: "triage" });
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

initialisePostHog();
track("$pageview");
track("demo_loaded");

// Deterministic browser proof mode for CI/review screenshots. It uses the same
// controls and API path as a judge clicking the guided fixtures by hand.
const proofScenario = new URLSearchParams(window.location.search).get("proof");
if (["supported", "uncertain"].includes(proofScenario)) {
  document.querySelector(`[data-scenario="${proofScenario}"]`).click();
  document.querySelector("#triage-button").click();
}
