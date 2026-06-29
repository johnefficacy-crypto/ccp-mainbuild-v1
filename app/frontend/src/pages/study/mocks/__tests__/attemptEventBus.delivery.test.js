/**
 * attemptEventBus — delivery / durability / isolation regression tests.
 *
 * Covers the PR #796 + #800 review requirements:
 *   - authenticated keepalive delivery (sendBeacon cannot send the auth header)
 *   - retain-until-ACK with the real {accepted,duplicates,rejected} contract
 *     (retain only retryable db_error sequences)
 *   - durable per-attempt sessionStorage queue + replay (unload-safe)
 *   - batch chunking <= MAX_BATCH so a backlog can never wedge on HTTP 413
 *   - immutable attempt/epoch isolation across destroy→re-init and in-flight
 *     route switches
 *   - stale-token 401 → refresh → retry
 */
import { AttemptEventBus } from "../attemptEventBus";

function makeBus({ token = "tok123", attemptId = "att1", apiBase = "/api/study/mocks/attempts" } = {}) {
  const bus = new AttemptEventBus();
  bus._attemptId = attemptId;
  bus._apiBase = apiBase;
  bus._getAuthToken = jest.fn(async () => token);
  return bus;
}

// Seed the live ring AND the durable mirror (mirrors what enqueue() does).
function seedRing(bus, events) {
  bus._ring = events.slice();
  bus._saveQueue(bus._attemptId, bus._ring);
}

function ok(body = { accepted: 0, duplicates: 0, rejected: [] }) {
  return { ok: true, status: 200, json: async () => body };
}

function evs(n, startSeq = 1) {
  return Array.from({ length: n }, (_, i) => ({
    sequence_no: startSeq + i,
    event_type: "question.visited",
    occurred_at: "2026-01-01T00:00:00+00:00",
    payload: { question_id: `q${startSeq + i}` },
  }));
}

beforeEach(() => {
  jest.spyOn(console, "warn").mockImplementation(() => {});
  sessionStorage.clear();
});

afterEach(() => {
  jest.restoreAllMocks();
  delete global.fetch;
});

describe("_flush ack contract", () => {
  test("clears the ring on a clean 200 and sends Bearer auth + keepalive", async () => {
    global.fetch = jest.fn(async () => ok({ accepted: 2, duplicates: 0, rejected: [] }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    await bus._flush();

    expect(bus._ring).toHaveLength(0);
    expect(bus._loadQueue("att1")).toHaveLength(0); // durable mirror cleared too
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/study/mocks/attempts/att1/events");
    expect(opts.keepalive).toBe(true);
    expect(opts.headers.Authorization).toBe("Bearer tok123");
  });

  test("retains all events on a non-ok response (e.g. 401)", async () => {
    global.fetch = jest.fn(async () => ({ ok: false, status: 401 }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    await bus._flush();

    expect(bus._ring).toHaveLength(2);
    expect(bus._loadQueue("att1")).toHaveLength(2);
  });

  test("retains events on a network error", async () => {
    global.fetch = jest.fn(async () => { throw new Error("network down"); });
    const bus = makeBus();
    seedRing(bus, evs(1));

    await bus._flush();

    expect(bus._ring).toHaveLength(1);
  });

  test("200 with a db_error reject retains ONLY the retryable seq; drops accepted + permanent rejects", async () => {
    // seq1 accepted, seq2 permanent (unknown event_type), seq3 transient db_error
    global.fetch = jest.fn(async () =>
      ok({
        accepted: 1,
        duplicates: 0,
        rejected: [
          { seq: 2, reason: "unknown event_type: 'foo'" },
          { seq: 3, reason: "db_error" },
        ],
      }),
    );
    const bus = makeBus();
    seedRing(bus, evs(3));

    await bus._flush();

    expect(bus._ring.map((e) => e.sequence_no)).toEqual([3]); // only the db_error seq retained
    expect(bus._loadQueue("att1").map((e) => e.sequence_no)).toEqual([3]);
  });

  test("does not send overlapping batches while a flush is in flight", async () => {
    global.fetch = jest.fn();
    const bus = makeBus();
    bus._inFlight = true;
    seedRing(bus, evs(1));

    await bus._flush();

    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("_flush ACK integrity (200 is not a blanket ACK)", () => {
  test("retains the batch when a 200 body is non-JSON / unparseable", async () => {
    global.fetch = jest.fn(async () => ({ ok: true, status: 200, json: async () => { throw new Error("Unexpected end of JSON input"); } }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    await bus._flush();

    expect(bus._ring).toHaveLength(2);
    expect(bus._loadQueue("att1")).toHaveLength(2);
  });

  test("retains the batch on an incomplete-accounting 200 (counts < chunk length)", async () => {
    // 2-event chunk but the server accounted for nothing.
    global.fetch = jest.fn(async () => ok({ accepted: 0, duplicates: 0, rejected: [] }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    await bus._flush();

    expect(bus._ring).toHaveLength(2);
  });

  test("retains the batch when a rejected seq does not belong to the chunk", async () => {
    global.fetch = jest.fn(async () => ok({ accepted: 1, duplicates: 0, rejected: [{ seq: 999, reason: "db_error" }] }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    await bus._flush();

    expect(bus._ring).toHaveLength(2);
  });

  test("clears the batch on a fully-accounted ACK (accepted + duplicates + rejected === chunk)", async () => {
    global.fetch = jest.fn(async () => ok({ accepted: 1, duplicates: 1, rejected: [] }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    await bus._flush();

    expect(bus._ring).toHaveLength(0);
  });
});

describe("_flush terminal 409 quarantine", () => {
  test("discards the attempt's durable queue on a 409 instead of retrying forever", async () => {
    global.fetch = jest.fn(async () => ({ ok: false, status: 409 }));
    const bus = makeBus();
    seedRing(bus, evs(3));

    await bus._flush();

    expect(global.fetch).toHaveBeenCalledTimes(1);     // no hot-retry loop
    expect(bus._ring).toHaveLength(0);                 // quarantined
    expect(bus._loadQueue("att1")).toHaveLength(0);
  });
});

describe("_flush chunking (HTTP 413 avoidance)", () => {
  test("a >100-event backlog is sent in bounded chunks of <= 100 and fully drains", async () => {
    const sizes = [];
    global.fetch = jest.fn(async (_url, opts) => {
      const { events } = JSON.parse(opts.body);
      sizes.push(events.length);
      return ok({ accepted: events.length, duplicates: 0, rejected: [] });
    });
    const bus = makeBus();
    seedRing(bus, evs(150));

    await bus._flush();

    expect(sizes).toEqual([100, 50]);          // never exceeds MAX_BATCH
    expect(sizes.every((n) => n <= 100)).toBe(true);
    expect(bus._ring).toHaveLength(0);          // backlog fully drained
  });

  test("recovers after a transient failure: first chunk retained, resent on next flush", async () => {
    let call = 0;
    global.fetch = jest.fn(async (_url, opts) => {
      const { events } = JSON.parse(opts.body);
      call += 1;
      if (call === 1) return { ok: false, status: 503 };
      return ok({ accepted: events.length, duplicates: 0, rejected: [] });
    });
    const bus = makeBus();
    seedRing(bus, evs(120));

    await bus._flush(); // 503 on first chunk → retained
    expect(bus._ring).toHaveLength(120);

    await bus._flush(); // recovers; drains both chunks
    expect(bus._ring).toHaveLength(0);
  });
});

describe("attempt/epoch isolation", () => {
  test("an in-flight flush posts to the ORIGINAL attempt and never touches the new attempt's ring", async () => {
    let resolveFetch;
    global.fetch = jest.fn(
      () => new Promise((res) => { resolveFetch = () => res(ok({ accepted: 1, duplicates: 0, rejected: [] })); }),
    );
    const bus = makeBus({ attemptId: "attOLD" });
    seedRing(bus, evs(1));

    const p = bus._flush();                 // binds to attOLD/epoch
    for (let i = 0; i < 20 && !resolveFetch; i++) await Promise.resolve();

    // Route switch mid-flight: same singleton re-init'd onto a new attempt.
    bus._epoch += 1;
    bus._attemptId = "attNEW";
    bus._ring = evs(1).map((e) => ({ ...e, sequence_no: 1 })); // new attempt, overlapping seq=1

    resolveFetch();
    await p;

    const [url] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/study/mocks/attempts/attOLD/events"); // posted to OLD attempt
    expect(bus._ring.map((e) => e.sequence_no)).toEqual([1]);     // new attempt's ring untouched
    expect(bus._loadQueue("attOLD")).toHaveLength(0);             // old durable queue cleared
  });
});

describe("durable persistence + replay across lifecycle", () => {
  test("init() replays a persisted unacked queue for the SAME attempt", () => {
    sessionStorage.setItem("mae_q_att1", JSON.stringify(evs(3)));
    global.fetch = jest.fn(() => new Promise(() => {})); // never resolves; we only check replay
    const bus = new AttemptEventBus();

    bus.init({ attemptId: "att1", apiBase: "/api/study/mocks/attempts", getAuthToken: async () => "t" });
    bus.destroy(); // stop timers

    expect(bus._ring.map((e) => e.sequence_no)).toEqual([1, 2, 3]);
  });

  test("init() on a DIFFERENT attempt does NOT replay the prior attempt's events", () => {
    sessionStorage.setItem("mae_q_attOLD", JSON.stringify(evs(2)));
    global.fetch = jest.fn(() => new Promise(() => {}));
    const bus = new AttemptEventBus();

    bus.init({ attemptId: "attNEW", apiBase: "/api/study/mocks/attempts", getAuthToken: async () => "t" });
    bus.destroy();

    expect(bus._ring).toHaveLength(0);                       // new attempt starts clean
    expect(bus._loadQueue("attOLD").map((e) => e.sequence_no)).toEqual([1, 2]); // old queue preserved
  });

  test("destroy() with no cached token retains the durable queue for later replay", () => {
    global.fetch = jest.fn();
    const bus = makeBus({ token: null });
    bus._cachedToken = null;
    seedRing(bus, evs(2));

    bus.destroy();

    expect(global.fetch).not.toHaveBeenCalled();             // no unauthenticated beacon
    expect(bus._loadQueue("att1")).toHaveLength(2);          // durable queue intact for replay
  });
});

describe("_flushBeacon (unload-safe)", () => {
  test("uses an authenticated keepalive fetch (not sendBeacon) and does NOT clear the durable queue", () => {
    global.fetch = jest.fn(() => Promise.resolve(ok()));
    navigator.sendBeacon = jest.fn();
    const bus = makeBus();
    bus._cachedToken = "tok123";
    seedRing(bus, evs(1));

    bus._flushBeacon();

    expect(navigator.sendBeacon).not.toHaveBeenCalled();
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/study/mocks/attempts/att1/events");
    expect(opts.keepalive).toBe(true);
    expect(opts.headers.Authorization).toBe("Bearer tok123");
    // Durability: events remain queued (cannot confirm ACK on unload).
    expect(bus._ring).toHaveLength(1);
    expect(bus._loadQueue("att1")).toHaveLength(1);
  });

  test("defers (no request, queue retained) when no auth token is cached", () => {
    global.fetch = jest.fn();
    const bus = makeBus();
    bus._cachedToken = null;
    seedRing(bus, evs(1));

    bus._flushBeacon();

    expect(global.fetch).not.toHaveBeenCalled();
    expect(bus._loadQueue("att1")).toHaveLength(1);
  });
});

describe("stale-token 401 → refresh → retry", () => {
  test("a 401 with a stale token is retained, then succeeds after the token refreshes", async () => {
    let token = "stale";
    global.fetch = jest.fn(async (_url, opts) => {
      const auth = opts.headers.Authorization;
      return auth === "Bearer fresh"
        ? ok({ accepted: 1, duplicates: 0, rejected: [] })
        : { ok: false, status: 401 };
    });
    const bus = makeBus();
    bus._getAuthToken = jest.fn(async () => token);
    seedRing(bus, evs(1));

    await bus._flush();            // stale → 401 → retained
    expect(bus._ring).toHaveLength(1);

    token = "fresh";              // session refreshed
    await bus._flush();            // fresh → 200 → cleared
    expect(bus._ring).toHaveLength(0);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});

describe("flushAndWait (pre-submit drain)", () => {
  test("resolves true after fully draining the queue", async () => {
    global.fetch = jest.fn(async (_url, opts) => {
      const { events } = JSON.parse(opts.body);
      return ok({ accepted: events.length, duplicates: 0, rejected: [] });
    });
    const bus = makeBus();
    seedRing(bus, evs(120)); // two chunks

    const drained = await bus.flushAndWait({ timeoutMs: 2000 });

    expect(drained).toBe(true);
    expect(bus._ring).toHaveLength(0);
  });

  test("resolves false (bounded, no hang) when delivery keeps failing", async () => {
    global.fetch = jest.fn(async () => ({ ok: false, status: 503 }));
    const bus = makeBus();
    seedRing(bus, evs(2));

    const drained = await bus.flushAndWait({ timeoutMs: 300 });

    expect(drained).toBe(false);
    expect(bus._ring).toHaveLength(2); // retained for the durable-replay path
  });

  test("returns true immediately when there is nothing to flush", async () => {
    global.fetch = jest.fn();
    const bus = makeBus();
    expect(await bus.flushAndWait({ timeoutMs: 200 })).toBe(true);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("_refreshToken caching", () => {
  test("caches the resolved token for the beacon path", async () => {
    const bus = makeBus({ token: "fresh-token" });
    const t = await bus._refreshToken();
    expect(t).toBe("fresh-token");
    expect(bus._cachedToken).toBe("fresh-token");
  });

  test("falls back to the cached token if the resolver throws", async () => {
    const bus = makeBus();
    bus._cachedToken = "stale-but-usable";
    bus._getAuthToken = jest.fn(async () => { throw new Error("session error"); });
    const t = await bus._refreshToken();
    expect(t).toBe("stale-but-usable");
  });
});
