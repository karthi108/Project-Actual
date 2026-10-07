import { test, expect } from "@playwright/test";

// Requires the real isolated synthetic API at 8765 with a fresh migrated disposable DB.
// No provider/browser mocks: this exercises browser -> bridge -> accepted API -> PostgreSQL.
test("fabricated career journey preserves review distinctions and recorded tracking", async ({
  page,
}) => {
  const initialRead = page.waitForResponse((response) =>
    response.url().endsWith("/api/actual/career"),
  );
  await page.goto("/");
  const initialResponse = await initialRead;
  const initialBody = await initialResponse.json();
  expect(
    initialResponse.status(),
    initialBody.error?.code ?? "initial career read",
  ).toBe(404);
  await expect(
    page.getByRole("heading", { name: "Begin with a synthetic example" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Create fabricated example" }).click();
  await expect(page.getByText("generation 1", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await page
    .getByRole("button", { name: "Record self-reported claim" })
    .click();
  await expect(page.getByText("Declared 1 · self_reported")).toBeVisible();
  await page
    .getByRole("button", { name: "Attach unreviewed synthetic source" })
    .click();
  await page.getByText("Evidence references", { exact: true }).click();
  await expect(
    page.getByText(
      "Synthetic fixture source describes the structured assertion above.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Review exact synthetic source" })
    .click();
  await expect(page.getByText("Declared 1 · self_reported")).toBeVisible();
  await page
    .getByRole("button", { name: "Review exact synthetic claim" })
    .click();
  await expect(page.getByText("Declared 1 · reviewed_supported")).toBeVisible();
  await page.getByRole("button", { name: "Withdraw source" }).click();
  await expect(page.getByText("Declared 1 · candidate_support")).toBeVisible();
  await page.getByRole("button", { name: "Jobs", exact: true }).click();
  await page.getByRole("button", { name: "Start preparing" }).click();
  await page.getByRole("button", { name: "Applications", exact: true }).click();
  await expect(
    page.getByText("preparing", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByLabel("Next reported status")
    .selectOption("ready_for_review");
  await page.getByRole("button", { name: "Record status" }).click();
  await expect(
    page.getByText("ready for review", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Next reported status").selectOption("offer");
  await page.getByRole("button", { name: "Record status" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Reload" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Record status" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Reload", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Record status" }),
  ).toBeEnabled();
  await expect(
    page.getByText("ready for review", { exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/career-workspace.png",
    fullPage: true,
  });
});

test("cross-site commands are rejected before the backend", async ({
  request,
}) => {
  const result = await request.post("/api/actual/career", {
    headers: { Origin: "https://hostile.invalid" },
    data: { expected_generation: 0 },
  });
  expect(result.status()).toBe(403);
});
