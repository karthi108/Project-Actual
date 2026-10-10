import { describe, expect, it, vi } from "vitest";
import { bridge } from "../src/lib/bridge";
function request(
  path = "career",
  method = "GET",
  headers: Record<string, string> = {},
  body?: string,
) {
  return new Request(`http://127.0.0.1:3000/api/actual/${path}`, {
    method,
    headers: { Host: "127.0.0.1:3000", ...headers },
    body,
  });
}
function provider() {
  return vi
    .fn<typeof fetch>()
    .mockResolvedValue(
      Response.json({ schema_version: "actual-api-v1", generation: 1 }),
    );
}
describe("local browser boundary", () => {
  it("admits Next's normalized local URL while retaining exact browser Host/Origin checks", async () => {
    const send = provider();
    const request = new Request("http://localhost:3000/api/actual/career", {
      headers: {
        Host: "127.0.0.1:3000",
        Origin: "http://127.0.0.1:3000",
        "Sec-Fetch-Site": "same-origin",
      },
    });
    expect((await bridge(request, ["career"], send)).status).toBe(200);
    expect(send.mock.calls[0][0]).toBe("http://127.0.0.1:8765/api/v1/career");
    const alien = new Request("http://hostile.invalid:3000/api/actual/career", {
      headers: { Host: "127.0.0.1:3000" },
    });
    expect((await bridge(alien, ["career"], send)).status).toBe(403);
    expect(send).toHaveBeenCalledOnce();
  });
  it("forwards a permitted operation only to the fixed API and drops client authority", async () => {
    const send = provider();
    const result = await bridge(
      request("career", "GET", {
        Authorization: "Bearer synthetic",
        Cookie: "fake=secret",
        "X-Forwarded-Host": "evil.invalid",
      }),
      ["career"],
      send,
    );
    expect(result.status).toBe(200);
    expect(send).toHaveBeenCalledOnce();
    expect(send.mock.calls[0][0]).toBe("http://127.0.0.1:8765/api/v1/career");
    const init = send.mock.calls[0][1]!;
    expect(init.headers).toEqual({
      Accept: "application/json",
      Origin: "http://127.0.0.1:8765",
    });
    expect(init.redirect).toBe("error");
    expect(result.headers.has("set-cookie")).toBe(false);
  });
  it.each<Record<string, string>>([
    { Origin: "https://evil.invalid" },
    { Origin: "http://localhost:3000" },
    { Host: "evil.invalid" },
    { "Sec-Fetch-Site": "cross-site" },
    { "Sec-Fetch-Site": "same-site" },
  ])("rejects alien browser context %j before transport", async (headers) => {
    const send = provider();
    expect(
      (await bridge(request("career", "GET", headers), ["career"], send))
        .status,
    ).toBe(403);
    expect(send).not.toHaveBeenCalled();
  });
  it.each([
    { path: ["..", "career"] },
    { path: ["http:", "evil.invalid"] },
    { path: ["career%2f.."] },
    { path: ["models"] },
    { path: ["jobs", "job_" + "a".repeat(31)] },
  ])("rejects arbitrary paths %j", async ({ path }) => {
    const send = provider();
    expect((await bridge(request(), path, send)).status).toBe(404);
    expect(send).not.toHaveBeenCalled();
  });
  it.each([
    "career?url=https://evil.invalid",
    "jobs?offset=1&offset=2",
    "career?limit=20",
    "jobs?limit=-1",
  ])("rejects arbitrary/ambiguous query %s", async (path) => {
    const send = provider();
    expect(
      (await bridge(request(path), [path.split("?")[0]], send)).status,
    ).toBe(422);
    expect(send).not.toHaveBeenCalled();
  });
  it("forwards exact command bytes without granting review authority", async () => {
    const body = '{"expected_generation":3,"unexpected":"authority"}';
    const send = provider();
    const result = await bridge(
      request(
        "profile/claims",
        "POST",
        { "Content-Type": "application/json", Origin: "http://127.0.0.1:3000" },
        body,
      ),
      ["profile", "claims"],
      send,
    );
    expect(result.status).toBe(200);
    expect(
      new TextDecoder().decode(send.mock.calls[0][1]!.body as Uint8Array),
    ).toBe(body);
    // The existing closed backend DTO, not this transport adapter, rejects extra fields.
  });
  it("rejects oversized chunked commands and compressed requests", async () => {
    const send = provider();
    expect(
      (
        await bridge(
          request(
            "career",
            "POST",
            { "Content-Type": "application/json" },
            "x".repeat(262145),
          ),
          ["career"],
          send,
        )
      ).status,
    ).toBe(413);
    expect(
      (
        await bridge(
          request(
            "career",
            "POST",
            { "Content-Type": "application/json", "Content-Encoding": "gzip" },
            "{}",
          ),
          ["career"],
          send,
        )
      ).status,
    ).toBe(415);
    expect(send).not.toHaveBeenCalled();
  });
  it("does not retry an uncertain command outcome", async () => {
    const send = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new Error("Synthetic response lost"));
    expect(
      (
        await bridge(
          request(
            "career",
            "POST",
            { "Content-Type": "application/json" },
            "{}",
          ),
          ["career"],
          send,
        )
      ).status,
    ).toBe(503);
    expect(send).toHaveBeenCalledOnce();
  });
  it("rejects non-JSON provider content and forwards safe backend errors", async () => {
    const send = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("<script>evil</script>", {
        headers: { "Content-Type": "text/html" },
      }),
    );
    expect((await bridge(request(), ["career"], send)).status).toBe(502);
    send.mockResolvedValue(
      Response.json({ error: { code: "STALE_GENERATION" } }, { status: 409 }),
    );
    expect((await bridge(request(), ["career"], send)).status).toBe(409);
  });
});
