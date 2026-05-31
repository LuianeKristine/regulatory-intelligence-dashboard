import { getDocumentDetail, listDocuments } from "../db/queries";
import type { Env } from "../types";
import { errorResponse, jsonResponse, methodNotAllowed, parseDocumentFilters } from "./_utils";

export async function handleApprovals(request: Request, env: Env, pathname = "/api/approvals"): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed(env);

  const detailMatch = /^\/api\/approvals\/([^/]+)$/.exec(pathname);
  if (detailMatch?.[1]) {
    const detail = await getDocumentDetail(env.DB, decodeURIComponent(detailMatch[1]));
    if (!detail || detail.document.source_type !== "approval") {
      return errorResponse(env, "Approval not found", "NOT_FOUND", 404);
    }
    return jsonResponse(env, detail);
  }

  const url = new URL(request.url);
  const result = await listDocuments(env.DB, parseDocumentFilters(url, "approval"));
  return jsonResponse(env, result);
}
