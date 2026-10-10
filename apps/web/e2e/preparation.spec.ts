import { test, expect } from "@playwright/test";

test("source-linked preparation is reviewed exactly and revision clears review", async ({
  page,
  request,
}) => {
  const read = async () => (await request.get("/api/actual/career")).json();
  const post = async (path: string, body: object) => {
    const response = await request.post(`/api/actual/${path}`, { data: body });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  };
  let state = await read();
  const claimId = `claim_${"a".repeat(32)}`;
  const sourceId = `evidence_${"a".repeat(32)}`;
  const assertion = {
    kind: "skill",
    subject: "javascript",
    unit: "skill_level",
    value: 1,
  };
  await post("profile/claims", {
    expected_generation: state.generation,
    id: claimId,
    assertion,
    text: "Explicitly synthetic JavaScript declaration.",
  });
  state = await read();
  await post("profile/evidence", {
    expected_generation: state.generation,
    id: sourceId,
    claim_id: claimId,
    assertion,
    relation: "supports",
    source_kind: "synthetic_fixture",
    source_reference: "synthetic:preparation-browser",
    excerpt: "Fabricated JavaScript unit 1 source.",
    collected_at: new Date().toISOString(),
  });
  const projection = async () =>
    (await request.get("/api/actual/profile/evidence")).json();
  let view = await projection();
  let row = view.profile.rows.find(
    (item: { subject: string }) => item.subject === "javascript",
  );
  let ref = row.unreviewed_evidence_refs[0];
  await post(`profile/evidence/${sourceId}/synthetic-review`, {
    expected_generation: view.generation,
    expected_revision: ref.revision,
    expected_digest: ref.content_digest,
  });
  view = await projection();
  row = view.profile.rows.find(
    (item: { subject: string }) => item.subject === "javascript",
  );
  ref = row.declarations[0].claim_ref;
  await post(`profile/claims/${claimId}/synthetic-review`, {
    expected_generation: view.generation,
    expected_revision: ref.revision,
    expected_digest: ref.content_digest,
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Preparation", exact: true }).click();
  await page.getByLabel("Variant name").fill("Synthetic browser CV");
  await page.locator(`input[value="${claimId}"]`).check();
  await page.getByRole("button", { name: "Create CV variant" }).click();
  await expect(page.getByLabel("CV variant")).toContainText(
    "Synthetic browser CV",
  );
  await page.getByRole("button", { name: "Prepare material" }).click();
  await expect(
    page.getByText("javascript: supported skill unit 1/3.", { exact: true }),
  ).toBeVisible();
  await page.getByText("Inspect supporting claims and sources").click();
  await expect(
    page.getByText("Fabricated JavaScript unit 1 source.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Accept exact content" }).click();
  await expect(
    page.getByRole("button", { name: "Accept exact content" }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Create new unreviewed revision" })
    .click();
  await expect(
    page.getByRole("button", { name: "Accept exact content" }),
  ).toBeEnabled();
  await expect(page.getByText(/Revision 3, digest/)).toBeVisible();
  await page.screenshot({
    path: "test-results/preparation.png",
    fullPage: true,
  });
});
