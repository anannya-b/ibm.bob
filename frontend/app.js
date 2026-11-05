/**
 * app.js – FinLit AI Frontend Logic
 * ===================================
 * Handles all chat interactions, API calls, calculator modals,
 * fraud warning display, and UI state management.
 */

// ===========================================================================
// Configuration
// ===========================================================================
// Auto-detect: use deployed Render URL in production, localhost in development
const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : "https://finlit-ai-backend.onrender.com";

// Generate or restore a session ID for conversation continuity
let sessionId = sessionStorage.getItem("finlit_session_id");
if (!sessionId) {
  sessionId = generateUUID();
  sessionStorage.setItem("finlit_session_id", sessionId);
}

// ===========================================================================
// DOM references
// ===========================================================================
const messagesArea   = document.getElementById("messagesArea");
const messageInput   = document.getElementById("messageInput");
const sendBtn        = document.getElementById("sendBtn");
const languageSelect = document.getElementById("languageSelect");
const fraudBanner    = document.getElementById("fraudBanner");
const statusDot      = document.getElementById("statusDot");
const statusText     = document.getElementById("statusText");

// ===========================================================================
// Initialisation
// ===========================================================================
document.addEventListener("DOMContentLoaded", () => {
  // Set welcome message timestamp
  const welcomeTime = document.getElementById("welcomeTime");
  if (welcomeTime) welcomeTime.textContent = formatTime(new Date());

  // Focus the input
  messageInput.focus();
});

// ===========================================================================
// Utility functions
// ===========================================================================

/** Generate a UUID v4 */
function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Format a Date object to HH:MM */
function formatTime(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Format a number as Indian currency (₹) */
function formatINR(amount) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Scroll the messages area to the bottom */
function scrollToBottom() {
  requestAnimationFrame(() => {
    messagesArea.scrollTop = messagesArea.scrollHeight;
  });
}

/** Auto-resize the textarea as the user types */
function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

/** Handle Enter key in the textarea */
function handleKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

/** Set the connection status indicator */
function setStatus(state) {
  statusDot.className = "status-dot " + state;
  const labels = { online: "Online", offline: "Offline", loading: "Thinking…" };
  statusText.textContent = labels[state] || state;
}

/**
 * Very basic Markdown-to-HTML renderer for bot responses.
 * Handles: **bold**, *italic*, bullet lists, numbered lists, line breaks.
 */
function renderMarkdown(text) {
  if (!text) return "";
  let html = text
    // Escape HTML special chars first
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // Bold
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Inline code
    .replace(/`(.+?)`/g, "<code>$1</code>");

  // Convert lines to paragraphs / list items
  const lines = html.split("\n");
  const parts = [];
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inList) { parts.push("</ul>"); inList = false; }
      continue;
    }
    if (/^[\-\*•] /.test(trimmed)) {
      if (!inList) { parts.push("<ul>"); inList = true; }
      parts.push(`<li>${trimmed.replace(/^[\-\*•] /, "")}</li>`);
    } else if (/^\d+\. /.test(trimmed)) {
      if (!inList) { parts.push("<ol>"); inList = true; }
      parts.push(`<li>${trimmed.replace(/^\d+\. /, "")}</li>`);
    } else {
      if (inList) { parts.push("</ul>"); inList = false; }
      parts.push(`<p>${trimmed}</p>`);
    }
  }
  if (inList) parts.push("</ul>");

  return parts.join("");
}

// ===========================================================================
// Chat functions
// ===========================================================================

/** Append a message bubble to the chat */
function appendMessage(role, text, extras = {}) {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "👤" : "🤖";

  const bubble = document.createElement("div");
  bubble.className = `msg-bubble ${role === "user" ? "user-bubble" : "bot-bubble"}`;

  if (role === "user") {
    // User messages are plain text
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
  } else {
    // Bot messages support markdown rendering
    bubble.innerHTML = renderMarkdown(text);
  }

  // Sources badge
  if (extras.sourcesUsed > 0 && role === "bot") {
    const badge = document.createElement("span");
    badge.className = "sources-badge";
    badge.textContent = `📚 ${extras.sourcesUsed} knowledge source${extras.sourcesUsed > 1 ? "s" : ""} used`;
    bubble.appendChild(badge);
  }

  // Timestamp
  const time = document.createElement("span");
  time.className = "msg-time";
  time.textContent = formatTime(new Date());
  bubble.appendChild(time);

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesArea.appendChild(row);
  scrollToBottom();
  return row;
}

/** Show a typing indicator while waiting for the bot response */
function showTyping() {
  const row = document.createElement("div");
  row.className = "msg-row bot";
  row.id = "typingIndicator";

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = "🤖";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble bot-bubble";

  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("div");
    dot.className = "typing-dot";
    indicator.appendChild(dot);
  }

  bubble.appendChild(indicator);
  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesArea.appendChild(row);
  scrollToBottom();
}

/** Remove the typing indicator */
function removeTyping() {
  const indicator = document.getElementById("typingIndicator");
  if (indicator) indicator.remove();
}

/** Show the fraud warning banner */
function showFraudWarning(fraudData) {
  if (!fraudData || !fraudData.is_suspicious) return;

  document.getElementById("fraudWarningTitle").textContent =
    fraudData.severity === "high" ? "🚨 High Alert – Possible Scam!" : "⚠️ Caution – Suspicious Content";
  document.getElementById("fraudWarningMsg").textContent = fraudData.warning;

  const tipsList = document.getElementById("fraudTipsList");
  tipsList.innerHTML = "";
  (fraudData.tips || []).forEach((tip) => {
    const li = document.createElement("li");
    li.textContent = tip;
    tipsList.appendChild(li);
  });

  fraudBanner.classList.remove("hidden");
  fraudBanner.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/** Hide the fraud warning banner */
function closeFraudBanner() {
  fraudBanner.classList.add("hidden");
}

/** Main send message function */
async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;

  const language = languageSelect.value;

  // Disable input during request
  sendBtn.disabled = true;
  messageInput.disabled = true;
  setStatus("loading");
  closeFraudBanner();

  // Display user message
  appendMessage("user", message);

  // Clear and reset input
  messageInput.value = "";
  messageInput.style.height = "auto";

  // Show typing indicator
  showTyping();

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        language,
        session_id: sessionId,
      }),
    });

    removeTyping();

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();

    // Update session ID in case server generated a new one
    if (data.session_id) {
      sessionId = data.session_id;
      sessionStorage.setItem("finlit_session_id", sessionId);
    }

    // Display bot response
    appendMessage("bot", data.response, { sourcesUsed: data.sources_used || 0 });

    // Show fraud warning if detected
    if (data.fraud_warning && data.fraud_warning.is_suspicious) {
      showFraudWarning(data.fraud_warning);
    }

    setStatus("online");

  } catch (error) {
    removeTyping();
    console.error("Chat error:", error);

    appendMessage(
      "bot",
      `I'm having trouble connecting to the server right now. Please make sure the backend is running on \`${API_BASE}\`.\n\nError: ${error.message}`,
    );
    setStatus("offline");
  } finally {
    sendBtn.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
  }
}

/** Pre-fill and send a quick action message */
function quickAction(message) {
  messageInput.value = message;
  autoResize(messageInput);
  messageInput.focus();
  // Small delay for UX — user can see it being filled
  setTimeout(sendMessage, 100);
}

/** Clear the chat and start a new session */
async function clearChat() {
  if (!confirm("Clear all messages and start a new session?")) return;

  // Clear UI
  messagesArea.innerHTML = "";
  closeFraudBanner();

  // Clear server-side session
  try {
    await fetch(`${API_BASE}/session/${sessionId}`, { method: "DELETE" });
  } catch (_) { /* ignore */ }

  // New session
  sessionId = generateUUID();
  sessionStorage.setItem("finlit_session_id", sessionId);

  // Show fresh welcome message
  const welcomeRow = document.createElement("div");
  welcomeRow.className = "msg-row bot";
  welcomeRow.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble bot-bubble">
      <p>👋 Chat cleared! How can I help you with your financial questions today?</p>
      <span class="msg-time">${formatTime(new Date())}</span>
    </div>
  `;
  messagesArea.appendChild(welcomeRow);
  setStatus("online");
}

// ===========================================================================
// Modal management
// ===========================================================================

function openModal(modalId) {
  document.getElementById(modalId).classList.remove("hidden");
  // Reset results
  const resultId = modalId.replace("Modal", "Result");
  const result = document.getElementById(resultId);
  if (result) result.classList.add("hidden");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

function closeModalOnOverlay(event, modalId) {
  if (event.target.id === modalId) closeModal(modalId);
}

// ===========================================================================
// Budget Calculator
// ===========================================================================

async function loadBudgetCalculator() {
  const incomeInput = document.getElementById("incomeInput");
  const resultDiv   = document.getElementById("budgetResult");
  const income      = parseFloat(incomeInput.value);

  if (!income || income <= 0) {
    incomeInput.focus();
    incomeInput.style.borderColor = "#ef4444";
    setTimeout(() => incomeInput.style.borderColor = "", 1500);
    return;
  }

  resultDiv.innerHTML = "<p style='color:#64748b;font-size:13px'>Calculating…</p>";
  resultDiv.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/budget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monthly_income: income }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    resultDiv.innerHTML = renderBudgetResult(data);

    // Animate bars after DOM renders
    requestAnimationFrame(() => {
      document.querySelector(".budget-bar-fill.needs").style.width = "50%";
      document.querySelector(".budget-bar-fill.wants").style.width = "30%";
      document.querySelector(".budget-bar-fill.savings").style.width = "20%";
    });

  } catch (err) {
    resultDiv.innerHTML = `<p style='color:#ef4444;font-size:13px'>Error: ${err.message}</p>`;
  }
}

function renderBudgetResult(data) {
  const { needs, wants, savings, tips } = data;

  const tipsHtml = tips && tips.length
    ? `<div class="budget-tip-section">
         <h4>💡 Personalized Tips</h4>
         <ul>${tips.map(t => `<li>${escapeHtml(t)}</li>`).join("")}</ul>
       </div>`
    : "";

  return `
    <div class="budget-row">
      <div class="budget-label-row">
        <span class="budget-cat-name">🏠 Needs (Essential)</span>
        <span><span class="budget-amount">${formatINR(needs.amount)}</span><span class="budget-pct">(50%)</span></span>
      </div>
      <div class="budget-bar-track"><div class="budget-bar-fill needs" style="width:0%"></div></div>
      <div class="budget-examples">${needs.examples.slice(0, 3).join(" · ")}</div>
    </div>
    <div class="budget-row">
      <div class="budget-label-row">
        <span class="budget-cat-name">🎉 Wants (Lifestyle)</span>
        <span><span class="budget-amount">${formatINR(wants.amount)}</span><span class="budget-pct">(30%)</span></span>
      </div>
      <div class="budget-bar-track"><div class="budget-bar-fill wants" style="width:0%"></div></div>
      <div class="budget-examples">${wants.examples.slice(0, 3).join(" · ")}</div>
    </div>
    <div class="budget-row">
      <div class="budget-label-row">
        <span class="budget-cat-name">💰 Savings & Investments</span>
        <span><span class="budget-amount">${formatINR(savings.amount)}</span><span class="budget-pct">(20%)</span></span>
      </div>
      <div class="budget-bar-track"><div class="budget-bar-fill savings" style="width:0%"></div></div>
      <div class="budget-examples">${savings.examples.slice(0, 3).join(" · ")}</div>
    </div>
    ${tipsHtml}
  `;
}

// ===========================================================================
// EMI Calculator
// ===========================================================================

async function loadEMICalculator() {
  const principal  = parseFloat(document.getElementById("principalInput").value);
  const rate       = parseFloat(document.getElementById("rateInput").value);
  const tenure     = parseInt(document.getElementById("tenureInput").value, 10);
  const resultDiv  = document.getElementById("emiResult");

  if (!principal || principal <= 0 || isNaN(rate) || rate < 0 || !tenure || tenure <= 0) {
    resultDiv.innerHTML = "<p style='color:#ef4444;font-size:13px'>Please fill in all fields with valid values.</p>";
    resultDiv.classList.remove("hidden");
    return;
  }

  resultDiv.innerHTML = "<p style='color:#64748b;font-size:13px'>Calculating…</p>";
  resultDiv.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/emi`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ principal, rate, tenure_months: tenure }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    resultDiv.innerHTML = renderEMIResult(data);

  } catch (err) {
    resultDiv.innerHTML = `<p style='color:#ef4444;font-size:13px'>Error: ${err.message}</p>`;
  }
}

function renderEMIResult(data) {
  const interestRatio = data.total_interest / data.principal;
  const interestBar = Math.min(100, Math.round(interestRatio * 50)); // visual scale

  return `
    <div class="emi-result-grid">
      <div class="emi-card highlight" style="grid-column:1/-1">
        <div class="emi-card-label">Monthly EMI</div>
        <div class="emi-card-value">${formatINR(data.emi)}</div>
        <div class="emi-card-sub">per month for ${data.tenure_months} months</div>
      </div>
      <div class="emi-card">
        <div class="emi-card-label">Total Payment</div>
        <div class="emi-card-value" style="font-size:15px">${formatINR(data.total_payment)}</div>
      </div>
      <div class="emi-card">
        <div class="emi-card-label">Total Interest</div>
        <div class="emi-card-value" style="font-size:15px;color:#ef4444">${formatINR(data.total_interest)}</div>
      </div>
    </div>
    <div class="emi-summary">
      <strong>Interest is ${data.interest_percentage}% of principal.</strong><br>
      You borrow ${formatINR(data.principal)} and repay ${formatINR(data.total_payment)} total.
      The extra ${formatINR(data.total_interest)} is the cost of the loan.
    </div>
  `;
}

// ===========================================================================
// Utility: HTML escape
// ===========================================================================
function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
