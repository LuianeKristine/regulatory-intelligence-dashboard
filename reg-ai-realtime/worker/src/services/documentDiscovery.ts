import type { SupportingDocumentInput, SupportingDocumentType } from "../types";
import { hashRelevantContent } from "./hash";
import { absoluteUrl, extractAttribute, extractLinks, parseDateToIso, stripTags } from "./parser";

interface DiscoveryLink {
  href: string;
  text: string;
  html: string;
}

const RELEVANT_TERMS = [
  "package insert",
  "approval letter",
  "clinical review",
  "statistical review",
  "summary basis",
  "sbra",
  "prescribing information",
  "label",
  "fda review",
  "briefing document",
  "presentation",
  "transcript",
  "agenda",
  "questions",
  "review memo",
  "supporting document"
];

export async function discoverSupportingDocuments(
  sourcePageUrl: string,
  html: string
): Promise<SupportingDocumentInput[]> {
  const links = extractLinks(html)
    .map((link) => enrichLink(link, sourcePageUrl))
    .filter((link): link is DiscoveryLink => Boolean(link));

  const documents: SupportingDocumentInput[] = [];
  const seen = new Set<string>();

  for (const link of links) {
    const text = link.text || extractAttribute(link.html, "title") || link.href;
    const keyText = `${text} ${link.href}`.toLowerCase();
    const isFdaDownload = /\/media\/\d+\/download/i.test(link.href);
    const isPdf = /\.pdf($|\?)/i.test(link.href) || isFdaDownload;
    const isRelevant = isPdf || RELEVANT_TERMS.some((term) => keyText.includes(term));

    if (!isRelevant) continue;

    const type = classifySupportingDocument(keyText);
    const fileType = isFdaDownload ? "PDF" : isPdf ? "PDF" : link.href.includes("/download") ? "Download" : "HTML";
    const cleanTitle = normalizeTitle(text, type);
    const url = link.href;
    const fingerprint = `${type}:${url}`.toLowerCase();
    if (seen.has(fingerprint)) continue;
    seen.add(fingerprint);

    const metadata = {
      extractionStatus: "identified_from_fda_page",
      detectedDate: extractDateFromText(text),
      originalText: text
    };

    documents.push({
      type,
      title: cleanTitle,
      url,
      fileUrl: fileType === "HTML" ? null : url,
      fileType,
      sourcePageUrl,
      contentHash: await hashRelevantContent({ type, title: cleanTitle, url, fileType, sourcePageUrl }),
      metadata
    });
  }

  return documents;
}

function enrichLink(
  link: { href: string; text: string; html: string },
  sourcePageUrl: string
): DiscoveryLink | null {
  const href = absoluteUrl(link.href, sourcePageUrl);
  if (!href) return null;
  const title = extractAttribute(link.html, "title");
  return {
    href,
    text: stripTags(title || link.text),
    html: link.html
  };
}

export function classifySupportingDocument(value: string): SupportingDocumentType {
  const text = value.toLowerCase();
  if (text.includes("package insert")) return "package_insert";
  if (text.includes("approval letter")) return "approval_letter";
  if (text.includes("clinical review") || text.includes("clinical pharmacology review")) return "clinical_review";
  if (text.includes("statistical review")) return "statistical_review";
  if (text.includes("summary basis") || text.includes("sbra")) return "sbra";
  if (text.includes("prescribing information")) return "prescribing_information";
  if (text.includes("label")) return "label";
  if (text.includes("fda review") || text.includes("review memo")) return "fda_review";
  if (text.includes("briefing document")) return "briefing_document";
  if (text.includes("presentation")) return "presentation";
  if (text.includes("transcript")) return "transcript";
  if (text.includes("agenda")) return "agenda";
  if (text.includes("questions")) return "questions";
  return "other";
}

function normalizeTitle(value: string, type: SupportingDocumentType): string {
  const clean = stripTags(value).replace(/\s+/g, " ").trim();
  if (clean) return clean;
  return supportingDocumentTypeLabel(type);
}

export function supportingDocumentTypeLabel(type: SupportingDocumentType): string {
  return {
    package_insert: "Package Insert",
    approval_letter: "Approval Letter",
    clinical_review: "Clinical Review",
    statistical_review: "Statistical Review",
    sbra: "Summary Basis for Regulatory Action",
    prescribing_information: "Prescribing Information",
    label: "Label",
    fda_review: "FDA Review",
    briefing_document: "Briefing Document",
    presentation: "Presentation",
    transcript: "Transcript",
    agenda: "Agenda",
    questions: "Questions",
    other: "Supporting Document"
  }[type];
}

function extractDateFromText(value: string): string | null {
  const monthDate = /(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}/i.exec(
    value
  );
  return monthDate?.[0] ? parseDateToIso(monthDate[0]) : null;
}
