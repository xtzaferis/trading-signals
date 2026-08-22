import assert from "node:assert/strict";

import { dispatchWorkflow, isTradingSession } from "./src/index.mjs";

assert.equal(isTradingSession(Date.parse("2026-08-21T13:59:00Z")), false);
assert.equal(isTradingSession(Date.parse("2026-08-21T14:00:00Z")), true);
assert.equal(isTradingSession(Date.parse("2026-08-21T15:59:00Z")), true);
assert.equal(isTradingSession(Date.parse("2026-08-21T16:00:00Z")), false);

let request;
const status = await dispatchWorkflow("test-token", async (url, options) => {
  request = { url, options };
  return new Response(null, { status: 204 });
});

assert.equal(status, 204);
assert.match(request.url, /advisory-pages\.yml\/dispatches$/);
assert.equal(request.options.method, "POST");
assert.equal(request.options.headers.Authorization, "Bearer test-token");
assert.equal(
  request.options.headers["User-Agent"],
  "trading-signals-scheduler/1.0",
);
assert.deepEqual(JSON.parse(request.options.body), { ref: "main" });

console.log("Cloudflare scheduler tests passed");
