import type { Env, SourceType, SyncRunSummary, SyncSourceSummary } from "../types";
import {
  clearSourceFlags,
  createSyncRun,
  finishSyncRun,
  seedSources,
  touchSourceSyncedAt,
  upsertDocument,
  upsertSupportingDocuments
} from "../db/queries";
import { fetchDocumentsForSource } from "./fdaClient";

const DEFAULT_SYNC_SOURCES: SourceType[] = ["guidance", "press", "approval"];

function log(level: "info" | "error", event: string, data: Record<string, unknown>): void {
  console[level](JSON.stringify({ level, event, ts: new Date().toISOString(), ...data }));
}

export function parseRequestedSources(value: unknown): SourceType[] {
  if (!value) return DEFAULT_SYNC_SOURCES;

  const raw = Array.isArray(value) ? value : String(value).split(",");
  const requested = raw
    .map((item) => String(item).trim() as SourceType)
    .filter((item) => DEFAULT_SYNC_SOURCES.includes(item));

  return requested.length > 0 ? [...new Set(requested)] : DEFAULT_SYNC_SOURCES;
}

export async function runSync(env: Env, sourceTypes = DEFAULT_SYNC_SOURCES): Promise<SyncRunSummary> {
  await seedSources(env.DB);

  const startedAt = new Date().toISOString();
  const runId = await createSyncRun(env.DB, sourceTypes.length === 1 && sourceTypes[0] ? sourceTypes[0] : "all");
  const sourceSummaries: SyncSourceSummary[] = [];

  log("info", "sync_started", { runId, sourceTypes });

  for (const sourceType of sourceTypes) {
    const summary: SyncSourceSummary = {
      sourceType,
      itemsFound: 0,
      itemsNew: 0,
      itemsUpdated: 0,
      itemsUnchanged: 0,
      errors: []
    };

    try {
      const documents = await fetchDocumentsForSource(env, sourceType);
      summary.itemsFound = documents.length;
      await clearSourceFlags(env.DB, sourceType);

      for (const document of documents) {
        const result = await upsertDocument(env.DB, document);
        await upsertSupportingDocuments(env.DB, result.document.id, document.supportingDocuments ?? []);
        if (result.changeType === "new") summary.itemsNew += 1;
        if (result.changeType === "updated") summary.itemsUpdated += 1;
        if (result.changeType === "unchanged") summary.itemsUnchanged += 1;
      }

      await touchSourceSyncedAt(env.DB, sourceType);
      log("info", "sync_source_completed", { runId, ...summary });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      summary.errors.push(message);
      log("error", "sync_source_failed", { runId, sourceType, message });
    }

    sourceSummaries.push(summary);
  }

  const itemsFound = sourceSummaries.reduce((sum, item) => sum + item.itemsFound, 0);
  const itemsNew = sourceSummaries.reduce((sum, item) => sum + item.itemsNew, 0);
  const itemsUpdated = sourceSummaries.reduce((sum, item) => sum + item.itemsUpdated, 0);
  const errorMessages = sourceSummaries.flatMap((item) => item.errors);
  const status: SyncRunSummary["status"] =
    errorMessages.length === 0
      ? "success"
      : errorMessages.length === sourceSummaries.length
        ? "failure"
        : "partial_failure";

  await finishSyncRun(env.DB, runId, {
    status,
    itemsFound,
    itemsNew,
    itemsUpdated,
    errorMessage: errorMessages.length ? errorMessages.join(" | ") : null
  });

  const finishedAt = new Date().toISOString();
  log("info", "sync_finished", { runId, status, itemsFound, itemsNew, itemsUpdated });

  return {
    startedAt,
    finishedAt,
    status,
    sourceSummaries
  };
}
