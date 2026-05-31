import type { Env, FdaDocumentInput, SourceType } from "../types";
import { cacheKeyForUrl, getCachedText, getCacheTtlSeconds, putCachedText } from "./cache";
import { hashRelevantContent } from "./hash";
import { discoverSupportingDocuments } from "./documentDiscovery";
import {
  FDA_BASE_URL,
  extractFdaProductMetadata,
  extractMetaContent,
  parseApprovals,
  parseGuidanceDatatablesPayload,
  parseGuidanceLinksFallback,
  parsePressAnnouncements,
  stripTags
} from "./parser";

export const FDA_SOURCES: Record<"guidance" | "press" | "approval", { name: string; url: string }> = {
  guidance: {
    name: "FDA Guidance Documents",
    url: `${FDA_BASE_URL}/regulatory-information/search-fda-guidance-documents`
  },
  press: {
    name: "FDA Press Announcements",
    url: `${FDA_BASE_URL}/news-events/fda-newsroom/press-announcements`
  },
  approval: {
    name: "Approved Cellular and Gene Therapy Products",
    url: `${FDA_BASE_URL}/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products`
  }
};

const GUIDANCE_JSON_ENDPOINT = `${FDA_BASE_URL}/datatables-json/search-for-guidance.json?draw=1&start=0&length=1000`;

const GUIDANCE_FALLBACK_PAGES: Array<{ center: "CDER" | "CBER" | "OCE"; url: string }> = [
  { center: "CDER", url: `${FDA_BASE_URL}/drugs/guidances-drugs` },
  {
    center: "CBER",
    url: `${FDA_BASE_URL}/vaccines-blood-biologics/guidance-compliance-regulatory-information-biologics/biologics-guidances`
  },
  {
    center: "OCE",
    url: `${FDA_BASE_URL}/about-fda/oncology-center-excellence/oncology-center-excellence-guidance-documents`
  }
];

export async function fetchDocumentsForSource(
  env: Env,
  sourceType: SourceType
): Promise<FdaDocumentInput[]> {
  switch (sourceType) {
    case "guidance":
      return withContentHashes(await enrichDocumentsWithDetailPages(env, await fetchGuidances(env)));
    case "press":
      return withContentHashes(await enrichDocumentsWithDetailPages(env, await fetchPressAnnouncements(env)));
    case "approval":
      return withContentHashes(await enrichDocumentsWithDetailPages(env, await fetchApprovals(env)));
    default:
      return [];
  }
}

export async function fetchGuidances(env: Env): Promise<FdaDocumentInput[]> {
  const jsonAttempts = [GUIDANCE_JSON_ENDPOINT];
  const errors: string[] = [];

  for (const endpoint of jsonAttempts) {
    try {
      const jsonText = await fetchTextWithCache(env, endpoint);
      const payload = JSON.parse(jsonText) as unknown;
      const documents = parseGuidanceDatatablesPayload(payload);
      if (documents.length > 0) {
        return documents;
      }
    } catch (error) {
      errors.push(error instanceof Error ? error.message : String(error));
    }
  }

  try {
    const html = await fetchTextWithCache(env, FDA_SOURCES.guidance.url);
    const documents = parseGuidanceLinksFallback(html);
    if (documents.length > 0) {
      return documents;
    }
  } catch (error) {
    errors.push(error instanceof Error ? error.message : String(error));
  }

  const fallbackDocs: FdaDocumentInput[] = [];
  for (const page of GUIDANCE_FALLBACK_PAGES) {
    try {
      const html = await fetchTextWithCache(env, page.url);
      fallbackDocs.push(
        ...parseGuidanceLinksFallback(html).map((document) => ({
          ...document,
          fdaCenter: document.fdaCenter ?? page.center,
          metadata: {
            ...(document.metadata ?? {}),
            fallbackCenterPage: page.center
          }
        }))
      );
    } catch (error) {
      errors.push(error instanceof Error ? error.message : String(error));
    }
  }

  if (fallbackDocs.length > 0) {
    return fallbackDocs;
  }

  throw new Error(`FDA guidance source unavailable: ${errors.join(" | ")}`);
}

export async function fetchPressAnnouncements(env: Env): Promise<FdaDocumentInput[]> {
  const docs: FdaDocumentInput[] = [];

  for (let page = 0; page < 2; page += 1) {
    const url = page === 0 ? FDA_SOURCES.press.url : `${FDA_SOURCES.press.url}?page=${page}`;
    const html = await fetchTextWithCache(env, url);
    docs.push(...parsePressAnnouncements(html, url));
  }

  return docs;
}

export async function fetchApprovals(env: Env): Promise<FdaDocumentInput[]> {
  const html = await fetchTextWithCache(env, FDA_SOURCES.approval.url);
  return parseApprovals(html, FDA_SOURCES.approval.url);
}

export async function fetchTextWithCache(env: Env, url: string): Promise<string> {
  const key = cacheKeyForUrl(url);
  const cached = await getCachedText(env, key);
  if (cached) return cached.value;

  try {
    const response = await fetch(url, {
      headers: {
        Accept: "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "RegAI-Realtime/0.1 regulatory-monitoring"
      },
      cf: {
        cacheTtl: getCacheTtlSeconds(env),
        cacheEverything: false
      }
    });

    if (!response.ok) {
      throw new Error(`FDA returned ${response.status} for ${url}`);
    }

    const text = await response.text();
    await putCachedText(env, key, text);
    return text;
  } catch (error) {
    const stale = await getCachedText(env, key, true);
    if (stale) return stale.value;
    throw error;
  }
}

async function enrichDocumentsWithDetailPages(
  env: Env,
  documents: FdaDocumentInput[]
): Promise<FdaDocumentInput[]> {
  const enriched: FdaDocumentInput[] = [];

  for (const document of documents) {
    try {
      const html = await fetchTextWithCache(env, document.url);
      const supportingDocuments = await discoverSupportingDocuments(document.url, html);
      const metadata =
        document.sourceType === "approval"
          ? extractFdaProductMetadata(html)
          : extractGenericDetailMetadata(html);
      const approvalDate = deriveApprovalDate(supportingDocuments, metadata);
      const preferredPdf =
        document.pdfUrl ??
        supportingDocuments.find((item) => item.type === "package_insert")?.fileUrl ??
        supportingDocuments.find((item) => item.fileUrl)?.fileUrl ??
        null;

      const mergedMetadata = {
        ...(document.metadata ?? {}),
        ...metadata,
        approvalDate,
        supportingDocumentCount: supportingDocuments.length,
        collectionStatus: supportingDocuments.length > 0 ? "complete" : "needs_review"
      };
      const sourceCurrentAsOf =
        typeof metadata.sourceCurrentAsOf === "string" ? metadata.sourceCurrentAsOf : null;

      const nextDocument: FdaDocumentInput = {
        ...document,
        title: deriveTitle(document, mergedMetadata),
        pdfUrl: preferredPdf,
        publishedDate: document.publishedDate ?? approvalDate ?? sourceCurrentAsOf,
        rawTextSnapshot: stripTags(html).slice(0, 12000),
        metadata: mergedMetadata,
        supportingDocuments
      };

      warnIfImportantApprovalFieldsMissing(nextDocument);
      enriched.push(nextDocument);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(
        JSON.stringify({
          level: "warn",
          event: "detail_discovery_failed",
          url: document.url,
          message,
          ts: new Date().toISOString()
        })
      );
      enriched.push({
        ...document,
        metadata: {
          ...(document.metadata ?? {}),
          collectionStatus: "using_cached_fda_data",
          discoveryWarning: message
        },
        supportingDocuments: document.supportingDocuments ?? []
      });
    }
  }

  return enriched;
}

function extractGenericDetailMetadata(html: string): Record<string, unknown> {
  const description = extractMetaContent(html, "description");
  const title = extractMetaContent(html, "dcterms.title") ?? extractMetaContent(html, "og:title");
  const sourceCurrentAsOf =
    extractMetaContent(html, "article:modified_time") ?? extractMetaContent(html, "og:updated_time");
  return {
    title,
    shortSummary: description,
    sourceCurrentAsOf,
    collectionStatus: "complete"
  };
}

function deriveApprovalDate(
  supportingDocuments: Awaited<ReturnType<typeof discoverSupportingDocuments>>,
  metadata: Record<string, unknown>
): string | null {
  const approvalLetterDate = supportingDocuments
    .filter((item) => item.type === "approval_letter")
    .map((item) => item.metadata?.detectedDate)
    .find((value): value is string => typeof value === "string" && value.length > 0);

  return approvalLetterDate ?? (typeof metadata.sourceCurrentAsOf === "string" ? metadata.sourceCurrentAsOf : null);
}

function deriveTitle(document: FdaDocumentInput, metadata: Record<string, unknown>): string {
  if (document.sourceType !== "approval") return document.title;
  const tradename = typeof metadata.tradename === "string" ? metadata.tradename.trim() : "";
  const properName = typeof metadata.properName === "string" ? metadata.properName.trim() : "";
  if (tradename && properName && !document.title.toLowerCase().includes(properName.toLowerCase())) {
    return `${tradename} (${properName})`;
  }
  return tradename || document.title;
}

function warnIfImportantApprovalFieldsMissing(document: FdaDocumentInput): void {
  if (document.sourceType !== "approval") return;
  const metadata = document.metadata ?? {};
  const missing = ["properName", "tradename", "manufacturer", "indication"].filter((key) => !metadata[key]);
  const hasPackageInsert = document.supportingDocuments?.some((item) => item.type === "package_insert") ?? false;
  if (!hasPackageInsert) missing.push("packageInsert");
  if (missing.length === 0) return;

  console.warn(
    JSON.stringify({
      level: "warn",
      event: "approval_metadata_incomplete",
      title: document.title,
      url: document.url,
      missing,
      ts: new Date().toISOString()
    })
  );
}

async function withContentHashes(documents: FdaDocumentInput[]): Promise<FdaDocumentInput[]> {
  const hashed: FdaDocumentInput[] = [];

  for (const document of documents) {
    hashed.push({
      ...document,
      contentHash: await hashRelevantContent({
        sourceType: document.sourceType,
        title: document.title,
        url: document.url,
        pdfUrl: document.pdfUrl ?? null,
        fdaCenter: document.fdaCenter ?? null,
        status: document.status ?? "unknown",
        topic: document.topic ?? null,
        publishedDate: document.publishedDate ?? null,
        rawTextSnapshot: document.rawTextSnapshot ?? "",
        metadata: document.metadata ?? {},
        supportingDocuments: document.supportingDocuments ?? []
      })
    });
  }

  return hashed;
}
