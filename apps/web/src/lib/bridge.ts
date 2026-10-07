// Fixed local transport adapter. Browser inputs never choose a destination or authority.
const BACKEND = "http://127.0.0.1:8765";
const UI_HOSTS = new Set(["127.0.0.1:3000", "localhost:3000"]);
const LIMIT = 262144;
const reads =
  /^(career|jobs(?:\/job_[0-9a-f]{32})?|profile(?:\/evidence)?|applications(?:\/application_[0-9a-f]{32})?|events|drafts\/draft_[0-9a-f]{32})$/;
const writes =
  /^(career|jobs|profile\/(?:claims|evidence)|profile\/evidence\/evidence_[0-9a-f]{32}\/(?:synthetic-review|withdraw)|profile\/claims\/claim_[0-9a-f]{32}\/synthetic-review|applications(?:\/application_[0-9a-f]{32}\/status)?|cvs(?:\/compare)?|drafts(?:\/draft_[0-9a-f]{32}\/(?:revise|review))?)$/;

function failure(status: number, code: string) {
  return Response.json(
    {
      schema_version: "actual-api-v1",
      error: {
        code,
        message:
          "The local request could not be completed. Reload current state before retrying a command.",
      },
      request_id: crypto.randomUUID(),
    },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

async function boundedBody(
  stream: ReadableStream<Uint8Array>,
  limit: number,
  timeout: number,
): Promise<Uint8Array> {
  const reader = stream.getReader();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("timeout")), timeout);
  });
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const part = await Promise.race([reader.read(), deadline]);
      if (part.done) break;
      length += part.value.byteLength;
      if (length > limit) throw new Error("size");
      chunks.push(part.value);
    }
    const body = new Uint8Array(length);
    let cursor = 0;
    for (const chunk of chunks) {
      body.set(chunk, cursor);
      cursor += chunk.byteLength;
    }
    return body;
  } catch (error) {
    void reader.cancel().catch(() => {});
    throw error;
  } finally {
    clearTimeout(timer);
    reader.releaseLock();
  }
}

export async function bridge(
  request: Request,
  segments: string[],
  send: typeof fetch = fetch,
): Promise<Response> {
  const host = request.headers.get("host");
  const origin = request.headers.get("origin");
  const site = request.headers.get("sec-fetch-site");
  const address = new URL(request.url);
  if (!host || !UI_HOSTS.has(host)) return failure(403, "INVALID_HOST");
  // Next may normalize the internal request URL to another local alias.
  // Browser authority remains the exact admitted Host/Origin pair; neither
  // alias can alter the fixed upstream destination.
  if (!UI_HOSTS.has(address.host) || address.protocol !== "http:")
    return failure(403, "INVALID_DESTINATION");
  if (origin !== null && origin !== `http://${host}`)
    return failure(403, "INVALID_ORIGIN");
  if (site !== null && !["none", "same-origin"].includes(site))
    return failure(403, "INVALID_SITE");
  const path = segments.join("/");
  if (
    segments.some((part) => !/^[a-z0-9_-]+$/.test(part)) ||
    !(request.method === "GET"
      ? reads.test(path)
      : request.method === "POST" && writes.test(path))
  )
    return failure(404, "RESOURCE_NOT_FOUND");
  const params = address.searchParams;
  if (
    [...params.keys()].some((key) => !["offset", "limit"].includes(key)) ||
    [...new Set(params.keys())].some(
      (key) => params.getAll(key).length !== 1,
    ) ||
    (params.size > 0 &&
      (request.method !== "GET" ||
        !["jobs", "applications", "events"].includes(path))) ||
    [...params.values()].some((value) => !/^\d{1,7}$/.test(value))
  )
    return failure(422, "INVALID_REQUEST");
  if (request.headers.has("content-encoding"))
    return failure(415, "UNSUPPORTED_ENCODING");
  const headers: Record<string, string> = {
    Accept: "application/json",
    Origin: BACKEND,
  };
  let body: Uint8Array | undefined;
  if (request.method === "POST") {
    if (
      request.headers
        .get("content-type")
        ?.split(";")[0]
        .trim()
        .toLowerCase() !== "application/json"
    )
      return failure(415, "JSON_REQUIRED");
    headers["Content-Type"] = "application/json";
    const declared = request.headers.get("content-length");
    if (
      declared !== null &&
      (!/^\d{1,10}$/.test(declared) || Number(declared) > LIMIT)
    )
      return failure(413, "BODY_TOO_LARGE");
    if (!request.body) return failure(422, "INVALID_JSON");
    try {
      body = await boundedBody(request.body, LIMIT, 5000);
    } catch (error) {
      return failure(
        error instanceof Error && error.message === "size" ? 413 : 408,
        error instanceof Error && error.message === "size"
          ? "BODY_TOO_LARGE"
          : "BODY_TIMEOUT",
      );
    }
    if (declared !== null && Number(declared) !== body.byteLength)
      return failure(400, "INVALID_LENGTH");
  } else if (request.body !== null) return failure(422, "UNEXPECTED_BODY");
  try {
    const upstream = await send(`${BACKEND}/api/v1/${path}${address.search}`, {
      method: request.method,
      headers,
      body: body as BodyInit | undefined,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10000),
    });
    if (!upstream.headers.get("content-type")?.includes("application/json"))
      return failure(502, "INVALID_BACKEND_RESPONSE");
    // Do not forward cookies, credentials, arbitrary response headers or error content logs.
    if (!upstream.body) return failure(502, "INVALID_BACKEND_RESPONSE");
    const result = await boundedBody(upstream.body, 2000000, 10000);
    return new Response(result as BodyInit, {
      status: upstream.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return failure(503, "BACKEND_UNAVAILABLE");
  }
}
