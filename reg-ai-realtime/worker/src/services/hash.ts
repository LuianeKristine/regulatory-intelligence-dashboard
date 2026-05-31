import type { SourceType } from "../types";

function toHex(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function sha256(input: string): Promise<string> {
  const encoded = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return toHex(digest);
}

export async function stableDocumentId(sourceType: SourceType, url: string): Promise<string> {
  return `${sourceType}_${(await sha256(`${sourceType}:${url.trim().toLowerCase()}`)).slice(0, 32)}`;
}

export async function versionId(documentId: string, hash: string): Promise<string> {
  return `ver_${(await sha256(`${documentId}:${hash}:${Date.now()}`)).slice(0, 32)}`;
}

export function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map(canonicalStringify).join(",")}]`;
  }

  const record = value as Record<string, unknown>;
  return `{${Object.keys(record)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalStringify(record[key])}`)
    .join(",")}}`;
}

export async function hashRelevantContent(value: unknown): Promise<string> {
  return sha256(canonicalStringify(value));
}
