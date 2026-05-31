import { getDocumentDetail, listSupportingDocuments } from "../db/queries";
import type { Env } from "../types";
import { errorResponse, jsonResponse, methodNotAllowed } from "./_utils";

export async function handleDocumentDetail(request: Request, env: Env, pathname: string): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed(env);

  const supportingMatch = /^\/api\/documents\/([^/]+)\/supporting-documents$/.exec(pathname);
  if (supportingMatch?.[1]) {
    return jsonResponse(env, await listSupportingDocuments(env.DB, decodeURIComponent(supportingMatch[1])));
  }

  const detailMatch = /^\/api\/documents\/([^/]+)$/.exec(pathname);
  if (!detailMatch?.[1]) return errorResponse(env, "Document not found", "NOT_FOUND", 404);

  const detail = await getDocumentDetail(env.DB, decodeURIComponent(detailMatch[1]));
  if (!detail) return errorResponse(env, "Document not found", "NOT_FOUND", 404);
  return jsonResponse(env, detail);
}
