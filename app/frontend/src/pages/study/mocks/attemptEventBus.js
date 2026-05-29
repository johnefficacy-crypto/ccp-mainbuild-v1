/**
 * attemptEventBus.js — PR2b client-side telemetry bus.
 *
 * Responsibilities:
 *   - In-memory ring buffer (max 200 events)
 *   - Monotonic sequence_no, persisted to sessionStorage per attempt
 *   - Flush triggers: every 5 s OR buffer >= 25 events
 *   - Flush on visibilitychange→hidden via navigator.sendBeacon (fire-and-forget)
 *   - Heartbeat every 15 s
 *   - DOM listeners: visibilitychange, focus/blur, copy, paste
 *
 * All enqueue and flush operations are wrapped in try/catch — event bus
 * failures must never throw into the attempt flow.
 */

const RING_SIZE       = 200;
const FLUSH_INTERVAL  = 5_000;   // ms
const FLUSH_THRESHOLD = 25;      // events
const HEARTBEAT_MS    = 15_000;  // ms
const SEQ_KEY_PREFIX  = "mae_seq_";

class AttemptEventBus {
  constructor() {
    this._attemptId      = null;
    this._apiBase        = null;
    this._getAuthToken   = null;
    this._ring           = [];
    this._seq            = 0;
    this._flushTimer     = null;
    this._heartbeatTimer = null;
    this._getServerRemaining = null;  // () => number|null — injected by shell
    this._clientRemaining    = null;  // () => number|null — injected by shell
    this._bound = {
      onVisibility: this._onVisibility.bind(this),
      onFocus:      this._onFocus.bind(this),
      onBlur:       this._onBlur.bind(this),
      onCopy:       this._onCopy.bind(this),
      onPaste:      this._onPaste.bind(this),
    };
  }

  // ── public init/teardown ────────────────────────────────────────────────────

  /**
   * @param {object} opts
   * @param {string}   opts.attemptId
   * @param {string}   opts.apiBase          - e.g. "/api/study/mocks/attempts"
   * @param {function} opts.getAuthToken      - () => Promise<string|null>
   * @param {function} [opts.getClientRemaining]  - () => number|null (seconds)
   * @param {function} [opts.getServerRemaining]  - () => number|null (seconds)
   */
  init({ attemptId, apiBase, getAuthToken, getClientRemaining, getServerRemaining }) {
    try {
      this._attemptId           = attemptId;
      this._apiBase             = apiBase;
      this._getAuthToken        = getAuthToken;
      this._getClientRemaining  = getClientRemaining  || (() => null);
      this._getServerRemaining  = getServerRemaining  || (() => null);

      // Restore monotonic counter across page reloads.
      const stored = sessionStorage.getItem(SEQ_KEY_PREFIX + attemptId);
      this._seq = stored ? (parseInt(stored, 10) || 0) : 0;

      document.addEventListener("visibilitychange", this._bound.onVisibility);
      window.addEventListener("focus", this._bound.onFocus);
      window.addEventListener("blur",  this._bound.onBlur);
      document.addEventListener("copy",  this._bound.onCopy);
      document.addEventListener("paste", this._bound.onPaste);

      this._flushTimer     = setInterval(() => this._flush(),     FLUSH_INTERVAL);
      this._heartbeatTimer = setInterval(() => this._heartbeat(), HEARTBEAT_MS);
    } catch (e) {
      console.warn("[EventBus] init error:", e);
    }
  }

  destroy() {
    try {
      clearInterval(this._flushTimer);
      clearInterval(this._heartbeatTimer);
      document.removeEventListener("visibilitychange", this._bound.onVisibility);
      window.removeEventListener("focus", this._bound.onFocus);
      window.removeEventListener("blur",  this._bound.onBlur);
      document.removeEventListener("copy",  this._bound.onCopy);
      document.removeEventListener("paste", this._bound.onPaste);
      this._flushBeacon();  // drain remaining buffer on unmount
    } catch (e) {
      console.warn("[EventBus] destroy error:", e);
    }
  }

  // ── public enqueue ──────────────────────────────────────────────────────────

  enqueue(eventType, payload = {}) {
    try {
      const seq = ++this._seq;
      sessionStorage.setItem(SEQ_KEY_PREFIX + this._attemptId, String(seq));

      const event = {
        event_type:  eventType,
        sequence_no: seq,
        occurred_at: new Date().toISOString(),
        payload,
      };

      if (this._ring.length >= RING_SIZE) {
        this._ring.shift();  // drop oldest when buffer is full
      }
      this._ring.push(event);

      if (this._ring.length >= FLUSH_THRESHOLD) {
        this._flush();
      }
    } catch (e) {
      console.warn("[EventBus] enqueue error:", e);
    }
  }

  // ── DOM listeners ───────────────────────────────────────────────────────────

  _onVisibility() {
    try {
      if (document.visibilityState === "hidden") {
        this.enqueue("attempt.tab_blurred", { at_question_id: this._currentQ() });
        this._flushBeacon();
      } else {
        this.enqueue("attempt.tab_focused", {
          at_question_id: this._currentQ(),
          away_for_ms: null,  // PR3 can compute via timestamps
        });
      }
    } catch (e) {
      console.warn("[EventBus] visibility error:", e);
    }
  }

  _onFocus() {
    try {
      this.enqueue("attempt.tab_focused", { at_question_id: this._currentQ(), away_for_ms: null });
    } catch (e) {
      console.warn("[EventBus] focus error:", e);
    }
  }

  _onBlur() {
    try {
      this.enqueue("attempt.tab_blurred", { at_question_id: this._currentQ() });
    } catch (e) {
      console.warn("[EventBus] blur error:", e);
    }
  }

  _onCopy() {
    try {
      this.enqueue("attempt.copy", { at_question_id: this._currentQ() });
    } catch (e) {
      console.warn("[EventBus] copy error:", e);
    }
  }

  _onPaste() {
    try {
      this.enqueue("attempt.paste", { at_question_id: this._currentQ() });
    } catch (e) {
      console.warn("[EventBus] paste error:", e);
    }
  }

  _heartbeat() {
    try {
      this.enqueue("attempt.heartbeat", {
        client_remaining_sec:          this._getClientRemaining(),
        server_remaining_sec_last_seen: this._getServerRemaining(),
      });
    } catch (e) {
      console.warn("[EventBus] heartbeat error:", e);
    }
  }

  // ── flush ───────────────────────────────────────────────────────────────────

  async _flush() {
    try {
      if (!this._ring.length || !this._attemptId) return;
      const batch = this._ring.splice(0);
      const token = this._getAuthToken ? await this._getAuthToken() : null;

      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      await fetch(`${this._apiBase}/${this._attemptId}/events`, {
        method:  "POST",
        headers,
        body:    JSON.stringify({ events: batch }),
        keepalive: true,
      });
    } catch (e) {
      console.warn("[EventBus] flush error:", e);
    }
  }

  /**
   * Synchronous beacon flush — used on visibilitychange→hidden and destroy().
   * navigator.sendBeacon is fire-and-forget and survives page unload.
   */
  _flushBeacon() {
    try {
      if (!this._ring.length || !this._attemptId) return;
      const batch = this._ring.splice(0);
      const url   = `${this._apiBase}/${this._attemptId}/events`;
      const blob  = new Blob(
        [JSON.stringify({ events: batch })],
        { type: "application/json" },
      );
      navigator.sendBeacon(url, blob);
    } catch (e) {
      console.warn("[EventBus] beacon error:", e);
    }
  }

  // ── internal state helpers (injected by shell) ──────────────────────────────

  _currentQuestionId = null;

  setCurrentQuestionId(qid) {
    this._currentQuestionId = qid;
  }

  _currentQ() {
    return this._currentQuestionId;
  }
}

// Singleton — one bus per page.
export const eventBus = new AttemptEventBus();
