import { getDocumentDetail, listDocuments } from "../db/queries";
import type { Env } from "../types";
import { errorResponse, jsonResponse, methodNotAllowed, parseDocumentFilters } from "./_utils";

export async function handlePress(request: Request, env: Env, pathname = "/api/press"): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed(env);

  const detailMatch = /^\/api\/press\/([^/]+)$/.exec(pathname);
  if (detailMatch?.[1]) {
    const detail = await getDocumentDetail(env.DB, decodeURIComponent(detailMatch[1]));
    if (!detail || detail.document.source_type !== "press") {
      return errorResponse(env, "Press announcement not found", "NOT_FOUND", 404);
    }
    return jsonResponse(env, detail);
  }

  const url = new URL(request.url);
  const result = await listDocuments(env.DB, parseDocumentFilters(url, "press"));
  return jsonResponse(env, result);
}
