# 🎬 FunnelBot: 2-Minute Recruiter Walkthrough Script

> **Goal**: Demonstrate full-stack engineering proficiency, clean architecture, zero-budget local NLP, state machine flow management, and business impact in under 120 seconds.

---

## ⚡ The 15-Second Elevator Pitch

> *"FunnelBot is a zero-budget social media automation engine. It converts Instagram and Telegram comments into qualified sales leads using local NLP—fuzzy Levenshtein matching and TF-IDF vectors—so it runs entirely free in under 50MB of RAM without paid APIs. I built it with an adapter architecture so any channel can plug in, and a live visual simulator so you can test it right now with zero login."*

---

## ⏱️ The 120-Second Chronological Demo Script

### Phase 1: The Hook & Comment Trigger (0:00 – 0:30)
1. **Open the Demo**: Open `http://localhost:8000` (or your deployed URL).
2. **Show the Dual-Screen Setup**:
   - Point to the left panel: *"This simulates an Instagram feed post."*
   - Point to the middle panel: *"This simulates the prospect's direct message inbox."*
   - Point to the right panel: *"This is the real-time Engine Inspector exposing the internal telemetry."*
3. **Trigger with a Typo**:
   - In the post comment box, type a deliberate typo: `send me the giude please` and press **Enter** (or click **Comment**).
4. **Talking Points**:
   - *"Notice how the engine used RapidFuzz to match the keyword 'GUIDE' with 90%+ similarity despite the typo."*
   - *"The post automatically receives an organic public reply from a randomized template to avoid algorithmic spam flags."*
   - *"Simultaneously, a private DM was dispatched to start our automated qualification funnel."*
   - *Point to the Engine Inspector: "Here you can see the NormalizedEvent, the matched rule ID, and the exact match confidence."*

---

### Phase 2: Qualification State Machine & Scoring (0:30 – 1:00)
1. **Answer Step 1 (Goal)**:
   - Click the quick reply button: `1. Lead Generation Funnel` (or type `1`).
2. **Answer Step 2 (Budget)**:
   - Click the quick reply button: `3. $5,000 - $10,000+` (or type `3`).
3. **Answer Step 3 (Timeline)**:
   - Click the quick reply button: `1. Immediately / Within 2 weeks` (or type `1`).
4. **Talking Points**:
   - *"The conversation state is tracked through a persistent state machine with a 24-hour expiration window."*
   - *Look at the Engine Inspector: "Notice the Lead Score accumulating. High-budget and immediate-timeline choices carry higher point weights (+30 and +25 points)."*

---

### Phase 3: The Wow Factor — FAQ Interruption & Auto-Recovery (1:00 – 1:30)
1. **Interrupt the Funnel**:
   - The bot is currently asking: *"What's the best email address to send your plan?"*
   - Instead of typing an email, simulate a distracted lead by asking a business question:
     ```
     How much does this cost?
     ```
     *(or: `Do you offer a free trial?` or `Is there a money-back guarantee?`)*
2. **Observe the Reaction**:
   - The engine recognizes this is an FAQ query, computes the TF-IDF cosine similarity ($> 0.55$), and answers it immediately.
   - Then, without human intervention, it recovers its previous state:
     ```
     Back to where we were: What's the best email address to send your tailored strategy and booking link?
     ```
3. **Complete the Lead Capture**:
   - Type a valid email: `alex@techscale.io`
4. **Talking Points**:
   - *"Most bots completely lose conversation state when interrupted. FunnelBot intercepts the FAQ using local scikit-learn TF-IDF vector similarity, answers it, and recovers the pending qualification step seamlessly."*
   - *"The email is validated with strict regex. Because the accumulated score exceeded 70 points, the lead was classified as HOT and immediately served an exclusive Cal.com scheduling link."*

---

### Phase 4: Admin Dashboard, Analytics & Multi-Channel Proof (1:30 – 2:00)
1. **Switch to Analytics**:
   - Click the **📊 Analytics** icon in the sidebar dock (or press `/` and click Analytics).
   - Show the live Chart.js metrics: total comments triggered, DMs dispatched, overall conversion rate, and lead tier doughnut chart (`HOT`, `WARM`, `COLD`).
2. **Show the Lead CRM**:
   - Click the **👥 Leads** icon.
   - Filter by `HOT` to see `alex@techscale.io` with full metadata and score breakdown.
   - Click **Download CSV** to demonstrate export capability for HubSpot/Salesforce ingestion.
3. **Show Knowledge Base**:
   - Click the **💬 FAQ Knowledge** icon.
   - Type a query into the live **TF-IDF Test Sandbox** (e.g., `can i cancel anytime?`) to show the real-time cosine score and match confidence.
4. **Mention Telegram / Production Adapter**:
   - *"Beyond the simulator, the Telegram adapter is fully implemented. The exact same engine powers live bots on Telegram via webhooks with custom keyboards, and includes an Instagram Graph API dev stub ready for production app review."*

---

## 🎯 Cheat Sheet: Answers to Tough Technical Questions

### Q1: "Why did you use local TF-IDF instead of calling OpenAI or Claude?"
> **Answer**:
> 1. **Zero Cost**: OpenAI embeddings and LLM prompts cost money on every user keystroke. TF-IDF is 100% free.
> 2. **Sub-millisecond Latency**: Local cosine vector calculation runs in `< 2 milliseconds`, compared to 500–2,000ms for network LLM roundtrips.
> 3. **Determinism & Explainability**: In sales funnels, hallucination is unacceptable. If a customer asks about a refund policy, TF-IDF returns the exact vetted answer with a calibrated confidence score.
> 4. **RAM Efficiency**: Deep neural models require gigabytes of GPU/RAM. Our TF-IDF vectorizer runs smoothly in under 50MB of RAM, making it deployable on free-tier containers.

---

### Q2: "How does the architecture prevent tight coupling to Instagram?"
> **Answer**:
> *"We apply the Adapter Pattern with a unified `NormalizedEvent` contract:
> `Inbound Channel` $\rightarrow$ `Adapter.normalize_inbound()` $\rightarrow$ `NormalizedEvent` $\rightarrow$ `FunnelEngine` $\rightarrow$ `EngineAction` $\rightarrow$ `Adapter.send_action()`.
> The core engine has zero dependencies on Telegram or Instagram APIs. Adding a new channel like WhatsApp Business or Discord only requires writing one adapter class without touching a single line of funnel logic."*

---

### Q3: "How do you handle rate limiting, abuse, and opt-outs?"
> **Answer**:
> 1. **Rate Limiting**: `SlowAPI` guards public endpoints (60 req/min).
> 2. **Cooldown Windows**: Per-user, per-rule cooldown locks prevent comment flooding.
> 3. **Global Opt-Out**: If a user types `STOP` or `unsubscribe`, an `OptOutDB` record is saved and the engine immediately halts all outbound messages across all channels.
> 4. **Human Takeover**: Typing `human` or `agent` flags the conversation for manual takeover and suppresses auto-replies.

---

### Q4: "How does the database scale from prototype to enterprise?"
> **Answer**:
> *"We use `SQLModel`, which is built directly on SQLAlchemy 2.0 and Pydantic v2. For development and zero-budget demos, it runs on local SQLite. In production, swapping to a managed PostgreSQL cluster (like Neon, Supabase, or AWS RDS) requires changing only one environment variable (`DATABASE_URL=postgresql://...`) with zero code alterations."*
