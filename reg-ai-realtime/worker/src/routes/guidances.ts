import { getDocumentDetail, listDocuments } from "../db/queries";
import type { Env } from "../types";
import { errorResponse, jsonResponse, methodNotAllowed, parseDocumentFilters } from "./_utils";

export async function handleGuidances(request: Request, env: Env, pathname: string): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed(env);

  const detailMatch = /^\/api\/guidances\/([^/]+)$/.exec(pathname);
  if (detailMatch?.[1]) {
    const detail = await getDocumentDetail(env.DB, decodeURIComponent(detailMatch[1]));
    if (!detail || detail.document.source_type !== "guidance") {
      return errorResponse(env, "Guidance not found", "NOT_FOUND", 404);
    }
    return jsonResponse(env, detail);
  }

  const url = new URL(request.url);
  const result = await listDocuments(env.DB, parseDocumentFilters(url, "guidance"));
  return jsonResponse(env, result);
}
