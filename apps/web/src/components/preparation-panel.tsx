"use client";

import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { components } from "@/lib/api.generated";
import { api, id, type Career } from "@/lib/client";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

type Comparison = components["schemas"]["CVComparison"];
type DraftView = components["schemas"]["DraftView"];
type Kind = components["schemas"]["PrepareDraft"]["material_kind"];

export function PreparationPanel({ career }: { career: Career }) {
  const cache = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [draft, setDraft] = useState<DraftView | null>(null);
  const snapshot = career.snapshot;
  async function command<T>(path: string, body: object): Promise<T | null> {
    if (busy || error) return null;
    setBusy(true);
    try {
      const result = await api<T>(path, {
        schema_version: "actual-api-v1",
        expected_generation: career.generation,
        ...body,
      });
      await cache.invalidateQueries({ queryKey: ["career"] });
      return result;
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unavailable");
      return null;
    } finally {
      setBusy(false);
    }
  }
  const disabled = busy || !!error;
  function form(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    return new FormData(event.currentTarget);
  }
  const currentComparison =
    comparison?.generation === career.generation ? comparison : null;
  const currentDraft = draft?.generation === career.generation ? draft : null;
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-600">
        Choose source-linked units, compare exact posting quotations, then
        inspect and review prepared content. Unverified claims stay separate.
        Submission remains manual.
      </p>
      {error && (
        <div role="alert">
          {error}{" "}
          <Button
            onClick={async () => {
              await cache.invalidateQueries({ queryKey: ["career"] });
              setComparison(null);
              setDraft(null);
              setError("");
            }}
          >
            Reload preparation
          </Button>
        </div>
      )}
      <Card>
        <h2 className="text-xl font-semibold">CV claim selection</h2>
        <form
          onSubmit={async (event) => {
            const data = form(event);
            await command("cvs", {
              id: id("cv"),
              name: data.get("name"),
              claim_ids: data.getAll("claim"),
            });
          }}
        >
          <label>
            Variant name
            <input name="name" required maxLength={256} />
          </label>
          {snapshot.profile.claims.map((claim) => (
            <label key={claim.id} className="flex gap-3 items-start">
              <input
                type="checkbox"
                name="claim"
                value={claim.id}
                className="w-auto"
              />
              <span>
                {claim.assertion.subject} {claim.assertion.value}{" "}
                {claim.assertion.unit} — {claim.status}
                <br />
                <small>{claim.id}</small>
              </span>
            </label>
          ))}
          <Button disabled={disabled || !snapshot.profile.claims.length}>
            Create CV variant
          </Button>
        </form>
      </Card>
      <Card>
        <h2 className="text-xl font-semibold">Compare source requirements</h2>
        <form
          onSubmit={async (event) => {
            const data = form(event);
            const result = await command<Comparison>("cvs/compare", {
              job_id: data.get("job"),
              selections: [
                {
                  quote: data.get("quote"),
                  term: data.get("term"),
                  priority: data.get("priority"),
                },
              ],
            });
            setComparison(result);
          }}
        >
          <label>
            Posting
            <select name="job">
              {snapshot.jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
          </label>
          <details>
            <summary>Original posting text</summary>
            {snapshot.jobs.map((job) => (
              <pre key={job.id}>
                {job.title}
                {"\n"}
                {job.text}
              </pre>
            ))}
          </details>
          <label>
            Exact quotation
            <textarea name="quote" required maxLength={512} />
          </label>
          <label>
            Term within quotation
            <input name="term" required maxLength={128} />
          </label>
          <label>
            Source priority
            <select name="priority">
              <option>essential</option>
              <option>preferred</option>
              <option>ambiguous</option>
            </select>
          </label>
          <Button disabled={disabled}>Compare CV coverage</Button>
        </form>
        {currentComparison && (
          <div className="mt-4 space-y-3">
            <p>{currentComparison.selection_basis}</p>
            {currentComparison.assessment.rows.map((row) => (
              <p key={row.requirement.id}>
                {row.requirement.source_quote} — <strong>{row.status}</strong>:{" "}
                {row.explanation}
              </p>
            ))}
            {currentComparison.options.map((option) => (
              <p key={option.cv_id}>
                {snapshot.cvs.find((cv) => cv.id === option.cv_id)?.name}:{" "}
                {option.covered_essential} essential, {option.covered_preferred}{" "}
                preferred units covered.
                {currentComparison.suggested_cv_ids.includes(option.cv_id)
                  ? " Suggested by selected-unit coverage."
                  : ""}
              </p>
            ))}
            <p>{currentComparison.limitation}</p>
            <details>
              <summary>
                Unverified user claims / unresolved declarations
              </summary>
              {currentComparison.unresolved_claims.map((claim) => (
                <p key={claim.id}>
                  {claim.text} — {claim.status}
                </p>
              ))}
            </details>
          </div>
        )}
      </Card>
      <Card>
        <h2 className="text-xl font-semibold">Prepare and review</h2>
        <form
          onSubmit={async (event) => {
            const data = form(event);
            const result = await command<DraftView>("drafts", {
              id: id("draft"),
              job_id: data.get("job"),
              cv_id: data.get("cv"),
              material_kind: data.get("kind"),
            });
            setDraft(result);
          }}
        >
          <label>
            Job
            <select name="job">
              {snapshot.jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            CV variant
            <select name="cv">
              {snapshot.cvs.map((cv) => (
                <option key={cv.id} value={cv.id}>
                  {cv.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Material
            <select name="kind">
              <option value="cv_adaptation">CV adaptation</option>
              <option value="application_message">Application message</option>
              <option value="cover_letter">Cover letter</option>
            </select>
          </label>
          <Button disabled={disabled || !snapshot.cvs.length}>
            Prepare material
          </Button>
        </form>
        <div className="my-4 flex flex-wrap gap-2">
          {snapshot.drafts.map((item) => (
            <Button
              key={item.id}
              variant="outline"
              disabled={disabled}
              onClick={async () => {
                try {
                  setDraft(await api<DraftView>(`drafts/${item.id}`));
                } catch {
                  setError("Draft unavailable. Reload.");
                }
              }}
            >
              Inspect revision {item.revision} (
              {item.review?.decision ?? "unreviewed"})
            </Button>
          ))}
        </div>
        {currentDraft && (
          <article className="space-y-3 border-t pt-4">
            <p>{currentDraft.draft.summary}</p>
            {currentDraft.draft.assertions.map((unit, index) => (
              <div key={index}>
                <p>{unit.text}</p>
                <details>
                  <summary>Inspect supporting claims and sources</summary>
                  {unit.source_claim_refs.map((ref) => {
                    const claim = snapshot.profile.claims.find(
                      (item) => item.id === ref.claim_id,
                    );
                    return (
                      <div key={ref.claim_id}>
                        <pre>{JSON.stringify(ref, null, 2)}</pre>
                        <p>{claim?.text}</p>
                        {claim?.evidence_refs.map((source) => (
                          <pre key={source.evidence_id}>
                            {String(
                              snapshot.profile.evidence.find(
                                (item) => item.id === source.evidence_id,
                              )?.excerpt ?? "Unavailable",
                            )}
                          </pre>
                        ))}
                      </div>
                    );
                  })}
                </details>
              </div>
            ))}
            <p className="text-xs">
              Revision {currentDraft.draft.revision}, digest{" "}
              {currentDraft.content_digest}
            </p>
            {currentDraft.draft.preparation && (
              <div className="flex flex-wrap gap-2">
                {(["accepted", "rejected"] as const).map((decision) => (
                  <Button
                    key={decision}
                    disabled={disabled || !!currentDraft.draft.review}
                    onClick={async () =>
                      setDraft(
                        await command<DraftView>(
                          `drafts/${currentDraft.draft.id}/review`,
                          {
                            expected_revision: currentDraft.draft.revision,
                            expected_digest: currentDraft.content_digest,
                            decision,
                          },
                        ),
                      )
                    }
                  >
                    {decision === "accepted"
                      ? "Accept exact content"
                      : "Reject exact content"}
                  </Button>
                ))}
                <Button
                  variant="outline"
                  disabled={disabled}
                  onClick={async () =>
                    setDraft(
                      await command<DraftView>(
                        `drafts/${currentDraft.draft.id}/revise`,
                        {
                          expected_revision: currentDraft.draft.revision,
                          expected_digest: currentDraft.content_digest,
                          job_id: currentDraft.draft.preparation!.job.object_id,
                          cv_id: currentDraft.draft.preparation!.cv.object_id,
                          material_kind: currentDraft.draft.preparation!
                            .material_kind as Kind,
                        },
                      ),
                    )
                  }
                >
                  Create new unreviewed revision
                </Button>
              </div>
            )}
          </article>
        )}
      </Card>
    </div>
  );
}
