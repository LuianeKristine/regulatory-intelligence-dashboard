import type { Env } from "../types";
import { jsonResponse, methodNotAllowed } from "./_utils";

export async function handlePhaseTwoPlaceholder(request: Request, env: Env, sourceName: string): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed(env);

  return jsonResponse(env, {
    enabled: false,
    sourceName,
    message: "Prepared for phase 2. Parser and sync are intentionally not enabled in this MVP.",
    todo: [
      "Add FDA source URL",
      "Implement parser in services/parser.ts",
      "Enable source in D1 table",
      "Add source type to syncService"
    ]
  });
}
