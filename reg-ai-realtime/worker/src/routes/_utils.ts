import type { Env, GuidanceStatus, ListDocumentsFilters, SourceType } from "../types";

export function corsHeaders(env: Env): HeadersInit {
  return {
    "Access-Control-Allow-Origin": env.CORS_ORIGIN ?? "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Cron-Secret",
    "Access-Control-Max-Age": "86400"
  };
}

export function jsonResponse<T>(env: Env, data: T, status = 200): Response {
  return new Response(JSON.stringify({ success: true, data }), {
    status,
    headers: {
      ...corsHeaders(env),
      "Content-Type": "application/json; charset=utf-8"
    }
  });
}

export function errorResponse(
  env: Env,
  message: string,
  code = "INTERNAL_ERROR",
  status = 500
): Response {
  return new Response(
    JSON.stringify({
      success: false,
      error: { message, code }
    }),
    {
      status,
      headers: {
        ...corsHeaders(env),
        "Content-Type": "application/json; charset=utf-8"
      }
    }
  );
}

export function methodNotAllowed(env: Env): Response {
  return errorResponse(env, "Method not allowed", "METHOD_NOT_ALLOWED", 405);
}

export async function readJsonBody(request: Request): Promise<Record<string, unknown>> {
  if (!request.headers.get("content-type")?.includes("application/json")) return {};
  const text = await request.text();
  if (!text.trim()) return {};
  return JSON.parse(text) as Record<string, unknown>;
}

export function parseBooleanParam(value: string | null): boolean | undefined {
  if (value === null || value === "") return undefined;
  if (["1", "true", "yes"].includes(value.toLowerCase())) return true;
  if (["0", "false", "no"].includes(value.toLowerCase())) return false;
  return undefined;
}

export function parseDocumentFilters(url: URL, sourceType?: SourceType): ListDocumentsFilters {
  const status = url.searchParams.get("status") as GuidanceStatus | null;
  return {
    sourceType: sourceType ?? ((url.searchParams.get("source_type") as SourceType | null) ?? undefined),
    q: url.searchParams.get("q") ?? url.searchParams.get("search") ?? undefined,
    fdaCenter: url.searchParams.get("fda_center") ?? undefined,
    status: status ?? undefined,
    from: url.searchParams.get("from") ?? undefined,
    to: url.searchParams.get("to") ?? undefined,
    isNew: parseBooleanParam(url.searchParams.get("is_new")),
    isUpdated: parseBooleanParam(url.searchParams.get("is_updated")),
    limit: Number(url.searchParams.get("limit") ?? "100"),
    offset: Number(url.searchParams.get("offset") ?? "0")
  };
}

export function logRouteError(pathname: string, error: unknown): void {
  console.error(
    JSON.stringify({
      level: "error",
      event: "route_failed",
      pathname,
      message: error instanceof Error ? error.message : String(error),
      ts: new Date().toISOString()
    })
  );
}
