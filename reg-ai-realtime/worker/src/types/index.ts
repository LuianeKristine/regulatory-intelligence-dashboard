export type SourceType =
  | "guidance"
  | "press"
  | "approval"
  | "advisory"
  | "oce_publication"
  | "otp_event"
  | "otp_learn";

export type GuidanceStatus = "draft" | "final" | "unknown";

export type SupportingDocumentType =
  | "package_insert"
  | "approval_letter"
  | "clinical_review"
  | "statistical_review"
  | "sbra"
  | "prescribing_information"
  | "label"
  | "fda_review"
  | "briefing_document"
  | "presentation"
  | "transcript"
  | "agenda"
  | "questions"
  | "other";

export interface Env {
  DB: D1Database;
  FDA_CACHE?: KVNamespace;
  CACHE_TTL_SECONDS?: string;
  CORS_ORIGIN?: string;
  CRON_SECRET?: string;
}

export interface ApiError {
  message: string;
  code: string;
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
}

export interface ApiFailure {
  success: false;
  error: ApiError;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export interface FdaDocumentInput {
  id?: string;
  sourceType: SourceType;
  title: string;
  url: string;
  pdfUrl?: string | null;
  fdaCenter?: string | null;
  status?: GuidanceStatus;
  topic?: string | null;
  publishedDate?: string | null;
  contentHash?: string;
  rawTextSnapshot?: string;
  metadata?: Record<string, unknown>;
  supportingDocuments?: SupportingDocumentInput[];
}

export interface SupportingDocumentInput {
  type: SupportingDocumentType;
  title: string;
  url: string;
  fileUrl?: string | null;
  fileType?: "PDF" | "HTML" | "Download" | "Other";
  sourcePageUrl: string;
  contentHash?: string;
  metadata?: Record<string, unknown>;
}

export interface DocumentRecord {
  id: string;
  source_type: SourceType;
  title: string;
  url: string;
  pdf_url: string | null;
  fda_center: string | null;
  status: GuidanceStatus;
  topic: string | null;
  published_date: string | null;
  last_checked_at: string | null;
  content_hash: string;
  is_new: number;
  is_updated: number;
  metadata_json: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersionRecord {
  id: string;
  document_id: string;
  content_hash: string;
  raw_text_snapshot: string | null;
  detected_at: string;
  change_type: "new" | "updated" | "removed";
}

export interface SupportingDocumentRecord {
  id: string;
  document_id: string;
  type: SupportingDocumentType;
  title: string;
  url: string;
  file_url: string | null;
  file_type: string | null;
  source_page_url: string;
  detected_at: string;
  content_hash: string;
  metadata_json: string;
  created_at: string;
  updated_at: string;
}

export interface ListDocumentsFilters {
  sourceType?: SourceType;
  q?: string;
  fdaCenter?: string;
  status?: GuidanceStatus;
  from?: string;
  to?: string;
  isNew?: boolean;
  isUpdated?: boolean;
  limit?: number;
  offset?: number;
}

export interface SyncSourceSummary {
  sourceType: SourceType;
  itemsFound: number;
  itemsNew: number;
  itemsUpdated: number;
  itemsUnchanged: number;
  errors: string[];
}

export interface SyncRunSummary {
  startedAt: string;
  finishedAt: string;
  status: "success" | "partial_failure" | "failure";
  sourceSummaries: SyncSourceSummary[];
}

export interface AIAnalysisResult {
  executiveSummary: string[];
  keyPoints: string[];
  regulatoryImpact: string;
  impactLevel: "low" | "medium" | "high";
}
