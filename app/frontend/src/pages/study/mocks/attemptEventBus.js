/**
 * attemptEventBus.js — PR2b client-side telemetry bus.
 *
 * Responsibilities:
 *   - In-memory ring buffer (max 200 events)
 *   - Monotonic sequence_no, persisted to sessionStorage per attempt
 *   - Flush triggers: every 5 s OR buffer >= 25 events
 *   - Flush on visibilitychange→hidden via fetch({keepalive}) (authenticated,
 *     fire-and-forget) — sendBeacon cannot attach the required Authorization
 *     header, so beacon batches would be rejected (401) and lost
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

export class AttemptEventBus {
  constructor() {
    this._attemptId      = null;
    this._apiBase        = null;
    this._getAuthToken   = null;
    this._cachedToken    = null;   // last known bearer token — used by the unload-safe beacon path
    this._inFlight       = false;  // guards against overlapping _flush() calls
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

      // Prime the token cache so the unload-safe beacon path has an
      // Authorization token available before the first scheduled flush.
      this._refreshToken();
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

  /**
   * Resolve the current bearer token and cache it for the unload-safe beacon
   * path (which cannot await). Never throws.
   */
  async _refreshToken() {
    try {
      if (!this._getAuthToken) return this._cachedToken;
      const t = await this._getAuthToken();
      if (t) this._cachedToken = t;
      return t || this._cachedToken;
    } catch (e) {
      console.warn("[EventBus] token refresh error:", e);
      return this._cachedToken;
    }
  }

  async _flush() {
    if (this._inFlight) return;  // do not send overlapping batches
    try {
      if (!this._ring.length || !this._attemptId) return;
      this._inFlight = true;

      // Snapshot the batch but RETAIN it until the server acknowledges — a
      // 401/409/5xx or network error must not silently drop events.
      const batch = this._ring.slice(0);
      const token = await this._refreshToken();

      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resp = await fetch(`${this._apiBase}/${this._attemptId}/events`, {
        method:  "POST",
        headers,
        body:    JSON.stringify({ events: batch }),
        keepalive: true,
      });

      if (resp && resp.ok) {
        // Remove only the acknowledged events by sequence_no (robust against
        // concurrent enqueues/drops during the await).
        const sent = new Set(batch.map((e) => e.sequence_no));
        this._ring = this._ring.filter((e) => !sent.has(e.sequence_no));
      } else {
        console.warn(
          `[EventBus] flush rejected (status ${resp && resp.status}); ` +
          `${batch.length} events retained for retry`,
        );
      }
    } catch (e) {
      console.warn("[EventBus] flush error (events retained):", e);
    } finally {
      this._inFlight = false;
    }
  }

  /**
   * Unload-safe flush — used on visibilitychange→hidden and destroy().
   * Uses fetch({keepalive:true}) rather than navigator.sendBeacon: the events
   * endpoint requires an Authorization header (get_current_user → 401), which
   * sendBeacon cannot attach. Fire-and-forget; survives page unload.
   */
  _flushBeacon() {
    try {
      if (!this._ring.length || !this._attemptId) return;
      const token = this._cachedToken;
      if (!token) {
        // An unauthenticated beacon would be rejected (401) and the batch
        // lost; retain it for the next authenticated flush instead.
        console.warn("[EventBus] beacon flush deferred: no cached auth token");
        return;
      }
      const batch = this._ring.slice(0);
      fetch(`${this._apiBase}/${this._attemptId}/events`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ events: batch }),
        keepalive: true,
      })
        .then((r) => {
          if (!r || !r.ok) console.warn(`[EventBus] beacon flush rejected (status ${r && r.status})`);
        })
        .catch((e) => console.warn("[EventBus] beacon flush error:", e));

      const sent = new Set(batch.map((e) => e.sequence_no));
      this._ring = this._ring.filter((e) => !sent.has(e.sequence_no));
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
