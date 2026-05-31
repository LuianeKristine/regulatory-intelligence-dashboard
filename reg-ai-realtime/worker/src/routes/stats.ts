import { getStats } from "../db/queries";
import type { Env } from "../types";
import { jsonResponse, methodNotAllowed } from "./_utils";

export async function handleStats(request: Request, env: Env): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed(env);
  return jsonResponse(env, await getStats(env.DB));
}
