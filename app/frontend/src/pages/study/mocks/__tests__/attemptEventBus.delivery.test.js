/**
 * attemptEventBus — delivery / retry / auth regression tests (PR #796 review P0).
 *
 * Regressions covered:
 *   1. `_flush()` previously spliced the batch BEFORE the request and never
 *      checked `response.ok`, so any 401/409/5xx or network error silently
 *      discarded events. Now the batch is retained until the server ACKs.
 *   2. `_flushBeacon()` previously used `navigator.sendBeacon`, which cannot
 *      attach the `Authorization` header the events endpoint requires
 *      (`get_current_user` → 401), so unmount/visibility-hidden batches
 *      (including `question.visited` anchors) were rejected and lost. Now it
 *      uses an authenticated `fetch({keepalive:true})`.
 */
import { AttemptEventBus } from "../attemptEventBus";

function makeBus({ token = "tok123" } = {}) {
  const bus = new AttemptEventBus();
  bus._attemptId = "att1";
  bus._apiBase = "/api/study/mocks/attempts";
  bus._getAuthToken = jest.fn(async () => token);
  return bus;
}

beforeEach(() => {
  jest.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
  delete global.fetch;
});

describe("_flush ack/retry semantics", () => {
  test("retains events when the server rejects the batch (401)", async () => {
    global.fetch = jest.fn(async () => ({ ok: false, status: 401 }));
    const bus = makeBus();
    bus._ring = [{ sequence_no: 1, event_type: "question.visited" }, { sequence_no: 2 }];

    await bus._flush();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(bus._ring).toHaveLength(2); // NOT dropped
  });

  test("clears events on a successful (ok) response and sends Bearer auth", async () => {
    global.fetch = jest.fn(async () => ({ ok: true, status: 200 }));
    const bus = makeBus();
    bus._ring = [{ sequence_no: 1 }, { sequence_no: 2 }];

    await bus._flush();

    expect(bus._ring).toHaveLength(0);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/study/mocks/attempts/att1/events");
    expect(opts.keepalive).toBe(true);
    expect(opts.headers.Authorization).toBe("Bearer tok123");
  });

  test("retains events on a network error", async () => {
    global.fetch = jest.fn(async () => {
      throw new Error("network down");
    });
    const bus = makeBus();
    bus._ring = [{ sequence_no: 1 }];

    await bus._flush();

    expect(bus._ring).toHaveLength(1);
  });

  test("a failed batch is resent on the next flush, then cleared", async () => {
    let call = 0;
    global.fetch = jest.fn(async () => (++call === 1 ? { ok: false, status: 503 } : { ok: true, status: 200 }));
    const bus = makeBus();
    bus._ring = [{ sequence_no: 1 }, { sequence_no: 2 }];

    await bus._flush(); // 503 → retained
    expect(bus._ring).toHaveLength(2);

    await bus._flush(); // 200 → cleared
    expect(bus._ring).toHaveLength(0);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  test("only acknowledged events are removed; events enqueued during the await survive", async () => {
    let resolveFetch;
    global.fetch = jest.fn(
      () => new Promise((res) => { resolveFetch = () => res({ ok: true, status: 200 }); }),
    );
    const bus = makeBus();
    bus._ring = [{ sequence_no: 1 }];

    const p = bus._flush();           // snapshots seq=1, awaits token then fetch
    // Let _refreshToken() resolve so fetch is actually invoked.
    for (let i = 0; i < 20 && !resolveFetch; i++) await Promise.resolve();
    bus._ring.push({ sequence_no: 2 }); // arrives mid-flight
    resolveFetch();
    await p;

    expect(bus._ring.map((e) => e.sequence_no)).toEqual([2]); // seq=1 acked & removed, seq=2 retained
  });

  test("does not send overlapping batches while a flush is in flight", async () => {
    global.fetch = jest.fn();
    const bus = makeBus();
    bus._inFlight = true;
    bus._ring = [{ sequence_no: 1 }];

    await bus._flush();

    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("_flushBeacon auth", () => {
  test("uses an authenticated keepalive fetch (not sendBeacon) when a token is cached", () => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200 }));
    navigator.sendBeacon = jest.fn();
    const bus = makeBus();
    bus._cachedToken = "tok123";
    bus._ring = [{ sequence_no: 1, event_type: "question.visited" }];

    bus._flushBeacon();

    expect(navigator.sendBeacon).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/study/mocks/attempts/att1/events");
    expect(opts.keepalive).toBe(true);
    expect(opts.headers.Authorization).toBe("Bearer tok123");
    expect(bus._ring).toHaveLength(0);
  });

  test("defers (no request, retains events) when no auth token is cached yet", () => {
    global.fetch = jest.fn();
    const bus = makeBus();
    bus._cachedToken = null;
    bus._ring = [{ sequence_no: 1 }];

    bus._flushBeacon();

    expect(global.fetch).not.toHaveBeenCalled();
    expect(bus._ring).toHaveLength(1); // retained for a later authenticated flush
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
