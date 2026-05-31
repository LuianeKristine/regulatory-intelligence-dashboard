import type { Env } from "../types";
import { parseRequestedSources, runSync } from "../services/syncService";
import { errorResponse, jsonResponse, methodNotAllowed, readJsonBody } from "./_utils";

export async function handleSync(request: Request, env: Env, cronEndpoint = false): Promise<Response> {
  if (request.method !== "POST") return methodNotAllowed(env);

  if (cronEndpoint && env.CRON_SECRET) {
    const provided = request.headers.get("X-Cron-Secret");
    if (provided !== env.CRON_SECRET) {
      return errorResponse(env, "Invalid cron secret", "UNAUTHORIZED", 401);
    }
  }

  const url = new URL(request.url);
  const body = await readJsonBody(request);
  const requested =
    body.sourceTypes ??
    body.sources ??
    body.source_type ??
    url.searchParams.get("source_type") ??
    url.searchParams.get("sources");

  const summary = await runSync(env, parseRequestedSources(requested));
  return jsonResponse(env, summary);
}
