/**
 * attemptEventBus.js — PR2b client-side telemetry bus.
 *
 * Delivery contract (hardened per PR #796 / #800 review):
 *   - Durable per-attempt queue persisted to sessionStorage (`mae_q_<attemptId>`).
 *     Events are cleared ONLY after a confirmed server ACK and replayed on the
 *     next lifecycle, so unload/visibility flushes cannot silently lose data.
 *   - The events endpoint returns `{accepted, duplicates, rejected:[{seq,reason}]}`
 *     with HTTP 200 even when individual rows fail (`reason: "db_error"`). We
 *     parse that body and retain only retryable (`db_error`) sequences; accepted,
 *     duplicate, and permanently-rejected (validation) sequences are removed.
 *   - Batches are chunked to <= MAX_BATCH (100, matching the server) with a
 *     keepalive byte-size guard, so a backlog can never wedge on HTTP 413.
 *   - Each batch is bound to an immutable (attemptId, epoch). A route/attempt
 *     switch during an in-flight flush never posts old events to a new attempt
 *     nor removes new-attempt events via overlapping sequence numbers.
 *   - The unload-safe path uses fetch({keepalive:true}) with the cached bearer
 *     token (sendBeacon cannot attach Authorization → 401) and relies on the
 *     durable queue + server idempotency for at-least-once delivery.
 *
 * All enqueue and flush operations are wrapped in try/catch — event bus
 * failures must never throw into the attempt flow.
 */

const RING_SIZE       = 200;
const FLUSH_INTERVAL  = 5_000;   // ms
const FLUSH_THRESHOLD = 25;      // events
const HEARTBEAT_MS    = 15_000;  // ms
const MAX_BATCH       = 100;     // must match server MAX_BATCH (413 over this)
const MAX_FLUSH_BYTES = 50_000;  // keepalive byte-size guard per request
const SEQ_KEY_PREFIX  = "mae_seq_";
const QUEUE_KEY_PREFIX = "mae_q_";

export class AttemptEventBus {
  constructor() {
    this._attemptId      = null;
    this._apiBase        = null;
    this._getAuthToken   = null;
    this._cachedToken    = null;   // last known bearer token — used by the unload-safe beacon path
    this._inFlight       = false;  // guards against overlapping _flush() calls
    this._epoch          = 0;      // bumped on every init() — binds a batch to one attempt lifecycle
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
      // New attempt lifecycle: bind subsequent batches to a fresh epoch and
      // never carry the prior attempt's ring/token into this one.
      this._epoch += 1;
      this._attemptId           = attemptId;
      this._apiBase             = apiBase;
      this._getAuthToken        = getAuthToken;
      this._cachedToken         = null;
      this._getClientRemaining  = getClientRemaining  || (() => null);
      this._getServerRemaining  = getServerRemaining  || (() => null);

      // Restore monotonic counter across page reloads (per attempt).
      const stored = this._safeStorageGet(SEQ_KEY_PREFIX + attemptId);
      this._seq = stored ? (parseInt(stored, 10) || 0) : 0;

      // Replay any durably-persisted-but-unacked events for THIS attempt only.
      this._ring = this._loadQueue(attemptId);

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

      // Drain any replayed backlog promptly.
      if (this._ring.length) this._flush();
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
      // Best-effort unload flush. The durable queue is NOT cleared here — it
      // replays on the next init() for this attempt; the server dedupes any
      // events the beacon already delivered.
      this._flushBeacon();
    } catch (e) {
      console.warn("[EventBus] destroy error:", e);
    }
  }

  // ── public enqueue ──────────────────────────────────────────────────────────

  enqueue(eventType, payload = {}) {
    try {
      if (!this._attemptId) return;
      const seq = ++this._seq;
      this._safeStorageSet(SEQ_KEY_PREFIX + this._attemptId, String(seq));

      const event = {
        event_type:  eventType,
        sequence_no: seq,
        occurred_at: new Date().toISOString(),
        payload,
      };

      if (this._ring.length >= RING_SIZE) {
        this._ring.shift();  // drop oldest when buffer is full (bounded backpressure)
      }
      this._ring.push(event);
      this._saveQueue(this._attemptId, this._ring);  // durable mirror

      if (this._ring.length >= FLUSH_THRESHOLD) {
        this._flush();
      }
    } catch (e) {
      console.warn("[EventBus] enqueue error:", e);
    }
  }

  /**
   * Emit the submit-boundary marker carrying the final monotonic sequence_no, so
   * the telemetry-quality gate can detect trailing event loss (a declared final
   * seq greater than the max observed seq). Call immediately before the
   * pre-submit flush.
   */
  markSubmitFlush() {
    try {
      // The marker takes the next sequence number; declare it as the final seq.
      this.enqueue("attempt.submit_flush", { final_sequence_no: this._seq + 1 });
    } catch (e) {
      console.warn("[EventBus] submit_flush mark error:", e);
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

  // ── durable queue (sessionStorage, per attempt) ──────────────────────────────

  _queueKey(attemptId) {
    return QUEUE_KEY_PREFIX + attemptId;
  }

  _safeStorageGet(key) {
    try {
      return sessionStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  _safeStorageSet(key, value) {
    try {
      sessionStorage.setItem(key, value);
    } catch (e) {
      /* storage full / unavailable — in-memory ring still carries the events */
    }
  }

  _loadQueue(attemptId) {
    try {
      const raw = this._safeStorageGet(this._queueKey(attemptId));
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  _saveQueue(attemptId, events) {
    if (!attemptId) return;
    this._safeStorageSet(this._queueKey(attemptId), JSON.stringify(events || []));
  }

  /** Remove the given sequence numbers from the durable queue for an attempt
   *  WITHOUT clobbering events enqueued concurrently (re-read, filter, write). */
  _ackRemoveFromQueue(attemptId, removeSeqs) {
    const cur = this._loadQueue(attemptId).filter((e) => !removeSeqs.has(e.sequence_no));
    this._saveQueue(attemptId, cur);
    return cur;
  }

  /** A response is a valid ACK only if every submitted event is accounted for
   *  exactly once: accepted + duplicates + rejected.length === chunk.length,
   *  with non-negative integer counts and every rejected seq belonging to the
   *  chunk. A malformed/empty/incomplete 200 is treated as NO ack. */
  _isValidAck(body, chunk) {
    if (!body || typeof body !== "object") return false;
    const { accepted, duplicates, rejected } = body;
    if (!Number.isInteger(accepted) || accepted < 0) return false;
    if (!Number.isInteger(duplicates) || duplicates < 0) return false;
    if (!Array.isArray(rejected)) return false;
    const chunkSeqs = new Set(chunk.map((e) => e.sequence_no));
    for (const r of rejected) {
      if (!r || !chunkSeqs.has(r.seq)) return false;  // every rejected seq must belong to the chunk
    }
    return accepted + duplicates + rejected.length === chunk.length;
  }

  /** Build the next chunk: <= MAX_BATCH events and <= MAX_FLUSH_BYTES serialized
   *  (always at least one event so a single large event still makes progress). */
  _buildChunk(events) {
    const chunk = [];
    let bytes = 12; // {"events":[]}
    for (const e of events) {
      if (chunk.length >= MAX_BATCH) break;
      const sz = JSON.stringify(e).length + 1;
      if (chunk.length > 0 && bytes + sz > MAX_FLUSH_BYTES) break;
      chunk.push(e);
      bytes += sz;
    }
    return chunk;
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

  /**
   * Public: drain the durable queue and RESOLVE once it is empty (all events
   * ACKed), the bounded deadline passes, or a transient failure stalls progress.
   * Used by the submit path so final buffered events (the last question.visited /
   * answered) are delivered and persisted BEFORE the server computes analytics.
   * Best-effort and time-bounded — never blocks the user's submit indefinitely.
   * Returns true iff the queue is fully drained.
   */
  async flushAndWait({ timeoutMs = 4000 } = {}) {
    try {
      if (!this._attemptId) return true;
      const start = Date.now();
      // Let any in-flight flush settle first.
      while (this._inFlight && Date.now() - start < timeoutMs) {
        await new Promise((r) => setTimeout(r, 25));
      }
      // Drain chunk batches until empty, stalled (no progress), or timed out.
      while (this._ring.length && Date.now() - start < timeoutMs) {
        const before = this._ring.length;
        await this._flush();
        if (this._ring.length >= before) break;  // transient failure — stop, do not spin
      }
      return this._ring.length === 0;
    } catch (e) {
      console.warn("[EventBus] flushAndWait error:", e);
      return false;
    }
  }

  async _flush() {
    if (this._inFlight) return;  // do not send overlapping batches
    if (!this._ring.length || !this._attemptId) return;
    this._inFlight = true;
    // Bind this flush to an immutable attempt + epoch. A route switch mid-flush
    // (destroy()+init()) bumps _epoch and _attemptId; we must never post this
    // attempt's events to another attempt, nor mutate the new attempt's ring.
    const attemptId = this._attemptId;
    const apiBase   = this._apiBase;
    const epoch     = this._epoch;
    try {
      // Drain chunk-by-chunk; stop on the first non-success or retryable reject.
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const isCurrent = this._epoch === epoch && this._attemptId === attemptId;
        const source = isCurrent ? this._ring : this._loadQueue(attemptId);
        if (!source.length) break;

        const chunk = this._buildChunk(source);
        if (!chunk.length) break;
        const chunkSeqs = new Set(chunk.map((e) => e.sequence_no));

        const token = await this._refreshToken();
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        let resp;
        try {
          resp = await fetch(`${apiBase}/${attemptId}/events`, {
            method:  "POST",
            headers,
            body:    JSON.stringify({ events: chunk }),
            keepalive: true,
          });
        } catch (e) {
          console.warn("[EventBus] flush network error (events retained):", e);
          break;
        }

        if (!resp || !resp.ok) {
          if (resp && resp.status === 409) {
            // Terminal: the attempt is past its submit grace and will NEVER
            // accept events again. Retrying forever would pin the durable queue
            // and sessionStorage, so quarantine (discard) this attempt's queue.
            console.warn(`[EventBus] attempt terminal (409); discarding ${chunk.length}+ un-ingestable events for ${attemptId}`);
            if (this._epoch === epoch && this._attemptId === attemptId) this._ring = [];
            this._saveQueue(attemptId, []);
            break;
          }
          // 401/5xx (and an unexpected 413 — but chunks are bounded): retain and
          // retry on the next tick rather than dropping events.
          console.warn(`[EventBus] flush rejected (status ${resp && resp.status}); ${chunk.length} events retained`);
          break;
        }

        // HTTP 200 — parse and VALIDATE the per-event ACK contract. A truncated,
        // empty, non-JSON, or incomplete-accounting 200 is NOT a valid ACK and
        // must not clear events (otherwise a partial-response edge silently loses
        // telemetry). Only on a fully-accounted ACK do we remove sequences.
        let body = null;
        try { body = await resp.json(); } catch (e) { body = null; }
        if (!this._isValidAck(body, chunk)) {
          console.warn(`[EventBus] 200 with invalid/incomplete ACK; ${chunk.length} events retained`);
          break;
        }
        // Retain only retryable (db_error) sequences; accepted / duplicate /
        // permanently-rejected (validation) sequences are removed.
        const retrySeqs = new Set(
          body.rejected
            .filter((r) => typeof r.reason === "string" && r.reason.includes("db_error"))
            .map((r) => r.seq),
        );
        const removeSeqs = new Set([...chunkSeqs].filter((s) => !retrySeqs.has(s)));

        // Clear acked / duplicate / permanently-rejected seqs; retain retryable
        // (db_error) ones.
        if (this._epoch === epoch && this._attemptId === attemptId) {
          this._ring = this._ring.filter((e) => !removeSeqs.has(e.sequence_no));
          this._saveQueue(attemptId, this._ring);  // keep durable mirror in sync
        } else {
          // A route switch landed mid-flush — update only the durable queue for
          // the ORIGINAL attempt; never touch the new attempt's live ring.
          this._ackRemoveFromQueue(attemptId, removeSeqs);
        }

        // If the chunk left retryable events, stop this pass so we don't
        // hot-loop; the timer retries them on the next tick. Otherwise the
        // top-of-loop length check drives draining of the next chunk.
        if (retrySeqs.size) break;
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
   * sendBeacon cannot attach. Fire-and-forget; the durable queue is NOT cleared
   * here (it replays on the next init(); the server dedupes any delivered rows).
   */
  _flushBeacon() {
    try {
      if (!this._ring.length || !this._attemptId) return;
      const token = this._cachedToken;
      if (!token) {
        // An unauthenticated beacon would be rejected (401). Skip the request;
        // the durable queue replays on the next authenticated lifecycle.
        console.warn("[EventBus] beacon flush deferred: no cached auth token (queue persisted)");
        return;
      }
      const chunk = this._buildChunk(this._ring);
      // Best-effort, fire-and-forget. Do NOT clear the ring/queue: we cannot
      // confirm the ACK during unload, so durability + server idempotency
      // provide at-least-once delivery on the next lifecycle.
      fetch(`${this._apiBase}/${this._attemptId}/events`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ events: chunk }),
        keepalive: true,
      })
        .then((r) => {
          if (!r || !r.ok) console.warn(`[EventBus] beacon flush rejected (status ${r && r.status})`);
        })
        .catch((e) => console.warn("[EventBus] beacon flush error:", e));
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
