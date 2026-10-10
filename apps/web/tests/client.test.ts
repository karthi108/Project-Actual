import { afterEach, expect, it, vi } from "vitest";
import { api, ApiFailure } from "../src/lib/client";
afterEach(() => vi.unstubAllGlobals());
it("does not retry failed commands or persist client credentials", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      Response.json({ error: { code: "STALE_GENERATION" } }, { status: 409 }),
    );
  vi.stubGlobal("fetch", fetch);
  await expect(
    api("profile/claims", { expected_generation: 1 }),
  ).rejects.toMatchObject({ status: 409, code: "STALE_GENERATION" });
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0][1].credentials).toBe("omit");
  expect(fetch.mock.calls[0][1].cache).toBe("no-store");
});
it("does not render backend errors containing private/untrusted content", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json(
        {
          error: {
            code: "INVALID_REQUEST",
            message: "secret synthetic hostile text",
          },
        },
        { status: 422 },
      ),
    ),
  );
  try {
    await api("career");
    throw new Error("Expected rejection");
  } catch (error) {
    expect(error).toBeInstanceOf(ApiFailure);
    expect((error as Error).message).not.toContain("secret");
  }
});
