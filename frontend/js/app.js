/**
 * Carbon Footprint Assistant - frontend controller.
 *
 * Handles the chat assistant (POST /api/chat) and the footprint assessment
 * form (POST /api/assess), with the 3D avatar reacting to state.
 *
 * Robustness: all network calls go through `fetchJson`, which never throws on a
 * non-JSON response (e.g. an HTML 404/500 from a stale server). Instead it
 * reports a clear, actionable message. Server data is always inserted with
 * `textContent` (never innerHTML), so the UI is immune to HTML/script injection.
 */

"use strict";

/* ---------------------------------------------------------------------------
 * Networking helper
 * ------------------------------------------------------------------------- */

/**
 * Fetch JSON safely.
 * @returns {Promise<{ok:boolean,status:number,data:object|null,reason:string}>}
 *   `data` is the parsed JSON or null. `reason` describes why data is null.
 *   Only rejects on a genuine network failure (server unreachable).
 */
async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  let data = null;
  let reason = "";
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      // The server replied, but not with JSON - typically an HTML error page
      // from a route that is not registered (stale server) or a crash page.
      reason = "non-json";
    }
  } else {
    reason = "empty";
  }
  return { ok: res.ok, status: res.status, data: data, reason: reason };
}

/** A consistent message when the server returns HTML/empty instead of JSON. */
function staleServerMessage(status) {
  return (
    "The server returned an unexpected response (status " + status + "). " +
    "This usually means the Flask server needs restarting so new routes load: " +
    "stop it with Ctrl+C and run 'python run.py' again, then refresh."
  );
}

/** A consistent message when the backend cannot be reached at all. */
function offlineMessage() {
  return (
    "I can't reach the backend. Make sure the Flask server is running " +
    "('python run.py') and open the app at http://localhost:5000 - not by " +
    "double-clicking the HTML file."
  );
}

/* ---------------------------------------------------------------------------
 * Small helpers
 * ------------------------------------------------------------------------- */

/** Safely set the avatar state if the 3D module loaded. */
function setAvatar(state) {
  if (window.TerraAvatar && window.TerraAvatar.setState) {
    window.TerraAvatar.setState(state);
  }
  const status = document.getElementById("avatar-status");
  if (status) {
    status.textContent =
      state === "thinking" ? "Thinking..."
      : state === "speaking" ? "Here is what I found"
      : "Ready to help";
  }
}

/** Create an element with optional class and text. */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/* ---------------------------------------------------------------------------
 * Chat assistant
 * ------------------------------------------------------------------------- */

function addBubble(role, text) {
  const log = document.getElementById("chat-log");
  const row = el("div", "bubble-row " + role);
  const bubble = el("div", "bubble bubble-" + role, text);
  row.appendChild(bubble);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function showTyping() {
  const log = document.getElementById("chat-log");
  const row = el("div", "bubble-row assistant");
  const bubble = el("div", "bubble bubble-assistant typing");
  for (let i = 0; i < 3; i++) bubble.appendChild(el("span", "dot"));
  row.appendChild(bubble);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return function remove() {
    if (row.parentNode) row.parentNode.removeChild(row);
  };
}

async function askAssistant(question) {
  addBubble("user", question);
  setAvatar("thinking");
  const removeTyping = showTyping();

  let result;
  try {
    result = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question }),
    });
  } catch (err) {
    removeTyping();
    addBubble("assistant", offlineMessage());
    setAvatar("idle");
    return;
  }

  removeTyping();

  if (!result.data) {
    addBubble("assistant", staleServerMessage(result.status));
    setAvatar("idle");
    return;
  }
  if (!result.ok) {
    addBubble("assistant", result.data.error || "Sorry, something went wrong.");
    setAvatar("idle");
    return;
  }

  const data = result.data;
  const bubble = addBubble("assistant", data.reply);
  if (data.topic && data.source === "knowledge_base") {
    bubble.appendChild(el("span", "bubble-topic", "Topic: " + data.topic));
  }
  if (data.suggestions && data.suggestions.length) {
    renderSuggestions(data.suggestions);
  }
  setAvatar("speaking");
  window.setTimeout(function () { setAvatar("idle"); }, 2600);
}

function renderSuggestions(topics) {
  const row = document.getElementById("chat-suggestions");
  row.textContent = "";
  topics.forEach(function (topic) {
    const chip = el("button", "chip", topic);
    chip.type = "button";
    chip.addEventListener("click", function () {
      document.getElementById("chat-input").value = "";
      askAssistant(topic);
    });
    row.appendChild(chip);
  });
}

async function loadSuggestions() {
  try {
    const result = await fetchJson("/api/chat/suggestions");
    if (result.data && result.data.suggestions) {
      renderSuggestions(result.data.suggestions);
    }
  } catch (err) {
    /* Non-fatal: chat still works without seed chips. */
  }
}

function handleChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  askAssistant(question);
}

/* ---------------------------------------------------------------------------
 * Footprint assessment form
 * ------------------------------------------------------------------------- */

const NUMERIC_FIELDS = {
  weekly_km: "Distance travelled per week",
  flights_per_year: "Flights per year",
  electricity_kwh: "Household electricity",
  gas_kwh: "Household gas",
  household_size: "People in your household",
};

const SELECT_FIELDS = {
  transport_mode: "Main mode of transport",
  diet_type: "Typical diet",
};

const CATEGORY_LABELS = {
  transport: "Transport",
  flights: "Flights",
  diet: "Diet",
  electricity: "Electricity",
  gas: "Gas / heating",
};

const RATING_CLASS = {
  Low: "rating-low",
  Medium: "rating-moderate",     // dataset-trained model uses Low/Medium/High
  Moderate: "rating-moderate",   // synthetic fallback band
  High: "rating-high",
  "Very High": "rating-veryhigh",
};

function collectForm(form) {
  const payload = {};
  const errors = [];

  form.querySelectorAll("[aria-invalid]").forEach(function (n) {
    n.removeAttribute("aria-invalid");
  });

  Object.keys(NUMERIC_FIELDS).forEach(function (name) {
    const node = form.elements[name];
    const value = node.value.trim();
    const num = Number(value);
    if (value === "" || isNaN(num)) {
      errors.push({ name: name, message: NUMERIC_FIELDS[name] + " must be a number." });
    } else if (num < Number(node.min) || num > Number(node.max)) {
      errors.push({
        name: name,
        message: NUMERIC_FIELDS[name] + " must be between " + node.min + " and " + node.max + ".",
      });
    } else {
      payload[name] = num;
    }
  });

  Object.keys(SELECT_FIELDS).forEach(function (name) {
    const node = form.elements[name];
    if (!node.value) {
      errors.push({ name: name, message: "Please choose " + SELECT_FIELDS[name].toLowerCase() + "." });
    } else {
      payload[name] = node.value;
    }
  });

  payload.region = form.elements["region"].value.trim();
  return { payload: payload, errors: errors };
}

function showErrors(errors, form) {
  const box = document.getElementById("form-error");
  box.textContent = "";
  box.appendChild(el("p", null,
    errors.length === 1 ? "Please fix 1 problem:" : "Please fix " + errors.length + " problems:"));
  const list = el("ul");
  errors.forEach(function (err) {
    list.appendChild(el("li", null, err.message));
    const field = form.elements[err.name];
    if (field) field.setAttribute("aria-invalid", "true");
  });
  box.appendChild(list);
  box.hidden = false;
  box.focus();
}

function clearErrors() {
  const box = document.getElementById("form-error");
  box.hidden = true;
  box.textContent = "";
}

function renderResult(result) {
  const badge = document.getElementById("rating-badge");
  badge.className = "rating-badge " + (RATING_CLASS[result.rating] || "");
  document.getElementById("rating-value").textContent = result.rating;
  document.getElementById("rating-explanation").textContent = result.rating_explanation;
  document.getElementById("per-capita-total").textContent =
    result.per_capita_annual_kg.toLocaleString();
  document.getElementById("total-annual").textContent =
    result.total_annual_kg.toLocaleString();

  let maxVal = 1;
  Object.keys(CATEGORY_LABELS).forEach(function (key) {
    if (result.breakdown[key] > maxVal) maxVal = result.breakdown[key];
  });

  const bars = document.getElementById("breakdown-bars");
  bars.textContent = "";
  bars.setAttribute("aria-hidden", "true");
  Object.keys(CATEGORY_LABELS).forEach(function (key) {
    const rowEl = el("div", "bar-row");
    rowEl.appendChild(el("span", "bar-label", CATEGORY_LABELS[key]));
    const track = el("div", "bar-track");
    const fill = el("div", "bar-fill");
    fill.style.width = Math.round((result.breakdown[key] / maxVal) * 100) + "%";
    track.appendChild(fill);
    rowEl.appendChild(track);
    rowEl.appendChild(el("span", "bar-value", result.breakdown[key].toLocaleString()));
    bars.appendChild(rowEl);
  });

  const body = document.getElementById("breakdown-body");
  body.textContent = "";
  Object.keys(CATEGORY_LABELS).forEach(function (key) {
    const tr = el("tr");
    const th = el("th", null, CATEGORY_LABELS[key]);
    th.scope = "row";
    tr.appendChild(th);
    tr.appendChild(el("td", null, result.breakdown[key].toLocaleString()));
    const delta = result.feature_contributions[key];
    const above = delta > 0;
    const deltaCell = el("td", above ? "delta-above" : "delta-below");
    deltaCell.textContent =
      (above ? "+" : "") + delta.toLocaleString() + " kg " +
      (delta === 0 ? "(average)" : above ? "(above avg)" : "(below avg)");
    tr.appendChild(deltaCell);
    body.appendChild(tr);
  });

  const list = document.getElementById("insights-list");
  list.textContent = "";
  if (!result.insights.length) {
    list.appendChild(el("li", null,
      "Your footprint is already low across the board - keep it up!"));
  }
  result.insights.forEach(function (insight) {
    const li = el("li", "insight");
    const title = el("p", "insight-title", insight.title);
    title.appendChild(el("span", "insight-saving",
      "~" + insight.annual_saving_kg.toLocaleString() + " kg/yr"));
    li.appendChild(title);
    li.appendChild(el("p", null, insight.detail));
    li.appendChild(el("p", "insight-reason", "Why: " + insight.reason));
    list.appendChild(li);
  });

  const section = document.getElementById("results");
  section.hidden = false;
  section.classList.add("reveal");
  const heading = document.getElementById("results-heading");
  heading.setAttribute("tabindex", "-1");
  heading.focus();
}

async function handleFormSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  clearErrors();

  const collected = collectForm(form);
  if (collected.errors.length) {
    showErrors(collected.errors, form);
    return;
  }

  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  button.textContent = "Calculating...";

  try {
    const result = await fetchJson("/api/assess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collected.payload),
    });
    if (!result.data) {
      showErrors([{ name: "", message: staleServerMessage(result.status) }], form);
      return;
    }
    if (!result.ok) {
      showErrors([{ name: "", message: result.data.error || "Request failed." }], form);
      return;
    }
    renderResult(result.data);
  } catch (err) {
    showErrors([{ name: "", message: offlineMessage() }], form);
  } finally {
    button.disabled = false;
    button.textContent = "Get my insights";
  }
}

/* ---------------------------------------------------------------------------
 * Wire up
 * ------------------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("chat-form").addEventListener("submit", handleChatSubmit);
  document.getElementById("footprint-form").addEventListener("submit", handleFormSubmit);

  addBubble("assistant",
    "Hi, I am Terra. Ask me anything about carbon footprints - travel, food, " +
    "home energy, recycling, offsetting and more.");
  loadSuggestions();
});
