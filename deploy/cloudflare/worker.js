const ALLOWED_METHODS = "GET, HEAD, POST, PUT, DELETE, OPTIONS";
const ALLOWED_HEADERS = "Authorization, Content-Type";

class RateLimitUnavailableError extends Error {}

function jsonResponse(data, status, headers = {}) {
  const responseHeaders = new Headers(headers);
  responseHeaders.set("Content-Type", "application/json; charset=utf-8");
  return new Response(JSON.stringify(data), {
    status,
    headers: responseHeaders,
  });
}

function allowedOrigins(env) {
  return new Set(
    (env.CORS_ALLOWED_ORIGINS || "")
      .split(",")
      .map((origin) => origin.trim())
      .filter(Boolean),
  );
}

function addCorsHeaders(headers, request, env) {
  const origin = request.headers.get("Origin");
  const existingVary = headers.get("Vary");
  headers.set("Vary", existingVary ? `${existingVary}, Origin` : "Origin");
  if (origin && allowedOrigins(env).has(origin)) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Access-Control-Allow-Methods", ALLOWED_METHODS);
    headers.set("Access-Control-Allow-Headers", ALLOWED_HEADERS);
    headers.set("Access-Control-Max-Age", "600");
  }
  return headers;
}

async function enforceRateLimit(binding, key) {
  try {
    const result = await binding.limit({ key });
    return result.success;
  } catch (error) {
    console.error(JSON.stringify({
      message: "rate limiter unavailable",
      error: error instanceof Error ? error.message : "unknown error",
    }));
    throw new RateLimitUnavailableError();
  }
}

function limiterForPath(pathname, env) {
  if (pathname.startsWith("/api/auth/")) {
    return { binding: env.AUTH_LIMITER, scope: "auth" };
  }
  if (/^\/api\/(analyze|tarot|kinh-dich|tu-vi|voice|video|social)(\/|$)/.test(pathname)) {
    return { binding: env.COMPUTE_LIMITER, scope: "compute" };
  }
  return { binding: env.API_LIMITER, scope: "api" };
}

function upstreamRequest(request, backendOrigin, clientIp) {
  const incomingUrl = new URL(request.url);
  const target = new URL(incomingUrl.pathname + incomingUrl.search, backendOrigin);
  const headers = new Headers(request.headers);
  for (const name of [
    "Forwarded",
    "X-Forwarded-For",
    "X-Forwarded-Host",
    "X-Forwarded-Proto",
    "X-Real-IP",
    "X-Huyenbao-Edge",
  ]) {
    headers.delete(name);
  }
  headers.set("X-Forwarded-For", clientIp);
  headers.set("X-Real-IP", clientIp);
  headers.set("X-Forwarded-Host", incomingUrl.host);
  headers.set("X-Forwarded-Proto", incomingUrl.protocol.slice(0, -1));
  headers.set("X-Huyenbao-Edge", "1");

  const init = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }
  return new Request(target, init);
}

async function proxyRequest(request, env, clientIp) {
  let backend;
  try {
    backend = new URL(env.BACKEND_ORIGIN);
  } catch {
    return jsonResponse({ error: "Backend origin is not configured." }, 503);
  }
  if (backend.protocol !== "https:" || backend.username || backend.password) {
    return jsonResponse({ error: "Backend origin configuration is invalid." }, 503);
  }

  let response;
  try {
    response = await fetch(upstreamRequest(request, backend.origin, clientIp));
  } catch {
    return jsonResponse({ error: "Backend is temporarily unavailable." }, 502);
  }

  const headers = new Headers(response.headers);
  for (const name of [
    "Access-Control-Allow-Origin",
    "Access-Control-Allow-Methods",
    "Access-Control-Allow-Headers",
    "Access-Control-Allow-Credentials",
  ]) {
    headers.delete(name);
  }
  headers.set("Cache-Control", "private, no-store");
  addCorsHeaders(headers, request, env);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const origins = allowedOrigins(env);
    const corsHeaders = new Headers();
    addCorsHeaders(corsHeaders, request, env);

    if (request.method === "OPTIONS") {
      if (!origin || !origins.has(origin)) {
        return jsonResponse({ error: "Origin is not allowed." }, 403, corsHeaders);
      }
      const requestedMethod = request.headers.get("Access-Control-Request-Method");
      if (!requestedMethod || !ALLOWED_METHODS.split(", ").includes(requestedMethod)) {
        return jsonResponse({ error: "Method is not allowed." }, 403, corsHeaders);
      }
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    if (url.protocol !== "https:") {
      return jsonResponse({ error: "HTTPS is required." }, 400, corsHeaders);
    }

    if (url.pathname.startsWith("/api/")) {
      const clientIp = request.headers.get("CF-Connecting-IP");
      if (!clientIp) {
        return jsonResponse({ error: "Client address is unavailable." }, 400, corsHeaders);
      }
      try {
        if (!await enforceRateLimit(env.API_LIMITER, clientIp)) {
          const headers = new Headers(corsHeaders);
          headers.set("Retry-After", "60");
          return jsonResponse(
            { error: "Too many requests. Please try again later." },
            429,
            headers,
          );
        }
        const selected = limiterForPath(url.pathname, env);
        if (selected.binding !== env.API_LIMITER &&
            !await enforceRateLimit(selected.binding, clientIp)) {
          const headers = new Headers(corsHeaders);
          headers.set("Retry-After", "60");
          return jsonResponse(
            { error: "Too many requests. Please try again later.", scope: selected.scope },
            429,
            headers,
          );
        }
      } catch (error) {
        if (error instanceof RateLimitUnavailableError) {
          return jsonResponse(
            { error: "Request protection is temporarily unavailable." },
            503,
            corsHeaders,
          );
        }
        throw error;
      }
      return proxyRequest(request, env, clientIp);
    }

    const headers = new Headers(corsHeaders);
    headers.set("Cache-Control", "private, no-store");
    return proxyRequest(request, { ...env, CORS_ALLOWED_ORIGINS: env.CORS_ALLOWED_ORIGINS }, request.headers.get("CF-Connecting-IP") || "");
  },
};
