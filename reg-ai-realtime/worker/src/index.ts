import { seedSources } from "./db/queries";
import { handleApprovals } from "./routes/approvals";
import { handleDocumentDetail } from "./routes/documents";
import { handleGuidances } from "./routes/guidances";
import { handlePress } from "./routes/press";
import { handlePhaseTwoPlaceholder } from "./routes/advisory";
import { handleStats } from "./routes/stats";
import { handleSync } from "./routes/sync";
import { corsHeaders, errorResponse, jsonResponse, logRouteError } from "./routes/_utils";
import { runSync } from "./services/syncService";
import type { Env } from "./types";

async function handleHealth(request: Request, env: Env): Promise<Response> {
  if (request.method !== "GET") {
    return errorResponse(env, "Method not allowed", "METHOD_NOT_ALLOWED", 405);
  }

  const db = await env.DB.prepare("SELECT 1 AS ok").first<{ ok: number }>();
  return jsonResponse(env, {
    service: "regai-realtime-worker",
    status: "ok",
    db: db?.ok === 1 ? "ok" : "unknown",
    ai: "not_enabled",
    timestamp: new Date().toISOString()
  });
}

async function route(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const pathname = url.pathname.replace(/\/+$/, "") || "/";

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(env) });
  }

  try {
    if (pathname === "/api/health") return handleHealth(request, env);
    if (pathname === "/api/stats") return handleStats(request, env);
    if (pathname === "/api/sync") return handleSync(request, env);
    if (pathname === "/api/cron/sync") return handleSync(request, env, true);
    if (pathname.startsWith("/api/press")) return handlePress(request, env, pathname);
    if (pathname.startsWith("/api/approvals")) return handleApprovals(request, env, pathname);
    if (pathname === "/api/advisory" || pathname === "/api/advisory-committees") {
      return handlePhaseTwoPlaceholder(request, env, "Advisory Committees");
    }
    if (pathname === "/api/oce-publications") {
      return handlePhaseTwoPlaceholder(request, env, "OCE Publications");
    }
    if (pathname.startsWith("/api/guidances")) return handleGuidances(request, env, pathname);
    if (pathname.startsWith("/api/documents/")) return handleDocumentDetail(request, env, pathname);

    return errorResponse(env, "Route not found", "NOT_FOUND", 404);
  } catch (error) {
    logRouteError(pathname, error);
    return errorResponse(
      env,
      error instanceof Error ? error.message : "Unexpected error",
      "INTERNAL_ERROR",
      500
    );
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    await seedSources(env.DB).catch(() => undefined);
    return route(request, env);
  },

  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(
      runSync(env).catch((error) => {
        console.error(
          JSON.stringify({
            level: "error",
            event: "scheduled_sync_failed",
            message: error instanceof Error ? error.message : String(error),
            ts: new Date().toISOString()
          })
        );
      })
    );
  }
};
