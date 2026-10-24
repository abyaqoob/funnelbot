/**
 * FunnelBot - Multi-Channel Social Funnel & Admin Suite Client
 */

class FunnelApp {
  constructor() {
    this.userId = "recruiter_demo";
    this.username = "recruiter";
    this.postId = "post_demo_1";
    this.adminPassword = sessionStorage.getItem("adminPassword") || "";
    this.currentTab = "simulator";

    // Chart.js instances
    this.tierChart = null;
    this.dropoffChart = null;

    this.cacheElements();
    this.bindEvents();
    this.init();
  }

  cacheElements() {
    // Navigation
    this.dockItems = document.querySelectorAll(".dock-item");
    this.pillBtns = document.querySelectorAll(".pill-btn");
    this.viewPanels = document.querySelectorAll(".view-panel");
    this.pageTitle = document.getElementById("pageTitle");
    this.pageSubtitle = document.getElementById("pageSubtitle");
    this.systemStatusEl = document.getElementById("systemStatus");

    // Simulator Elements
    this.commentsList = document.getElementById("commentsList");
    this.commentForm = document.getElementById("commentForm");
    this.commentInput = document.getElementById("commentInput");
    this.dmContainer = document.getElementById("dmContainer");
    this.dmForm = document.getElementById("dmForm");
    this.dmInput = document.getElementById("dmInput");
    this.resetBtn = document.getElementById("resetBtn");

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

    // Admin Elements
    this.rulesTableBody = document.getElementById("rulesTableBody");
    this.faqsTableBody = document.getElementById("faqsTableBody");
    this.leadsTableBody = document.getElementById("leadsTableBody");
    this.leadTierFilter = document.getElementById("leadTierFilter");
    this.auditTableBody = document.getElementById("auditTableBody");
    this.flowJsonEditor = document.getElementById("flowJsonEditor");
    this.flowPreviewBox = document.getElementById("flowPreviewBox");

    // KPI Elements
    this.kpiComments = document.getElementById("kpiComments");
    this.kpiDMs = document.getElementById("kpiDMs");
    this.kpiLeads = document.getElementById("kpiLeads");
    this.kpiCompletion = document.getElementById("kpiCompletion");

    // Modals
    this.ruleModal = document.getElementById("ruleModal");
    this.faqModal = document.getElementById("faqModal");
    this.authModal = document.getElementById("authModal");
    this.authStatusText = document.getElementById("authStatusText");
    this.toastShelf = document.getElementById("toastShelf");
  }

  bindEvents() {
    // Dock Navigation Switching
    this.dockItems.forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        this.switchTab(tab);
      });
    });

    // Top Pill Switcher
    this.pillBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        this.switchTab(tab);
      });
    });

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

    // Reset Demo
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

    // Admin Auth Button
    document.getElementById("authBtn").addEventListener("click", () => {
      this.authModal.classList.add("open");
    });
    document.getElementById("authForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.adminPassword = document.getElementById("adminPasswordInput").value.trim();
      sessionStorage.setItem("adminPassword", this.adminPassword);
      this.updateAuthUI();
      this.authModal.classList.remove("open");
      this.showToast("Admin password saved for mutations.");
    });

    // Admin Modals & Action Buttons
    document.getElementById("addRuleBtn").addEventListener("click", () => {
      document.getElementById("ruleForm").reset();
      this.ruleModal.classList.add("open");
    });
    document.getElementById("ruleForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleCreateRule();
    });

    document.getElementById("addFAQBtn").addEventListener("click", () => {
      document.getElementById("faqForm").reset();
      this.faqModal.classList.add("open");
    });
    document.getElementById("faqForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleCreateFAQ();
    });

    document.getElementById("testFAQBtn").addEventListener("click", () => this.promptTestFAQ());
    document.getElementById("saveFlowBtn").addEventListener("click", () => this.handleSaveFlow());
    document.getElementById("refreshAnalyticsBtn").addEventListener("click", () => this.loadAnalytics());
    document.getElementById("refreshLogsBtn").addEventListener("click", () => this.loadAuditLogs());

    // Leads Tier Filter
    this.leadTierFilter.addEventListener("change", () => {
      this.loadLeads(this.leadTierFilter.value);
    });

    // Flow Editor Live Preview
    this.flowJsonEditor.addEventListener("input", () => this.renderFlowPreview());

    // Dock Action Shortcut
    document.getElementById("dockQuickActionBtn").addEventListener("click", () => {
      this.switchTab("simulator");
      this.commentInput.value = "GUIDE";
      this.commentInput.focus();
    });
  }

  async init() {
    this.updateAuthUI();
    await this.checkHealth();
    this.logConsole("FunnelBot engine ready. Connected to backend.");
  }

  getAuthHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (this.adminPassword) {
      headers["X-Admin-Password"] = this.adminPassword;
    }
    return headers;
  }

  updateAuthUI() {
    if (this.adminPassword) {
      this.authStatusText.textContent = "Unlocked 🔓";
      this.authStatusText.style.color = "#16a34a";
    } else {
      this.authStatusText.textContent = "Demo Mode";
      this.authStatusText.style.color = "var(--text-secondary)";
    }
  }

  async checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        this.systemStatusEl.innerHTML = `<span class="status-indicator"></span> Operational (${data.database})`;
      }
    } catch (err) {
      this.systemStatusEl.innerHTML = `<span class="status-indicator" style="background:#ef4444;box-shadow:0 0 6px #ef4444;"></span> Offline`;
    }
  }

  switchTab(tabName) {
    this.currentTab = tabName;

    // Update Dock Icons
    this.dockItems.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
    });

    // Update Pill Buttons
    this.pillBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
    });

    // Update View Panels
    this.viewPanels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `panel-${tabName}`);
    });

    // Update Page Title
    const titles = {
      simulator: ["All Channels", "Interactive Social Funnel Simulator (Instagram & DM Inbox)"],
      analytics: ["Funnel Analytics", "Performance Metrics, Completion Rates, and Lead Breakdown"],
      rules: ["Trigger Rules", "Keyword Triggers, RapidFuzz Matching, and Reply Templates"],
      faqs: ["FAQ Knowledge Base", "scikit-learn TF-IDF Cosine Similarity & Automated DM Answers"],
      flows: ["Flow Editor", "Multi-Step Lead Qualification State Machine & Scoring Logic"],
      leads: ["Captured Leads", "CRM Lead Records, Qualification Tiers, and CSV Export"],
      logs: ["Audit Logs", "Real-Time Conversation Events & Engine Telemetry Trail"],
    };

    if (titles[tabName]) {
      this.pageTitle.firstElementChild.textContent = titles[tabName][0];
      this.pageSubtitle.textContent = titles[tabName][1];
    }

    // Lazy load data for selected tab
    if (tabName === "analytics") this.loadAnalytics();
    else if (tabName === "rules") this.loadRules();
    else if (tabName === "faqs") this.loadFAQs();
    else if (tabName === "flows") this.loadFlow();
    else if (tabName === "leads") this.loadLeads();
    else if (tabName === "logs") this.loadAuditLogs();
  }

  // ==========================================
  // SIMULATOR ORCHESTRATION
  // ==========================================

  async handleUserComment(text) {
    this.appendUserComment(this.username, text);
    this.logConsole(`[Comment] @${this.username}: "${text}"`);

    try {
      const res = await fetch("/api/simulator/event", {
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

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const result = await res.json();
      this.updateInspector(result.inspector_info);

      if (result.actions && result.actions.length > 0) {
        for (const action of result.actions) {
          if (action.action_type === "reply_comment") {
            this.appendBotCommentReply(action.text);
          } else if (action.action_type === "send_dm") {
            this.showTypingIndicator();
            setTimeout(() => {
              this.hideTypingIndicator();
              this.appendBotDM(action.text, action.quick_replies);
            }, 350);
          }
        }
      } else {
        this.logConsole("Comment processed: Cooldown active or no rule matched.");
      }
    } catch (err) {
      this.showToast(`Error: ${err.message}`);
    }
  }

  async handleUserDM(text) {
    this.appendUserDM(text);
    this.removeQuickReplies();
    this.logConsole(`[DM] @${this.username}: "${text}"`);
    this.showTypingIndicator();

    try {
      const res = await fetch("/api/simulator/event", {
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

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const result = await res.json();
      this.hideTypingIndicator();
      this.updateInspector(result.inspector_info);

      if (result.actions && result.actions.length > 0) {
        for (const action of result.actions) {
          if (action.action_type === "send_dm") {
            this.appendBotDM(action.text, action.quick_replies);
          } else if (action.action_type === "notify") {
            this.logConsole(`🔔 [Admin Alert] ${action.text}`);
          } else if (action.action_type === "tag_lead") {
            this.showToast(`🎉 Lead Qualified as ${action.text}!`);
          }
        }
      }
    } catch (err) {
      this.hideTypingIndicator();
      this.showToast(`Error: ${err.message}`);
    }
  }

  appendUserComment(author, text) {
    const row = document.createElement("div");
    row.className = "comment-row";
    row.innerHTML = `<div><span class="comment-user">@${author}</span> <span>${this.escapeHTML(text)}</span></div>`;
    this.commentsList.appendChild(row);
    this.commentsList.scrollTop = this.commentsList.scrollHeight;
  }

  appendBotCommentReply(text) {
    const row = document.createElement("div");
    row.className = "bot-reply-pill";
    row.innerHTML = `<strong>🤖 Growth Bot:</strong> ${this.escapeHTML(text)}`;
    this.commentsList.appendChild(row);
    this.commentsList.scrollTop = this.commentsList.scrollHeight;
  }

  appendUserDM(text) {
    const bubble = document.createElement("div");
    bubble.className = "bubble bubble-out";
    bubble.textContent = text;
    this.dmContainer.appendChild(bubble);
    this.dmContainer.scrollTop = this.dmContainer.scrollHeight;
  }

  appendBotDM(text, quickReplies = null) {
    const bubble = document.createElement("div");
    bubble.className = "bubble bubble-in";
    bubble.innerHTML = this.formatBotMessage(text);
    this.dmContainer.appendChild(bubble);

    if (quickReplies && quickReplies.length > 0) {
      const qGroup = document.createElement("div");
      qGroup.className = "quick-choice-container";
      quickReplies.forEach((label) => {
        const btn = document.createElement("button");
        btn.className = "choice-pill";
        btn.textContent = label;
        btn.addEventListener("click", () => this.handleUserDM(label));
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
    ind.className = "typing-box";
    ind.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    this.dmContainer.appendChild(ind);
    this.dmContainer.scrollTop = this.dmContainer.scrollHeight;
  }

  hideTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  removeQuickReplies() {
    document.querySelectorAll(".quick-choice-container").forEach((el) => el.remove());
  }

  updateInspector(info) {
    if (!info) return;

    this.matchedRuleEl.textContent = info.matched_rule || "None";
    this.matchedKeywordEl.textContent = info.keyword_matched ? `"${info.keyword_matched}"` : "None";

    if (info.faq_match && info.faq_match.score > 0) {
      this.faqQuestionEl.textContent = info.faq_match.question || "None";
      const scorePct = (info.faq_match.score * 100).toFixed(1);
      this.faqScoreEl.textContent = `${scorePct}% (${info.faq_match.score})`;

      const conf = (info.faq_match.confidence || "low").toUpperCase();
      this.faqConfidenceBadge.textContent = conf;
      this.faqConfidenceBadge.className = `tier-pill ${conf === "HIGH" ? "cold" : conf === "MEDIUM" ? "warm" : "hot"}`;
    } else {
      this.faqQuestionEl.textContent = "None";
      this.faqScoreEl.textContent = "0.00";
      this.faqConfidenceBadge.textContent = "IDLE";
      this.faqConfidenceBadge.className = "tier-pill";
    }

    if (info.flow_state) {
      this.flowStepEl.textContent = info.flow_state.current_step_id || info.flow_state.status || "Idle";
    } else {
      this.flowStepEl.textContent = "Idle";
    }

    const score = info.lead_score || 0;
    this.leadScoreEl.textContent = `${score} pts`;
    this.scoreBar.style.width = `${Math.min(score, 100)}%`;

    if (info.lead_tier) {
      this.leadTierEl.textContent = info.lead_tier;
      this.leadTierEl.className = `tier-pill ${info.lead_tier.toLowerCase()}`;
    } else if (score >= 70) {
      this.leadTierEl.textContent = "HOT (Projected)";
      this.leadTierEl.className = "tier-pill hot";
    } else if (score >= 40) {
      this.leadTierEl.textContent = "WARM (Projected)";
      this.leadTierEl.className = "tier-pill warm";
    } else if (score > 0) {
      this.leadTierEl.textContent = "COLD (Projected)";
      this.leadTierEl.className = "tier-pill cold";
    } else {
      this.leadTierEl.textContent = "None";
      this.leadTierEl.className = "tier-pill";
    }

    if (info.execution_notes) {
      info.execution_notes.forEach((note) => this.logConsole(`⚙️ ${note}`));
    }
  }

  logConsole(msg) {
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.innerHTML = `<span style="color:#64748b;">[${time}]</span> ${this.escapeHTML(msg)}`;
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
        this.showToast("Demo state reset! Ready for a fresh run.");
        this.commentsList.innerHTML = `
          <div class="comment-row">
            <div><span class="comment-user">@sarah_growth</span> <span>Is this bot built with free tools?</span></div>
          </div>
          <div class="comment-row">
            <div><span class="comment-user">@saas_founder</span> <span>Testing the lead qualification flow!</span></div>
          </div>
        `;
        this.dmContainer.innerHTML = `
          <div class="bubble bubble-in">
            👋 Hey there! Comment <strong>GUIDE</strong>, <strong>PRICE</strong>, or <strong>LINK</strong> on our post, or ask any question here directly.
          </div>
        `;
        this.matchedRuleEl.textContent = "None";
        this.matchedKeywordEl.textContent = "None";
        this.faqQuestionEl.textContent = "None";
        this.faqScoreEl.textContent = "0.00";
        this.faqConfidenceBadge.textContent = "IDLE";
        this.flowStepEl.textContent = "Idle";
        this.leadScoreEl.textContent = "0 pts";
        this.leadTierEl.textContent = "None";
        this.scoreBar.style.width = "0%";
        this.logConsole("Demo wiped: Cooldowns, state, and opt-outs cleared.");
      }
    } catch (err) {
      this.showToast("Failed to reset demo.");
    }
  }

  // ==========================================
  // PHASE 4: ADMIN DASHBOARD DATA & CHARTS
  // ==========================================

  async loadAnalytics() {
    try {
      const res = await fetch("/api/admin/analytics", { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const data = await res.json();

      this.kpiComments.textContent = data.total_comments_triggered;
      this.kpiDMs.textContent = data.total_dms_received;
      this.kpiLeads.textContent = data.total_leads;
      this.kpiCompletion.textContent = `${data.completion_rate_percent}%`;

      this.renderCharts(data);
    } catch (err) {
      console.error("Analytics fetch error:", err);
    }
  }

  renderCharts(data) {
    if (typeof Chart === "undefined") return;

    // 1. Leads by Tier Doughnut Chart
    const ctxTier = document.getElementById("leadsTierChart");
    if (ctxTier) {
      if (this.tierChart) this.tierChart.destroy();
      const tiers = data.leads_by_tier || { HOT: 0, WARM: 0, COLD: 0 };
      this.tierChart = new Chart(ctxTier, {
        type: "doughnut",
        data: {
          labels: ["HOT 🔥", "WARM ⚡", "COLD 🌱"],
          datasets: [
            {
              data: [tiers.HOT || 0, tiers.WARM || 0, tiers.COLD || 0],
              backgroundColor: ["#ef4444", "#f59e0b", "#10b981"],
              borderWidth: 2,
              borderColor: "#ffffff",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom" } },
        },
      });
    }

    // 2. Funnel Drop-off Bar Chart
    const ctxDrop = document.getElementById("dropoffChart");
    if (ctxDrop) {
      if (this.dropoffChart) this.dropoffChart.destroy();
      const dropOff = data.funnel_drop_off || {};
      const labels = Object.keys(dropOff).length > 0 ? Object.keys(dropOff) : ["step_goal", "step_budget", "step_timeline", "completed"];
      const values = Object.keys(dropOff).length > 0 ? Object.values(dropOff) : [10, 8, 6, 5];

      this.dropoffChart = new Chart(ctxDrop, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Users at Step",
              data: values,
              backgroundColor: "#22c55e",
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }
  }

  async loadRules() {
    try {
      const res = await fetch("/api/admin/rules", { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const rules = await res.json();
      this.rulesTableBody.innerHTML = "";

      rules.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${this.escapeHTML(r.name)}</strong><br><small style="color:var(--text-muted);">${r.id}</small></td>
          <td>${r.keywords.map((k) => `<span class="chip-btn">${this.escapeHTML(k)}</span>`).join(" ")}</td>
          <td><span class="badge-subtle">${r.match_mode} (${r.fuzzy_threshold}%)</span></td>
          <td>${r.cooldown_seconds}s</td>
          <td><small>${r.reply_templates.length} template(s)</small></td>
          <td><span class="tier-pill cold">Active</span></td>
          <td>
            <button class="btn-header" style="padding:3px 8px; color:#dc2626;" onclick="window.app.deleteRule('${r.id}')">Delete</button>
          </td>
        `;
        this.rulesTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Rules fetch error:", err);
    }
  }

  async handleCreateRule() {
    const id = document.getElementById("ruleIdInput").value.trim();
    const name = document.getElementById("ruleNameInput").value.trim();
    const keywords = document.getElementById("ruleKeywordsInput").value.split(",").map((s) => s.trim()).filter(Boolean);
    const match_mode = document.getElementById("ruleMatchModeInput").value;
    const fuzzy_threshold = parseFloat(document.getElementById("ruleThresholdInput").value) || 80.0;
    const cooldown_seconds = parseInt(document.getElementById("ruleCooldownInput").value) || 3600;
    const templates = document.getElementById("ruleTemplatesInput").value.split("\n").map((s) => s.trim()).filter(Boolean);

    try {
      const res = await fetch("/api/admin/rules", {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          id,
          name,
          keywords,
          match_mode,
          fuzzy_threshold,
          cooldown_seconds,
          reply_templates: templates.length > 0 ? templates : ["Thanks @{username}! Just sent you a DM 📩"],
          flow_id: "lead_qualification",
          is_active: true,
        }),
      });

      if (res.status === 401) {
        this.showToast("Unauthorized: Enter admin password via key icon first.");
        return;
      }
      if (!res.ok) throw new Error("Failed to save rule.");

      this.showToast("Trigger rule created successfully!");
      this.ruleModal.classList.remove("open");
      this.loadRules();
    } catch (err) {
      this.showToast(err.message);
    }
  }

  async deleteRule(ruleId) {
    if (!confirm(`Delete rule "${ruleId}"?`)) return;
    try {
      const res = await fetch(`/api/admin/rules/${ruleId}`, {
        method: "DELETE",
        headers: this.getAuthHeaders(),
      });
      if (res.status === 401) {
        this.showToast("Admin password required to delete rules.");
        return;
      }
      this.showToast("Rule deleted.");
      this.loadRules();
    } catch (err) {
      this.showToast("Failed to delete rule.");
    }
  }

  async loadFAQs() {
    try {
      const res = await fetch("/api/admin/faqs", { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const faqs = await res.json();
      this.faqsTableBody.innerHTML = "";

      faqs.forEach((f) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><span class="badge-subtle">${this.escapeHTML(f.category)}</span></td>
          <td><strong>${this.escapeHTML(f.question)}</strong></td>
          <td><small style="color:var(--text-secondary);">${f.question_variants.map(v => this.escapeHTML(v)).join(" • ")}</small></td>
          <td style="max-width:320px;">${this.escapeHTML(f.answer)}</td>
          <td>
            <button class="btn-header" style="padding:3px 8px; color:#dc2626;" onclick="window.app.deleteFAQ('${f.id}')">Delete</button>
          </td>
        `;
        this.faqsTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("FAQs fetch error:", err);
    }
  }

  async handleCreateFAQ() {
    const id = document.getElementById("faqIdInput").value.trim();
    const category = document.getElementById("faqCategoryInput").value.trim() || "General";
    const question = document.getElementById("faqQuestionInput").value.trim();
    const variants = document.getElementById("faqVariantsInput").value.split("\n").map(s => s.trim()).filter(Boolean);
    const answer = document.getElementById("faqAnswerInput").value.trim();

    try {
      const res = await fetch("/api/admin/faqs", {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          id,
          category,
          question,
          question_variants: variants,
          answer,
          is_active: true,
        }),
      });

      if (res.status === 401) {
        this.showToast("Unauthorized: Enter admin password via key icon first.");
        return;
      }
      if (!res.ok) throw new Error("Failed to save FAQ.");

      this.showToast("FAQ added and TF-IDF index re-fitted!");
      this.faqModal.classList.remove("open");
      this.loadFAQs();
    } catch (err) {
      this.showToast(err.message);
    }
  }

  async deleteFAQ(faqId) {
    if (!confirm(`Delete FAQ "${faqId}"?`)) return;
    try {
      const res = await fetch(`/api/admin/faqs/${faqId}`, {
        method: "DELETE",
        headers: this.getAuthHeaders(),
      });
      if (res.status === 401) {
        this.showToast("Admin password required to delete FAQs.");
        return;
      }
      this.showToast("FAQ deleted.");
      this.loadFAQs();
    } catch (err) {
      this.showToast("Failed to delete FAQ.");
    }
  }

  async promptTestFAQ() {
    const q = prompt("Enter a test question to evaluate against TF-IDF index (e.g. 'How much do you charge?'):");
    if (!q) return;

    try {
      const res = await fetch("/api/simulator/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: "simulator",
          event_type: "dm",
          user_id: "faq_tester",
          username: "tester",
          text: q,
        }),
      });
      const data = await res.json();
      const match = data.inspector_info.faq_match;
      if (match) {
        alert(`TF-IDF Match Result:\n\nClosest FAQ: ${match.question}\nScore: ${(match.score * 100).toFixed(1)}%\nConfidence Tier: ${match.confidence.toUpperCase()}`);
      } else {
        alert("No FAQ matched above threshold.");
      }
    } catch (err) {
      alert(`Error testing query: ${err.message}`);
    }
  }

  async loadFlow() {
    try {
      const res = await fetch("/api/admin/flows/lead_qualification", { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const flow = await res.json();
      this.flowJsonEditor.value = JSON.stringify(flow, null, 2);
      this.renderFlowPreview();
    } catch (err) {
      console.error("Flow fetch error:", err);
    }
  }

  renderFlowPreview() {
    try {
      const flow = JSON.parse(this.flowJsonEditor.value);
      let html = `<h4 style="font-size:0.95rem; margin-bottom:10px;">${this.escapeHTML(flow.title)}</h4>`;
      html += `<p style="font-size:0.75rem; color:var(--text-muted); margin-bottom:14px;">Hot threshold: ${flow.hot_threshold} pts | Warm threshold: ${flow.warm_threshold} pts</p>`;

      flow.steps.forEach((s, idx) => {
        html += `
          <div style="background:var(--surface-subtle); border:1px solid var(--border-light); border-radius:10px; padding:12px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; font-weight:700; margin-bottom:4px;">
              <span>Step ${idx + 1}: ${this.escapeHTML(s.id)}</span>
              <span class="badge-subtle">${s.step_type}</span>
            </div>
            <p style="font-size:0.8rem; margin-bottom:6px;">"${this.escapeHTML(s.prompt)}"</p>
            ${s.choices ? s.choices.map(c => `<div style="font-size:0.75rem; color:var(--text-secondary); margin-left:8px;">• ${this.escapeHTML(c.label)} (<strong>+${c.points} pts</strong>)</div>`).join("") : ""}
          </div>
        `;
      });
      this.flowPreviewBox.innerHTML = html;
    } catch (e) {
      this.flowPreviewBox.innerHTML = `<div style="color:#dc2626; font-size:0.8rem;">⚠️ Invalid JSON syntax: ${e.message}</div>`;
    }
  }

  async handleSaveFlow() {
    try {
      const flow = JSON.parse(this.flowJsonEditor.value);
      const res = await fetch(`/api/admin/flows/${flow.id}`, {
        method: "PUT",
        headers: this.getAuthHeaders(),
        body: JSON.stringify(flow),
      });

      if (res.status === 401) {
        this.showToast("Unauthorized: Enter admin password via key icon first.");
        return;
      }
      if (!res.ok) throw new Error("Failed to save flow.");

      this.showToast("Qualification flow saved successfully!");
      this.renderFlowPreview();
    } catch (err) {
      this.showToast(`Error: ${err.message}`);
    }
  }

  async loadLeads(tierFilter = "") {
    try {
      let url = "/api/admin/leads";
      if (tierFilter) url += `?tier=${encodeURIComponent(tierFilter)}`;

      const res = await fetch(url, { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const leads = await res.json();
      this.leadsTableBody.innerHTML = "";

      if (leads.length === 0) {
        this.leadsTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:24px;">No captured leads yet. Complete the funnel walkthrough to qualify leads!</td></tr>';
        return;
      }

      leads.forEach((l) => {
        const tr = document.createElement("tr");
        const tierClass = l.tier.toLowerCase();
        const answersSummary = Object.entries(l.answers || {})
          .map(([k, v]) => `<strong>${k}:</strong> ${v}`)
          .join(" | ");

        tr.innerHTML = `
          <td><strong>@${this.escapeHTML(l.username || l.user_id)}</strong></td>
          <td>${l.email ? `<a href="mailto:${l.email}" style="color:#0284c7; font-weight:600;">${this.escapeHTML(l.email)}</a>` : '<span style="color:var(--text-muted);">None</span>'}</td>
          <td><strong>${l.score} pts</strong></td>
          <td><span class="tier-pill ${tierClass}">${l.tier}</span></td>
          <td><span class="badge-subtle">${l.channel}</span></td>
          <td style="font-size:0.75rem; color:var(--text-secondary); max-width:280px;">${answersSummary}</td>
          <td><small style="color:var(--text-muted);">${new Date(l.created_at).toLocaleString()}</small></td>
        `;
        this.leadsTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Leads fetch error:", err);
    }
  }

  async loadAuditLogs() {
    try {
      const res = await fetch("/api/admin/conversations?limit=25", { headers: this.getAuthHeaders() });
      if (!res.ok) return;
      const logs = await res.json();
      this.auditTableBody.innerHTML = "";

      logs.forEach((log) => {
        const tr = document.createElement("tr");
        const actionsSummary = (log.actions || []).map((a) => a.action_type).join(", ");
        const inspectorSummary = log.inspector
          ? `${log.inspector.matched_rule || ""} | Score: ${log.inspector.lead_score || 0} pts`
          : "";

        tr.innerHTML = `
          <td><small style="color:var(--text-muted);">${new Date(log.timestamp).toLocaleTimeString()}</small></td>
          <td><span class="badge-subtle">${log.event_type}</span></td>
          <td>@${this.escapeHTML(log.username || log.user_id)}</td>
          <td>"${this.escapeHTML(log.text)}"</td>
          <td><span class="badge-subtle" style="background:#e0f2fe; color:#0369a1;">${actionsSummary || "none"}</span></td>
          <td><small style="color:var(--text-secondary);">${this.escapeHTML(inspectorSummary)}</small></td>
        `;
        this.auditTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Audit logs fetch error:", err);
    }
  }

  formatBotMessage(text) {
    let clean = this.escapeHTML(text);
    clean = clean.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" style="color:#0284c7;font-weight:600;text-decoration:underline;">$1</a>'
    );
    return clean.replace(/\n/g, "<br>");
  }

  escapeHTML(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  showToast(msg) {
    const toast = document.createElement("div");
    toast.className = "toast-msg";
    toast.textContent = msg;
    this.toastShelf.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }
}

// Global initialization
document.addEventListener("DOMContentLoaded", () => {
  window.app = new FunnelApp();
});
