import type { AIAnalysisResult, DocumentRecord } from "../types";

export type AIAnalysisProvider = "openai" | "local" | "custom";

export interface AIAnalysisRequest {
  document: DocumentRecord;
  text: string;
  provider: AIAnalysisProvider;
}

export async function analyzeDocument(_request: AIAnalysisRequest): Promise<AIAnalysisResult> {
  // TODO phase 2: add optional AI providers behind this interface.
  // This MVP intentionally avoids paid AI APIs and external model calls.
  throw new Error("AI analysis is not enabled in this MVP.");
}
