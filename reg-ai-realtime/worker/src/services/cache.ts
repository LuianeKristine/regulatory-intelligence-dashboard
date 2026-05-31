import type { Env } from "../types";

interface CachedTextPayload {
  value: string;
  cachedAt: string;
  expiresAt: string;
}

export function getCacheTtlSeconds(env: Env): number {
  const parsed = Number(env.CACHE_TTL_SECONDS ?? "900");
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 900;
}

export function cacheKeyForUrl(url: string): string {
  return `fda:${url}`;
}

export async function getCachedText(
  env: Env,
  key: string,
  allowStale = false
): Promise<{ value: string; stale: boolean } | null> {
  if (env.FDA_CACHE) {
    const raw = await env.FDA_CACHE.get(key);
    if (!raw) return null;

    const payload = JSON.parse(raw) as CachedTextPayload;
    const stale = Date.parse(payload.expiresAt) <= Date.now();
    if (!stale || allowStale) {
      return { value: payload.value, stale };
    }
    return null;
  }

  const request = new Request(`https://regai.local/cache/${encodeURIComponent(key)}`, {
    method: "GET"
  });
  const cached = await caches.default.match(request);
  if (!cached) return null;
  return { value: await cached.text(), stale: false };
}

export async function putCachedText(env: Env, key: string, value: string, ttlSeconds?: number): Promise<void> {
  const ttl = ttlSeconds ?? getCacheTtlSeconds(env);
  const cachedAt = new Date();
  const payload: CachedTextPayload = {
    value,
    cachedAt: cachedAt.toISOString(),
    expiresAt: new Date(cachedAt.getTime() + ttl * 1000).toISOString()
  };

  if (env.FDA_CACHE) {
    await env.FDA_CACHE.put(key, JSON.stringify(payload));
    return;
  }

  const request = new Request(`https://regai.local/cache/${encodeURIComponent(key)}`, {
    method: "GET"
  });
  await caches.default.put(
    request,
    new Response(value, {
      headers: {
        "Cache-Control": `public, max-age=${ttl}`,
        "Content-Type": "text/plain; charset=utf-8"
      }
    })
  );
}
