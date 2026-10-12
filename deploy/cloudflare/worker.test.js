import assert from "node:assert/strict";
import test from "node:test";

import worker from "./worker.js";

const allowedOrigin = "https://huyenbao.com";

function env(overrides = {}) {
  const allow = { limit: async () => ({ success: true }) };
  return {
    BACKEND_ORIGIN: "https://api.huyenbao.com",
    CORS_ALLOWED_ORIGINS: allowedOrigin,
    API_LIMITER: allow,
    AUTH_LIMITER: allow,
    COMPUTE_LIMITER: allow,
    ...overrides,
  };
}

test("proxy forwards API requests without trusting client forwarded headers or caching", async () => {
  const originalFetch = globalThis.fetch;
  let forwarded;
  globalThis.fetch = async (request) => {
    forwarded = request;
    return new Response("ok", { headers: { "Cache-Control": "public, max-age=600" } });
  };
  try {
    const request = new Request("https://huyenbao.com/api/example?x=1", {
      headers: {
        Origin: allowedOrigin,
        "CF-Connecting-IP": "203.0.113.4",
        "X-Forwarded-For": "198.51.100.9",
        Authorization: "Bearer test",
      },
    });
    const response = await worker.fetch(request, env());
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "private, no-store");
    assert.equal(response.headers.get("access-control-allow-origin"), allowedOrigin);
    assert.equal(forwarded.url, "https://api.huyenbao.com/api/example?x=1");
    assert.equal(forwarded.headers.get("x-forwarded-for"), "203.0.113.4");
    assert.equal(forwarded.headers.get("authorization"), "Bearer test");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("authentication rate limits are enforced before contacting the origin", async () => {
  let originCalled = false;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    originCalled = true;
    return new Response("unexpected");
  };
  try {
    const response = await worker.fetch(
      new Request("https://huyenbao.com/api/auth/login", {
        method: "POST",
        headers: {
          Origin: allowedOrigin,
          "CF-Connecting-IP": "203.0.113.4",
        },
        body: "{}",
      }),
      env({ AUTH_LIMITER: { limit: async () => ({ success: false }) } }),
    );
    assert.equal(response.status, 429);
    assert.equal(response.headers.get("retry-after"), "60");
    assert.equal(response.headers.get("access-control-allow-origin"), allowedOrigin);
    assert.equal(originCalled, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("preflight rejects unconfigured origins and permits configured origins", async () => {
  const denied = await worker.fetch(new Request("https://huyenbao.com/api/x", {
    method: "OPTIONS",
    headers: {
      Origin: "https://attacker.example",
      "Access-Control-Request-Method": "POST",
    },
  }), env());
  assert.equal(denied.status, 403);
  assert.equal(denied.headers.get("access-control-allow-origin"), null);

  const allowed = await worker.fetch(new Request("https://huyenbao.com/api/x", {
    method: "OPTIONS",
    headers: {
      Origin: allowedOrigin,
      "Access-Control-Request-Method": "POST",
    },
  }), env());
  assert.equal(allowed.status, 204);
  assert.equal(allowed.headers.get("access-control-allow-origin"), allowedOrigin);
});

test("rate limiting fails closed when the binding is unavailable", async () => {
  const response = await worker.fetch(
    new Request("https://huyenbao.com/api/example", {
      headers: { "CF-Connecting-IP": "203.0.113.4" },
    }),
    env({ API_LIMITER: { limit: async () => { throw new Error("unavailable"); } } }),
  );
  assert.equal(response.status, 503);
});
