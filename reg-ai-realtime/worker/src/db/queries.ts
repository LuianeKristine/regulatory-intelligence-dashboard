import type {
  DocumentRecord,
  DocumentVersionRecord,
  FdaDocumentInput,
  GuidanceStatus,
  ListDocumentsFilters,
  SourceType,
  SupportingDocumentInput,
  SupportingDocumentRecord
} from "../types";
import { hashRelevantContent, sha256, stableDocumentId, versionId } from "../services/hash";

export interface ListDocumentsResult {
  items: DocumentRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface UpsertResult {
  document: DocumentRecord;
  changeType: "new" | "updated" | "unchanged";
}

function clampLimit(limit?: number): number {
  if (!limit || !Number.isFinite(limit)) return 100;
  return Math.max(1, Math.min(Math.trunc(limit), 500));
}

function clampOffset(offset?: number): number {
  if (!offset || !Number.isFinite(offset)) return 0;
  return Math.max(0, Math.trunc(offset));
}

function parseStatus(status?: string): GuidanceStatus | undefined {
  if (status === "draft" || status === "final" || status === "unknown") return status;
  return undefined;
}

function normalizeMetadata(metadata: Record<string, unknown> | undefined): string {
  return JSON.stringify(metadata ?? {});
}

function bindableBoolean(value: boolean): number {
  return value ? 1 : 0;
}

export async function listDocuments(
  db: D1Database,
  filters: ListDocumentsFilters = {}
): Promise<ListDocumentsResult> {
  const where: string[] = [];
  const binds: Array<string | number> = [];

  if (filters.sourceType) {
    where.push("source_type = ?");
    binds.push(filters.sourceType);
  }

  if (filters.q) {
    where.push("(title LIKE ? OR topic LIKE ? OR fda_center LIKE ? OR metadata_json LIKE ?)");
    const term = `%${filters.q.trim()}%`;
    binds.push(term, term, term, term);
  }

  if (filters.fdaCenter) {
    where.push("fda_center LIKE ?");
    binds.push(`%${filters.fdaCenter.trim()}%`);
  }

  const status = parseStatus(filters.status);
  if (status) {
    where.push("status = ?");
    binds.push(status);
  }

  if (filters.from) {
    where.push("published_date >= ?");
    binds.push(filters.from);
  }

  if (filters.to) {
    where.push("published_date <= ?");
    binds.push(filters.to);
  }

  if (typeof filters.isNew === "boolean") {
    where.push("is_new = ?");
    binds.push(bindableBoolean(filters.isNew));
  }

  if (typeof filters.isUpdated === "boolean") {
    where.push("is_updated = ?");
    binds.push(bindableBoolean(filters.isUpdated));
  }

  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  const limit = clampLimit(filters.limit);
  const offset = clampOffset(filters.offset);

  const totalRow = await db
    .prepare(`SELECT COUNT(*) AS total FROM documents ${whereSql}`)
    .bind(...binds)
    .first<{ total: number }>();

  const query = `
    SELECT *
    FROM documents
    ${whereSql}
    ORDER BY
      datetime(COALESCE(published_date, updated_at, created_at)) DESC,
      datetime(updated_at) DESC
    LIMIT ? OFFSET ?
  `;

  const result = await db
    .prepare(query)
    .bind(...binds, limit, offset)
    .all<DocumentRecord>();

  return {
    items: result.results ?? [],
    total: totalRow?.total ?? 0,
    limit,
    offset
  };
}

export async function getDocumentById(db: D1Database, id: string): Promise<DocumentRecord | null> {
  const row = await db.prepare("SELECT * FROM documents WHERE id = ?").bind(id).first<DocumentRecord>();
  return row ?? null;
}

export async function listDocumentVersions(
  db: D1Database,
  documentId: string
): Promise<DocumentVersionRecord[]> {
  const result = await db
    .prepare(
      `SELECT *
       FROM document_versions
       WHERE document_id = ?
       ORDER BY datetime(detected_at) DESC`
    )
    .bind(documentId)
    .all<DocumentVersionRecord>();

  return result.results ?? [];
}

export async function getDocumentDetail(
  db: D1Database,
  id: string
): Promise<{
  document: DocumentRecord;
  supporting_documents: SupportingDocumentRecord[];
  versions: DocumentVersionRecord[];
  metadata: Record<string, unknown>;
} | null> {
  const document = await getDocumentById(db, id);
  if (!document) return null;
  const [versions, supportingDocuments] = await Promise.all([
    listDocumentVersions(db, id),
    listSupportingDocuments(db, id)
  ]);
  return {
    document,
    supporting_documents: supportingDocuments,
    versions,
    metadata: parseMetadataJson(document.metadata_json)
  };
}

function parseMetadataJson(value: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

export async function clearSourceFlags(db: D1Database, sourceType: SourceType): Promise<void> {
  await db
    .prepare("UPDATE documents SET is_new = 0, is_updated = 0 WHERE source_type = ?")
    .bind(sourceType)
    .run();
}

export async function upsertDocument(db: D1Database, input: FdaDocumentInput): Promise<UpsertResult> {
  const id = input.id ?? (await stableDocumentId(input.sourceType, input.url));
  const now = new Date().toISOString();
  const metadataJson = normalizeMetadata(input.metadata);
  const status = input.status ?? "unknown";
  const rawTextSnapshot = input.rawTextSnapshot ?? JSON.stringify(input);

  const existing = await db
    .prepare("SELECT * FROM documents WHERE id = ? OR url = ? LIMIT 1")
    .bind(id, input.url)
    .first<DocumentRecord>();

  if (!existing) {
    await db
      .prepare(
        `INSERT INTO documents (
          id, source_type, title, url, pdf_url, fda_center, status, topic,
          published_date, last_checked_at, content_hash, is_new, is_updated,
          metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?)`
      )
      .bind(
        id,
        input.sourceType,
        input.title,
        input.url,
        input.pdfUrl ?? null,
        input.fdaCenter ?? null,
        status,
        input.topic ?? null,
        input.publishedDate ?? null,
        now,
        input.contentHash ?? "",
        metadataJson,
        now,
        now
      )
      .run();

    await insertDocumentVersion(db, id, input.contentHash ?? "", rawTextSnapshot, "new");
    const document = await getDocumentById(db, id);
    if (!document) throw new Error(`Inserted document ${id} was not found`);
    return { document, changeType: "new" };
  }

  const targetId = existing.id;
  if (existing.content_hash !== input.contentHash) {
    await db
      .prepare(
        `UPDATE documents
         SET title = ?, url = ?, pdf_url = ?, fda_center = ?, status = ?, topic = ?,
             published_date = ?, last_checked_at = ?, content_hash = ?,
             is_new = 0, is_updated = 1, metadata_json = ?, updated_at = ?
         WHERE id = ?`
      )
      .bind(
        input.title,
        input.url,
        input.pdfUrl ?? null,
        input.fdaCenter ?? null,
        status,
        input.topic ?? null,
        input.publishedDate ?? null,
        now,
        input.contentHash ?? "",
        metadataJson,
        now,
        targetId
      )
      .run();

    await insertDocumentVersion(db, targetId, input.contentHash ?? "", rawTextSnapshot, "updated");
    const document = await getDocumentById(db, targetId);
    if (!document) throw new Error(`Updated document ${targetId} was not found`);
    return { document, changeType: "updated" };
  }

  await db
    .prepare(
      `UPDATE documents
       SET last_checked_at = ?, is_new = 0, is_updated = 0
       WHERE id = ?`
    )
    .bind(now, targetId)
    .run();

  const document = await getDocumentById(db, targetId);
  if (!document) throw new Error(`Unchanged document ${targetId} was not found`);
  return { document, changeType: "unchanged" };
}

export async function listSupportingDocuments(
  db: D1Database,
  documentId: string
): Promise<SupportingDocumentRecord[]> {
  const result = await db
    .prepare(
      `SELECT *
       FROM supporting_documents
       WHERE document_id = ?
       ORDER BY
         CASE type
           WHEN 'package_insert' THEN 1
           WHEN 'prescribing_information' THEN 2
           WHEN 'approval_letter' THEN 3
           WHEN 'clinical_review' THEN 4
           WHEN 'statistical_review' THEN 5
           WHEN 'sbra' THEN 6
           ELSE 20
         END,
         title ASC`
    )
    .bind(documentId)
    .all<SupportingDocumentRecord>();

  return result.results ?? [];
}

export async function upsertSupportingDocument(
  db: D1Database,
  documentId: string,
  input: SupportingDocumentInput
): Promise<SupportingDocumentRecord> {
  const now = new Date().toISOString();
  const contentHash =
    input.contentHash ??
    (await hashRelevantContent({
      documentId,
      type: input.type,
      title: input.title,
      url: input.url,
      fileUrl: input.fileUrl ?? null,
      fileType: input.fileType ?? null
    }));
  const id = `supp_${(await sha256(`${documentId}:${input.url.toLowerCase()}`)).slice(0, 32)}`;

  await db
    .prepare(
      `INSERT INTO supporting_documents (
        id, document_id, type, title, url, file_url, file_type, source_page_url,
        detected_at, content_hash, metadata_json, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(document_id, url) DO UPDATE SET
        type = excluded.type,
        title = excluded.title,
        file_url = excluded.file_url,
        file_type = excluded.file_type,
        source_page_url = excluded.source_page_url,
        detected_at = excluded.detected_at,
        content_hash = excluded.content_hash,
        metadata_json = excluded.metadata_json,
        updated_at = excluded.updated_at`
    )
    .bind(
      id,
      documentId,
      input.type,
      input.title,
      input.url,
      input.fileUrl ?? null,
      input.fileType ?? null,
      input.sourcePageUrl,
      now,
      contentHash,
      normalizeMetadata(input.metadata),
      now,
      now
    )
    .run();

  const row = await db
    .prepare("SELECT * FROM supporting_documents WHERE document_id = ? AND url = ?")
    .bind(documentId, input.url)
    .first<SupportingDocumentRecord>();

  if (!row) throw new Error(`Supporting document ${input.url} was not persisted`);
  return row;
}

export async function upsertSupportingDocuments(
  db: D1Database,
  documentId: string,
  inputs: SupportingDocumentInput[] = []
): Promise<SupportingDocumentRecord[]> {
  const records: SupportingDocumentRecord[] = [];
  for (const input of inputs) {
    records.push(await upsertSupportingDocument(db, documentId, input));
  }
  return records;
}

export async function insertDocumentVersion(
  db: D1Database,
  documentId: string,
  contentHash: string,
  rawTextSnapshot: string | null,
  changeType: "new" | "updated" | "removed"
): Promise<void> {
  await db
    .prepare(
      `INSERT INTO document_versions (
        id, document_id, content_hash, raw_text_snapshot, detected_at, change_type
      ) VALUES (?, ?, ?, ?, ?, ?)`
    )
    .bind(await versionId(documentId, contentHash), documentId, contentHash, rawTextSnapshot, new Date().toISOString(), changeType)
    .run();
}

export async function createSyncRun(
  db: D1Database,
  sourceType: SourceType | "all"
): Promise<string> {
  const id = `sync_${crypto.randomUUID()}`;
  await db
    .prepare(
      `INSERT INTO sync_runs (
        id, started_at, status, source_type, items_found, items_new, items_updated
      ) VALUES (?, ?, 'running', ?, 0, 0, 0)`
    )
    .bind(id, new Date().toISOString(), sourceType === "all" ? null : sourceType)
    .run();
  return id;
}

export async function finishSyncRun(
  db: D1Database,
  id: string,
  args: {
    status: "success" | "partial_failure" | "failure";
    itemsFound: number;
    itemsNew: number;
    itemsUpdated: number;
    errorMessage?: string | null;
  }
): Promise<void> {
  await db
    .prepare(
      `UPDATE sync_runs
       SET finished_at = ?, status = ?, items_found = ?, items_new = ?,
           items_updated = ?, error_message = ?
       WHERE id = ?`
    )
    .bind(
      new Date().toISOString(),
      args.status,
      args.itemsFound,
      args.itemsNew,
      args.itemsUpdated,
      args.errorMessage ?? null,
      id
    )
    .run();
}

export async function touchSourceSyncedAt(db: D1Database, sourceType: SourceType): Promise<void> {
  await db
    .prepare("UPDATE sources SET last_synced_at = ? WHERE source_type = ?")
    .bind(new Date().toISOString(), sourceType)
    .run();
}

export async function getStats(db: D1Database): Promise<Record<string, unknown>> {
  const totals = await db
    .prepare(
      `SELECT
        COUNT(*) AS totalDocuments,
        COALESCE(SUM(is_new), 0) AS newDocuments,
        COALESCE(SUM(is_updated), 0) AS updatedDocuments
       FROM documents`
    )
    .first<{ totalDocuments: number; newDocuments: number; updatedDocuments: number }>();

  const bySource = await db
    .prepare(
      `SELECT source_type AS sourceType, COUNT(*) AS total
       FROM documents
       GROUP BY source_type
       ORDER BY total DESC`
    )
    .all<{ sourceType: string; total: number }>();

  const latestSync = await db
    .prepare(
      `SELECT *
       FROM sync_runs
       ORDER BY datetime(started_at) DESC
       LIMIT 1`
    )
    .first<Record<string, unknown>>();

  const highPriority = await db
    .prepare(
      `SELECT COUNT(*) AS total
       FROM sources
       WHERE enabled = 1 AND source_type IN ('guidance', 'approval')`
    )
    .first<{ total: number }>();

  const sources = await db
    .prepare(
      `SELECT id, name, url, source_type AS sourceType, enabled, last_synced_at AS lastSyncedAt
       FROM sources
       ORDER BY enabled DESC, name ASC`
    )
    .all<Record<string, unknown>>();

  const supportingDocuments = await db
    .prepare("SELECT COUNT(*) AS total FROM supporting_documents")
    .first<{ total: number }>();

  return {
    totalDocuments: totals?.totalDocuments ?? 0,
    newDocuments: totals?.newDocuments ?? 0,
    updatedDocuments: totals?.updatedDocuments ?? 0,
    supportingDocumentsFound: supportingDocuments?.total ?? 0,
    highPrioritySources: highPriority?.total ?? 0,
    lastSync: latestSync ?? null,
    bySource: bySource.results ?? [],
    sources: sources.results ?? []
  };
}

export async function seedSources(db: D1Database): Promise<void> {
  const statements = [
    [
      "src_guidance",
      "FDA Guidance Documents",
      "https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
      "guidance",
      1
    ],
    [
      "src_press",
      "FDA Press Announcements",
      "https://www.fda.gov/news-events/fda-newsroom/press-announcements",
      "press",
      1
    ],
    [
      "src_approvals",
      "Approved Cellular and Gene Therapy Products",
      "https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products",
      "approval",
      1
    ],
    ["src_advisory", "Advisory Committees", "TODO_PHASE_2", "advisory", 0],
    ["src_oce_publications", "OCE Publications", "TODO_PHASE_2", "oce_publication", 0],
    ["src_otp_events", "OTP Events", "TODO_PHASE_2", "otp_event", 0],
    ["src_otp_learn", "OTP Learn", "TODO_PHASE_2", "otp_learn", 0]
  ] as const;

  await db.batch(
    statements.map((row) =>
      db
        .prepare(
          `INSERT OR IGNORE INTO sources (id, name, url, source_type, enabled)
           VALUES (?, ?, ?, ?, ?)`
        )
        .bind(...row)
    )
  );
}
