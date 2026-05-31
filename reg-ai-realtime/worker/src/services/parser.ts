import type { FdaDocumentInput, GuidanceStatus, SourceType } from "../types";

export const FDA_BASE_URL = "https://www.fda.gov";

const TARGET_CENTER_CODES = new Set(["CDER", "CBER", "OCE"]);

export function decodeHtml(value: string): string {
  const named: Record<string, string> = {
    amp: "&",
    lt: "<",
    gt: ">",
    quot: "\"",
    apos: "'",
    nbsp: " "
  };

  return value
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (_, entity: string) => {
      const lower = entity.toLowerCase();
      if (lower.startsWith("#x")) {
        return String.fromCharCode(Number.parseInt(lower.slice(2), 16));
      }
      if (lower.startsWith("#")) {
        return String.fromCharCode(Number.parseInt(lower.slice(1), 10));
      }
      return named[lower] ?? `&${entity};`;
    })
    .replace(/\u00a0/g, " ");
}

export function stripTags(html: string | null | undefined): string {
  if (!html) return "";
  return decodeHtml(
    html
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/<\/(p|div|li|tr|td|th|h\d)>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
  );
}

export function absoluteUrl(href: string | null | undefined, base = FDA_BASE_URL): string | null {
  if (!href) return null;
  const clean = decodeHtml(href.trim());
  if (!clean || clean.startsWith("#") || clean.startsWith("mailto:") || clean.startsWith("tel:")) {
    return null;
  }
  try {
    return new URL(clean, base).toString();
  } catch {
    return null;
  }
}

export function extractAttribute(html: string, attr: string): string | null {
  const match = new RegExp(`${attr}\\s*=\\s*["']([^"']+)["']`, "i").exec(html);
  return match?.[1] ? decodeHtml(match[1]) : null;
}

export function extractLinks(html: string): Array<{ href: string; text: string; html: string }> {
  const links: Array<{ href: string; text: string; html: string }> = [];
  const re = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match: RegExpExecArray | null;

  while ((match = re.exec(html)) !== null) {
    const href = absoluteUrl(match[1]);
    if (!href) continue;
    links.push({
      href,
      text: stripTags(match[2]),
      html: match[0]
    });
  }

  return links;
}

function firstLink(html: string, predicate?: (href: string) => boolean): string | null {
  for (const link of extractLinks(html)) {
    if (!predicate || predicate(link.href)) return link.href;
  }
  return null;
}

function cleanCell(cell: unknown): string {
  if (cell === null || typeof cell === "undefined") return "";
  return stripTags(String(cell));
}

function getArrayCell(row: unknown[], index: number): string {
  return typeof row[index] === "undefined" ? "" : String(row[index]);
}

function getObjectCell(row: Record<string, unknown>, names: string[]): string {
  const lowerMap = new Map(Object.keys(row).map((key) => [key.toLowerCase(), key]));
  for (const name of names) {
    const key = lowerMap.get(name.toLowerCase());
    if (key && typeof row[key] !== "undefined") return String(row[key]);
  }
  return "";
}

export function normalizeStatus(value: string | null | undefined): GuidanceStatus {
  const clean = stripTags(value ?? "").toLowerCase();
  if (clean.includes("draft")) return "draft";
  if (clean.includes("final")) return "final";
  return "unknown";
}

export function normalizeCenter(value: string | null | undefined): string | null {
  const clean = stripTags(value ?? "");
  const upper = clean.toUpperCase();
  if (upper.includes("CDER") || clean.includes("Center for Drug Evaluation and Research")) return "CDER";
  if (upper.includes("CBER") || clean.includes("Center for Biologics Evaluation and Research")) return "CBER";
  if (upper.includes("OCE") || clean.includes("Oncology Center")) return "OCE";
  return clean || null;
}

export function isTargetCenter(center: string | null): boolean {
  if (!center) return true;
  return TARGET_CENTER_CODES.has(center.toUpperCase());
}

export function parseDateToIso(value: string | null | undefined): string | null {
  const clean = stripTags(value ?? "").replace(/\s+-\s+.*$/, "").trim();
  if (!clean) return null;
  const parsed = new Date(clean);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

export function extractMetaContent(html: string, nameOrProperty: string): string | null {
  const escaped = nameOrProperty.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(
    `<meta\\s+(?:name|property)=["']${escaped}["']\\s+content=["']([^"']+)["']`,
    "i"
  );
  const reverseRe = new RegExp(
    `<meta\\s+content=["']([^"']+)["']\\s+(?:name|property)=["']${escaped}["']`,
    "i"
  );
  return decodeHtml(re.exec(html)?.[1] ?? reverseRe.exec(html)?.[1] ?? "") || null;
}

function extractStrongValue(html: string, label: string): string | null {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const inline = new RegExp(
    `<strong>\\s*${escaped}\\s*:?\\s*<\\/strong>\\s*([^<\\n]+(?:<br\\s*\\/?>)?[^<\\n]*)`,
    "i"
  ).exec(html);
  const value = stripTags(inline?.[1] ?? "");
  return value || null;
}

function extractIndication(html: string): string | null {
  const afterLabel = /<strong>\s*Indication\s*:?\s*<\/strong>[\s\S]*?(?:<ul[^>]*>([\s\S]*?)<\/ul>|<p[^>]*>([\s\S]*?)<\/p>)/i.exec(
    html
  );
  const value = stripTags(afterLabel?.[1] ?? afterLabel?.[2] ?? "");
  return value || extractMetaContent(html, "description");
}

function extractContentCurrentAsOf(html: string): string | null {
  const match = /Content current as of:[\s\S]*?<time\b[^>]*datetime=["']([^"']+)["']/i.exec(html);
  if (match?.[1]) return parseDateToIso(match[1]);
  const meta = /property=["']article:modified_time["']\s+content=["']([^"']+)["']/i.exec(html);
  return meta?.[1] ? parseDateToIso(meta[1]) : null;
}

export function extractFdaProductMetadata(html: string): Record<string, unknown> {
  const stn = extractStrongValue(html, "STN");
  const properName = extractStrongValue(html, "Proper Name");
  const tradename = extractStrongValue(html, "Tradename") ?? extractMetaContent(html, "dcterms.title");
  const manufacturer = extractStrongValue(html, "Manufacturer");
  const indication = extractIndication(html);
  const description = extractMetaContent(html, "description");
  const currentAsOf = extractContentCurrentAsOf(html);

  return {
    stn,
    properName,
    tradename,
    manufacturer,
    sponsor: manufacturer,
    indication,
    productCategory: "Cellular and Gene Therapy Product",
    sourceCurrentAsOf: currentAsOf,
    shortSummary: indication ?? description,
    extractionStatus: "complete"
  };
}

function pickGuidanceCells(row: unknown): {
  documentHtml: string;
  dateHtml: string;
  centerHtml: string;
  topicHtml: string;
  statusHtml: string;
  allHtml: string;
} {
  if (Array.isArray(row)) {
    return {
      documentHtml: getArrayCell(row, 1),
      dateHtml: getArrayCell(row, 2),
      centerHtml: getArrayCell(row, 3) || getArrayCell(row, 12),
      topicHtml: getArrayCell(row, 6) || getArrayCell(row, 5),
      statusHtml: getArrayCell(row, 7),
      allHtml: row.map((cell) => String(cell ?? "")).join(" ")
    };
  }

  const objectRow = row && typeof row === "object" ? (row as Record<string, unknown>) : {};
  const values = Object.values(objectRow).map((value) => String(value ?? ""));
  return {
    documentHtml:
      getObjectCell(objectRow, ["document", "title", "field_title", "field_document"]) || values[1] || values[0] || "",
    dateHtml: getObjectCell(objectRow, ["issue_date", "date", "published_date"]) || values[2] || "",
    centerHtml: getObjectCell(objectRow, ["fda_organization", "center", "organization"]) || values[3] || "",
    topicHtml: getObjectCell(objectRow, ["topic", "field_topic"]) || values[6] || values[5] || "",
    statusHtml: getObjectCell(objectRow, ["guidance_status", "status"]) || values[7] || "",
    allHtml: values.join(" ")
  };
}

export function parseGuidanceDatatablesPayload(payload: unknown): FdaDocumentInput[] {
  const objectPayload = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const rows = Array.isArray(objectPayload.data) ? objectPayload.data : [];
  const documents: FdaDocumentInput[] = [];

  for (const row of rows) {
    const cells = pickGuidanceCells(row);
    const title = cleanCell(cells.documentHtml);
    const url = firstLink(cells.documentHtml, (href) => !href.toLowerCase().endsWith(".pdf")) ?? firstLink(cells.allHtml);
    const pdfUrl = firstLink(cells.allHtml, (href) => href.toLowerCase().includes(".pdf"));
    const fdaCenter = normalizeCenter(cells.centerHtml);

    if (!title || !url || !isTargetCenter(fdaCenter)) continue;

    documents.push({
      sourceType: "guidance",
      title,
      url,
      pdfUrl,
      fdaCenter,
      status: normalizeStatus(cells.statusHtml),
      topic: cleanCell(cells.topicHtml) || null,
      publishedDate: parseDateToIso(cells.dateHtml),
      rawTextSnapshot: stripTags(cells.allHtml),
      metadata: {
        parser: "guidance_datatables",
        originalCenter: cleanCell(cells.centerHtml)
      }
    });
  }

  return dedupeDocuments(documents);
}

export function parseGuidanceLinksFallback(html: string): FdaDocumentInput[] {
  // FDA renders the guidance table through DataTables. This fallback catches useful
  // guidance links if the JSON endpoint changes or is temporarily blocked.
  const candidates = extractLinks(html).filter((link) => {
    const text = link.text.toLowerCase();
    const href = link.href.toLowerCase();
    return href.includes("guidance") && text.includes("guidance") && !href.includes("search-fda-guidance-documents");
  });

  return dedupeDocuments(
    candidates.slice(0, 80).map((link) => ({
      sourceType: "guidance" as SourceType,
      title: link.text,
      url: link.href,
      pdfUrl: link.href.toLowerCase().includes(".pdf") ? link.href : null,
      fdaCenter: null,
      status: normalizeStatus(link.text),
      topic: null,
      publishedDate: null,
      rawTextSnapshot: link.text,
      metadata: {
        parser: "guidance_link_fallback"
      }
    }))
  );
}

export function parsePressAnnouncements(html: string, pageUrl: string): FdaDocumentInput[] {
  const documents: FdaDocumentInput[] = [];
  const re = /<a\b[^>]*href=["']([^"']+)["'][^>]*>\s*<time\b[^>]*datetime=["']([^"']+)["'][^>]*>[\s\S]*?<\/time>\s*-\s*([\s\S]*?)<\/a>/gi;
  let match: RegExpExecArray | null;

  while ((match = re.exec(html)) !== null) {
    const url = absoluteUrl(match[1]);
    const title = stripTags(match[3]);
    if (!url || !title) continue;

    documents.push({
      sourceType: "press",
      title,
      url,
      pdfUrl: null,
      fdaCenter: null,
      status: "unknown",
      topic: "Press Announcement",
      publishedDate: parseDateToIso(match[2]),
      rawTextSnapshot: `${match[2]} ${title}`,
      metadata: {
        parser: "press_listing",
        listingPage: pageUrl,
        summary: null
      }
    });
  }

  return dedupeDocuments(documents);
}

function extractTableCells(rowHtml: string): string[] {
  const cells: string[] = [];
  const re = /<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(rowHtml)) !== null) {
    cells.push(match[1] ?? "");
  }
  return cells;
}

export function parseApprovals(html: string, sourceUrl: string): FdaDocumentInput[] {
  const sourceCurrentAsOf = extractContentCurrentAsOf(html);
  const documents: FdaDocumentInput[] = [];
  const rowRe = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
  let match: RegExpExecArray | null;

  while ((match = rowRe.exec(html)) !== null) {
    const rowHtml = match[1] ?? "";
    const cells = extractTableCells(rowHtml);
    if (cells.length < 2) continue;

    const productCell = cells[0] ?? "";
    const sponsorCell = cells[1] ?? "";
    const productLink = firstLink(productCell);
    const productName = stripTags(productCell);
    const sponsor = stripTags(sponsorCell);
    if (!productName || !productLink || productName.toLowerCase() === "product") continue;

    const rowLinks = extractLinks(rowHtml).map((link) => link.href);
    documents.push({
      sourceType: "approval",
      title: productName,
      url: productLink,
      pdfUrl: rowLinks.find((href) => href.toLowerCase().includes(".pdf")) ?? null,
      fdaCenter: "CBER",
      status: "final",
      topic: "Cellular and Gene Therapy Products",
      publishedDate: null,
      rawTextSnapshot: `${productName} ${sponsor} ${rowLinks.join(" ")}`,
      metadata: {
        parser: "approval_table",
        sponsor,
        indication: null,
        approvalDate: null,
        sourcePage: sourceUrl,
        sourceCurrentAsOf,
        relatedLinks: rowLinks
      }
    });
  }

  return dedupeDocuments(documents);
}

export function dedupeDocuments(documents: FdaDocumentInput[]): FdaDocumentInput[] {
  const seen = new Set<string>();
  const deduped: FdaDocumentInput[] = [];

  for (const document of documents) {
    const key = document.url.trim().toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(document);
  }

  return deduped;
}
