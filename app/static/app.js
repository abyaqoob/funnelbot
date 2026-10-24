/**
 * FunnelBot - Interactive Social Funnel Simulator Client
 */

class FunnelSimulator {
  constructor() {
    this.userId = "recruiter_demo";
    this.username = "recruiter";
    this.postId = "post_demo_1";
    this.activeFlowStep = null;
    this.leadScore = 0;

    // DOM Elements
    this.commentsList = document.getElementById("commentsList");
    this.commentForm = document.getElementById("commentForm");
    this.commentInput = document.getElementById("commentInput");

    this.dmContainer = document.getElementById("dmContainer");
    this.dmForm = document.getElementById("dmForm");
    this.dmInput = document.getElementById("dmInput");

    this.resetBtn = document.getElementById("resetBtn");
    this.toastContainer = document.getElementById("toastContainer");

    // Inspector Elements
    this.matchedRuleEl = document.getElementById("matchedRule");
    this.matchedKeywordEl = document.getElementById("matchedKeyword");
    this.faqQuestionEl = document.getElementById("faqQuestion");
    this.faqScoreEl = document.getElementById("faqScore");
    this.faqConfidenceBadge = document.getElementById("faqConfidenceBadge");
    this.flowStepEl = document.getElementById("flowStep");
    this.leadScoreEl = document.getElementById("leadScore");
    this.leadTierEl = document.getElementById("leadTier");
    this.scoreBar = document.getElementById("scoreBar");
    this.consoleLogs = document.getElementById("consoleLogs");
    this.systemStatusEl = document.getElementById("systemStatus");

    this.init();
  }

  async init() {
    this.bindEvents();
    await this.checkHealth();
    this.logConsole("Simulator engine initialized. Ready for recruiter demo.");
  }

  bindEvents() {
    // Comment Submission
    this.commentForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = this.commentInput.value.trim();
      if (!text) return;
      this.commentInput.value = "";
      this.handleUserComment(text);
    });

    // DM Submission
    this.dmForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = this.dmInput.value.trim();
      if (!text) return;
      this.dmInput.value = "";
      this.handleUserDM(text);
    });

    // Reset Demo Button
    this.resetBtn.addEventListener("click", () => this.resetDemo());

    // Quick Trigger Chips in Comment Box
    document.querySelectorAll(".comment-quick-trigger").forEach((btn) => {
      btn.addEventListener("click", () => {
        const text = btn.getAttribute("data-text");
        this.commentInput.value = text;
        this.commentForm.dispatchEvent(new Event("submit"));
      });
    });

    // Quick Action Chips in DM Box
    document.querySelectorAll(".dm-quick-trigger").forEach((btn) => {
      btn.addEventListener("click", () => {
        const text = btn.getAttribute("data-text");
        this.dmInput.value = text;
        this.dmForm.dispatchEvent(new Event("submit"));
      });
    });
  }

  async checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        this.systemStatusEl.innerHTML = `<span class="status-dot"></span> System Operational (${data.database})`;
      }
    } catch (err) {
      this.systemStatusEl.innerHTML = `<span class="status-dot" style="background:#ef4444;box-shadow:0 0 8px #ef4444;"></span> Offline`;
    }
  }

  async handleUserComment(text) {
    // 1. Render user comment immediately in Instagram post
    this.appendUserComment(this.username, text);

    this.logConsole(`[Inbound Comment] @${this.username}: "${text}"`);

    try {
      const response = await fetch("/api/simulator/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: "simulator",
          event_type: "comment",
          user_id: this.userId,
          username: this.username,
          text: text,
          post_id: this.postId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const result = await response.json();
      this.updateInspector(result.inspector_info);

      // 2. Dispatch actions
      if (result.actions && result.actions.length > 0) {
        for (const action of result.actions) {
          if (action.action_type === "reply_comment") {
            this.appendBotCommentReply(action.text);
          } else if (action.action_type === "send_dm") {
            this.showTypingIndicator();
            setTimeout(() => {
              this.hideTypingIndicator();
              this.appendBotDM(action.text, action.quick_replies);
            }, 450);
          }
        }
      } else {
        this.logConsole("Comment processed: No actions fired (cooldown or no matching rule).");
      }
    } catch (err) {
      this.showToast(`Error processing comment: ${err.message}`);
      this.logConsole(`[Error] ${err.message}`);
    }
  }

  async handleUserDM(text) {
    // 1. Render user message in DM chat
    this.appendUserDM(text);
    this.removeQuickReplies();

    this.logConsole(`[Inbound DM] @${this.username}: "${text}"`);

    // Show typing indicator
    this.showTypingIndicator();

    try {
      const response = await fetch("/api/simulator/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: "simulator",
          event_type: "dm",
          user_id: this.userId,
          username: this.username,
          text: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const result = await response.json();
      this.hideTypingIndicator();
      this.updateInspector(result.inspector_info);

      // Process Actions
      if (result.actions && result.actions.length > 0) {
        for (const action of result.actions) {
          if (action.action_type === "send_dm") {
            this.appendBotDM(action.text, action.quick_replies);
          } else if (action.action_type === "notify") {
            this.logConsole(`🔔 [Admin Notification] ${action.text}`);
          } else if (action.action_type === "tag_lead") {
            this.showToast(`Lead tagged as ${action.text}!`);
          }
        }
      }
    } catch (err) {
      this.hideTypingIndicator();
      this.showToast(`Error sending DM: ${err.message}`);
      this.logConsole(`[Error] ${err.message}`);
    }
  }

  appendUserComment(author, text) {
    const item = document.createElement("div");
    item.className = "comment-item";
    item.innerHTML = `
      <div><span class="comment-author">@${author}</span> <span class="comment-text">${this.escapeHTML(text)}</span></div>
    `;
    this.commentsList.appendChild(item);
    this.commentsList.parentElement.scrollTop = this.commentsList.parentElement.scrollHeight;
  }

  appendBotCommentReply(text) {
    const reply = document.createElement("div");
    reply.className = "comment-reply";
    reply.innerHTML = `
      <span class="reply-tag">🤖 Growth Bot</span>
      <span>${this.escapeHTML(text)}</span>
    `;
    this.commentsList.appendChild(reply);
    this.commentsList.parentElement.scrollTop = this.commentsList.parentElement.scrollHeight;
  }

  appendUserDM(text) {
    const bubble = document.createElement("div");
    bubble.className = "dm-bubble dm-bubble-out";
    bubble.textContent = text;
    this.dmContainer.appendChild(bubble);
    this.dmContainer.scrollTop = this.dmContainer.scrollHeight;
  }

  appendBotDM(text, quickReplies = null) {
    const bubble = document.createElement("div");
    bubble.className = "dm-bubble dm-bubble-in";
    bubble.innerHTML = this.formatBotMessage(text);
    this.dmContainer.appendChild(bubble);

    // If quick reply buttons exist, render them
    if (quickReplies && quickReplies.length > 0) {
      const qGroup = document.createElement("div");
      qGroup.className = "quick-replies-group";
      quickReplies.forEach((choiceLabel) => {
        const btn = document.createElement("button");
        btn.className = "quick-reply-btn";
        btn.textContent = choiceLabel;
        btn.addEventListener("click", () => {
          this.handleUserDM(choiceLabel);
        });
        qGroup.appendChild(btn);
      });
      this.dmContainer.appendChild(qGroup);
    }

    this.dmContainer.scrollTop = this.dmContainer.scrollHeight;
  }

  showTypingIndicator() {
    this.hideTypingIndicator();
    const ind = document.createElement("div");
    ind.id = "typingIndicator";
    ind.className = "typing-indicator";
    ind.innerHTML = `
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    `;
    this.dmContainer.appendChild(ind);
    this.dmContainer.scrollTop = this.dmContainer.scrollHeight;
  }

  hideTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  removeQuickReplies() {
    document.querySelectorAll(".quick-replies-group").forEach((el) => el.remove());
  }

  updateInspector(info) {
    if (!info) return;

    // 1. Rule Match
    this.matchedRuleEl.textContent = info.matched_rule || "None";
    this.matchedKeywordEl.textContent = info.keyword_matched ? `"${info.keyword_matched}"` : "None";

    // 2. FAQ Similarity
    if (info.faq_match && info.faq_match.score > 0) {
      this.faqQuestionEl.textContent = info.faq_match.question || "None";
      const score = (info.faq_match.score * 100).toFixed(1);
      this.faqScoreEl.textContent = `${score}% (${info.faq_match.score})`;

      const conf = (info.faq_match.confidence || "low").toUpperCase();
      this.faqConfidenceBadge.textContent = conf;
      this.faqConfidenceBadge.className = `tier-badge ${
        conf === "HIGH" ? "tier-cold" : conf === "MEDIUM" ? "tier-warm" : "tier-hot"
      }`;
    } else {
      this.faqQuestionEl.textContent = "None";
      this.faqScoreEl.textContent = "0.00";
      this.faqConfidenceBadge.textContent = "IDLE";
      this.faqConfidenceBadge.className = "tier-badge";
    }

    // 3. Flow State
    if (info.flow_state) {
      const stepId = info.flow_state.current_step_id || info.flow_state.status || "idle";
      this.flowStepEl.textContent = stepId;
    } else {
      this.flowStepEl.textContent = "Idle";
    }

    // 4. Lead Score & Tier
    const score = info.lead_score || 0;
    this.leadScoreEl.textContent = `${score} pts`;
    this.scoreBar.style.width = `${Math.min(score, 100)}%`;

    if (info.lead_tier) {
      this.leadTierEl.textContent = info.lead_tier;
      this.leadTierEl.className = `tier-badge ${
        info.lead_tier === "HOT"
          ? "tier-hot"
          : info.lead_tier === "WARM"
          ? "tier-warm"
          : "tier-cold"
      }`;
    } else if (score >= 70) {
      this.leadTierEl.textContent = "HOT (Projected)";
      this.leadTierEl.className = "tier-badge tier-hot";
    } else if (score >= 40) {
      this.leadTierEl.textContent = "WARM (Projected)";
      this.leadTierEl.className = "tier-badge tier-warm";
    } else if (score > 0) {
      this.leadTierEl.textContent = "COLD (Projected)";
      this.leadTierEl.className = "tier-badge tier-cold";
    } else {
      this.leadTierEl.textContent = "None";
      this.leadTierEl.className = "tier-badge";
    }

    // 5. Append Execution Notes to Console
    if (info.execution_notes && info.execution_notes.length > 0) {
      info.execution_notes.forEach((note) => this.logConsole(`⚙️ ${note}`));
    }
  }

  logConsole(message) {
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.className = "console-entry";
    entry.innerHTML = `<span class="console-time">[${time}]</span> ${this.escapeHTML(message)}`;
    this.consoleLogs.appendChild(entry);
    this.consoleLogs.scrollTop = this.consoleLogs.scrollHeight;
  }

  async resetDemo() {
    try {
      const res = await fetch("/api/simulator/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.userId, channel: "simulator" }),
      });
      if (res.ok) {
        this.showToast("Demo user state reset! Ready for a fresh run.");
        this.resetUI();
        this.logConsole("Demo state wiped. Rules cooldown and opt-outs reset.");
      }
    } catch (err) {
      this.showToast("Failed to reset demo state.");
    }
  }

  resetUI() {
    // Reset comments
    this.commentsList.innerHTML = `
      <div class="comment-item">
        <div><span class="comment-author">@sarah_marketer</span> <span class="comment-text">Is this automation built with free tools?</span></div>
      </div>
      <div class="comment-item">
        <div><span class="comment-author">@growth_agency</span> <span class="comment-text">Looking forward to testing the qualification flow!</span></div>
      </div>
    `;

    // Reset DMs
    this.dmContainer.innerHTML = `
      <div class="dm-bubble dm-bubble-in">
        👋 Hey there! Comment on our post with <strong>GUIDE</strong>, <strong>PRICE</strong>, or <strong>LINK</strong> to start the live funnel, or ask any question here directly.
      </div>
    `;

    // Reset Inspector
    this.matchedRuleEl.textContent = "None";
    this.matchedKeywordEl.textContent = "None";
    this.faqQuestionEl.textContent = "None";
    this.faqScoreEl.textContent = "0.00";
    this.faqConfidenceBadge.textContent = "IDLE";
    this.faqConfidenceBadge.className = "tier-badge";
    this.flowStepEl.textContent = "Idle";
    this.leadScoreEl.textContent = "0 pts";
    this.leadTierEl.textContent = "None";
    this.leadTierEl.className = "tier-badge";
    this.scoreBar.style.width = "0%";
  }

  formatBotMessage(text) {
    let clean = this.escapeHTML(text);
    // Convert links into clickable anchors
    clean = clean.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" style="color:#60a5fa;text-decoration:underline;">$1</a>'
    );
    // Convert newlines to breaks
    return clean.replace(/\n/g, "<br>");
  }

  escapeHTML(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  showToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}

// Instantiate simulator once DOM loads
document.addEventListener("DOMContentLoaded", () => {
  window.simulator = new FunnelSimulator();
});
