"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  CheckCheck,
  FileText,
  Layers3,
  LayoutDashboard,
  RefreshCw,
  Settings2,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import {
  api,
  ApiFailure,
  id,
  type Application,
  type Assertion,
  type Career,
  type EvidenceProfile,
  type Job,
} from "@/lib/client";
import type { components } from "@/lib/api.generated";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

type Screen =
  "Overview" | "Jobs" | "Profile" | "Skills" | "Applications" | "Settings";
const navigation = [
  ["Overview", LayoutDashboard],
  ["Jobs", BriefcaseBusiness],
  ["Profile", UserRound],
  ["Skills", Layers3],
  ["Applications", FileText],
  ["Settings", Settings2],
] as const;
function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full border border-teal-900/10 bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-900">
      {children}
    </span>
  );
}
function Field({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <label>
      <span>{title}</span>
      {children}
    </label>
  );
}
function Table<T>({ items, columns }: { items: T[]; columns: ColumnDef<T>[] }) {
  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
  return (
    <div className="overflow-x-auto">
      <table>
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => (
                <th key={header.id}>
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && (
        <p className="py-8 text-center text-sm text-slate-500">
          No records yet. Add synthetic data to begin.
        </p>
      )}
    </div>
  );
}

export function CareerWorkspace() {
  const [screen, setScreen] = useState<Screen>("Overview");
  const [focusJob, setFocusJob] = useState<Job | null>(null);
  const [expandedSources, setExpandedSources] = useState<
    Record<string, boolean>
  >({});
  const [blocked, setBlocked] = useState(false);
  const cache = useQueryClient();
  const career = useQuery({
    queryKey: ["career"],
    queryFn: () => api<Career>("career"),
  });
  const evidence = useQuery({
    queryKey: ["evidence"],
    queryFn: () => api<EvidenceProfile>("profile/evidence"),
    enabled: !!career.data,
  });
  const mutation = useMutation({
    mutationFn: ({ path, command }: { path: string; command: object }) =>
      api(path, command),
    onSuccess: async () => {
      await cache.invalidateQueries();
    },
    onError: () => {
      setBlocked(true);
    },
  });
  const state = career.error ? undefined : career.data;
  const snapshot = state?.snapshot;
  function sourceText(identifier: string, field: string): string {
    const value = snapshot?.profile.evidence.find(
      (source) => source.id === identifier,
    )?.[field];
    return typeof value === "string" ? value : "Unavailable";
  }
  const busy = mutation.isPending || blocked || career.isFetching;
  function send(path: string, command: object) {
    mutation.mutate({ path, command });
  }
  async function reload() {
    mutation.reset();
    await cache.invalidateQueries();
    setBlocked(cache.getQueryState(["career"])?.status !== "success");
  }
  const now = () => new Date().toISOString();
  function syntheticDemo() {
    const command: components["schemas"]["InitializeCareer"] = {
      schema_version: "actual-api-v1",
      expected_generation: 0,
      profile: {
        schema_version: "actual-api-v1",
        id: id("profile"),
        name: "Synthetic Example Candidate",
      },
      job: {
        schema_version: "actual-api-v1",
        id: id("job"),
        opportunity_id: id("opportunity"),
        company: {
          schema_version: "actual-api-v1",
          id: id("company"),
          name: "Synthetic Example Studio",
          context: "Fabricated development company.",
        },
        title: "Synthetic Backend Engineer",
        text: "Synthetic posting: Python and FastAPI required. French B2 preferred. This is fabricated development data.",
        source_reference: "synthetic:manual-ui-demo",
        posted_at: now(),
      },
    };
    send("career", command);
  }
  const jobColumns: ColumnDef<Job>[] = [
    {
      accessorKey: "title",
      header: "Opportunity",
      cell: ({ row }) => (
        <button
          className="font-semibold text-teal-900 underline-offset-4 hover:underline"
          onClick={() => setFocusJob(row.original)}
        >
          {row.original.title}
        </button>
      ),
    },
    {
      accessorKey: "decision",
      header: "Decision",
      cell: ({ row }) => <Badge>{row.original.decision}</Badge>,
    },
    {
      accessorKey: "posted_at",
      header: "Posted",
      cell: ({ row }) => row.original.posted_at.slice(0, 10),
    },
    {
      id: "prepare",
      header: "Next step",
      cell: ({ row }) => (
        <Button
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() =>
            send("applications", {
              schema_version: "actual-api-v1",
              expected_generation: state!.generation,
              id: id("application"),
              job_id: row.original.id,
              occurred_at: now(),
            })
          }
        >
          Start preparing <ArrowUpRight size={14} />
        </Button>
      ),
    },
  ];
  const appColumns: ColumnDef<Application>[] = [
    {
      accessorKey: "job_id",
      header: "Opportunity",
      cell: ({ row }) =>
        snapshot?.jobs.find((job) => job.id === row.original.job_id)?.title ??
        row.original.job_id,
    },
    {
      accessorKey: "state",
      header: "Reported status",
      cell: ({ row }) => (
        <Badge>{row.original.state.replaceAll("_", " ")}</Badge>
      ),
    },
    {
      id: "history",
      header: "History",
      cell: ({ row }) => (
        <details>
          <summary>{row.original.history.length} observations</summary>
          {row.original.history.map((item, index) => (
            <p className="text-xs py-1" key={index}>
              {item.state} · {item.basis} · {item.occurred_at}
              {item.external_manual
                ? " · manually submitted outside ACTUAL"
                : ""}
            </p>
          ))}
        </details>
      ),
    },
    {
      id: "update",
      header: "Record next status",
      cell: ({ row }) => (
        <StatusForm
          busy={busy}
          onSubmit={(target, manual) =>
            send(`applications/${row.original.id}/status`, {
              schema_version: "actual-api-v1",
              expected_generation: state!.generation,
              state: target,
              occurred_at: now(),
              external_manual: manual,
            })
          }
        />
      ),
    },
  ];

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-r border-slate-200 bg-[#eaf0eb] p-6 lg:sticky lg:top-0 lg:h-screen flex flex-col">
        <div className="flex items-center gap-3 text-xl font-semibold tracking-tight">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-900 text-white">
            a.
          </span>{" "}
          ACTUAL
        </div>
        <p className="mt-3 text-xs text-slate-500">Work with evidence.</p>
        <nav
          aria-label="Main navigation"
          className="mt-9 flex flex-wrap gap-1 lg:flex-col"
        >
          {navigation.map(([name, Icon]) => (
            <button
              key={name}
              onClick={() => {
                setScreen(name);
                setFocusJob(null);
              }}
              aria-current={screen === name ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-left ${screen === name ? "bg-white shadow-sm font-semibold text-teal-950" : "text-slate-600 hover:bg-white/60"}`}
            >
              <Icon size={17} />
              {name}
            </button>
          ))}
        </nav>
        <div className="mt-auto pt-10 text-xs leading-5 text-slate-500">
          <ShieldCheck className="mb-2" size={18} />
          <strong>Synthetic workspace</strong>
          <br />
          Office development only.
          <br />
          Canonical acceptance pending.
        </div>
      </aside>
      <main className="px-5 py-8 md:px-10 lg:px-12 max-w-[1500px] w-full">
        <header className="mb-8 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[.2em] text-slate-500 mb-2">
              Career / {screen}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              {screen === "Overview" ? "Your career workspace" : screen}
            </h1>
          </div>
          <Button
            variant="outline"
            onClick={reload}
            disabled={career.isFetching || mutation.isPending}
          >
            <RefreshCw size={15} /> Reload
          </Button>
        </header>
        <p className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          Use fabricated jobs and profiles only. Source reviews are synthetic
          development checks. ACTUAL does not submit applications.
        </p>
        {mutation.error && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm"
          >
            {mutation.error.message} Reload before another command.
          </div>
        )}
        {career.isPending && (
          <Card>
            <p role="status">Loading the local workspace…</p>
          </Card>
        )}
        {career.error && (
          <Card>
            <h2 className="text-xl font-semibold mb-3">
              {career.error instanceof ApiFailure && career.error.status === 404
                ? "Begin with a synthetic example"
                : "Connect the local Career API"}
            </h2>
            <p className="text-slate-600 mb-5">{career.error.message}</p>
            {career.error instanceof ApiFailure &&
              career.error.status === 404 && (
                <Button onClick={syntheticDemo} disabled={busy}>
                  Create fabricated example
                </Button>
              )}
            <p className="text-xs text-slate-500 mt-4">
              Setup commands and the disposable database requirements are in the
              repository’s Phase 8 guide.
            </p>
          </Card>
        )}
        {snapshot && screen === "Overview" && (
          <>
            <div className="grid gap-4 md:grid-cols-3 mb-6">
              {[
                ["Opportunities", snapshot.jobs.length, "Source text retained"],
                [
                  "Applications",
                  snapshot.applications.length,
                  "Status is a user report",
                ],
                [
                  "Profile declarations",
                  snapshot.profile.claims.length,
                  "Claims need reviewed support",
                ],
              ].map(([label, count, note]) => (
                <Card key={label}>
                  <p className="text-sm text-slate-500">{label}</p>
                  <p className="text-4xl font-semibold my-4">{count}</p>
                  <p className="text-xs text-slate-500">{note}</p>
                </Card>
              ))}
            </div>
            <Card>
              <div className="flex justify-between items-center mb-5">
                <h2 className="text-lg font-semibold">Current opportunities</h2>
                <Button variant="ghost" onClick={() => setScreen("Jobs")}>
                  View jobs <ArrowUpRight size={16} />
                </Button>
              </div>
              <Table items={snapshot.jobs} columns={jobColumns} />
            </Card>
            <div className="grid gap-5 md:grid-cols-2 mt-6">
              <Card>
                <CheckCheck className="text-teal-700 mb-4" />
                <h2 className="font-semibold mb-2">Evidence comes first</h2>
                <p className="text-sm leading-6 text-slate-600">
                  Inspect declarations and sources separately. Conflicting
                  evidence stays visible; missing support stays uncertain.
                </p>
                <Button
                  className="mt-4"
                  variant="outline"
                  onClick={() => setScreen("Profile")}
                >
                  Inspect profile
                </Button>
              </Card>
              <Card>
                <FileText className="text-teal-700 mb-4" />
                <h2 className="font-semibold mb-2">
                  Prepare, review, then act
                </h2>
                <p className="text-sm leading-6 text-slate-600">
                  Track preparation and reported outcomes. Human content review
                  does not authorize an external submission.
                </p>
                <Button
                  className="mt-4"
                  variant="outline"
                  onClick={() => setScreen("Applications")}
                >
                  Open applications
                </Button>
              </Card>
            </div>
          </>
        )}
        {snapshot && screen === "Jobs" && (
          <div className="space-y-6">
            <Card>
              <Table items={snapshot.jobs} columns={jobColumns} />
            </Card>
            {focusJob && (
              <Card>
                <h2 className="text-xl font-semibold mb-4">{focusJob.title}</h2>
                <p className="whitespace-pre-wrap text-sm leading-7">
                  {focusJob.text}
                </p>
                <p className="text-xs text-slate-500 mt-5">
                  Source reference: {focusJob.source_reference} · revision{" "}
                  {focusJob.revision}
                </p>
              </Card>
            )}
            <JobForm
              busy={busy}
              submit={(job) =>
                send("jobs", {
                  schema_version: "actual-api-v1",
                  expected_generation: state!.generation,
                  job,
                })
              }
            />
          </div>
        )}
        {snapshot && (screen === "Profile" || screen === "Skills") && (
          <div className="space-y-6">
            <Card>
              <h2 className="text-xl font-semibold mb-4">
                {snapshot.profile.name}
              </h2>
              <p className="text-sm text-slate-500 mb-4">
                Declarations, eligible support and source review are separate.
                Experience categories are never added together.
              </p>
              {evidence.error && <p role="alert">{evidence.error.message}</p>}
              {evidence.data?.generation !== state!.generation ? (
                <p role="status">Refreshing the evidence view…</p>
              ) : (
                evidence.data.profile.rows
                  .filter((row) => screen !== "Skills" || row.kind === "skill")
                  .map((row) => (
                    <div
                      key={`${row.kind}:${row.subject}`}
                      className="border-t border-slate-200 py-5"
                    >
                      <div className="flex gap-4 items-center justify-between">
                        <h3 className="font-semibold">
                          {row.subject}{" "}
                          <span className="text-xs text-slate-500">
                            {row.unit}
                          </span>
                        </h3>
                        <Badge>{row.state}</Badge>
                      </div>
                      <p className="text-sm text-slate-600 mt-3">
                        Supported value:{" "}
                        {row.supported_value ?? "not established"} · Reviewed
                        source value:{" "}
                        {row.reviewed_source_value ?? "not established"}
                      </p>
                      {row.declaration_exceeds_support && (
                        <p className="text-sm text-amber-800 mt-2">
                          A declaration exceeds current reviewed source support.
                        </p>
                      )}
                      {row.declarations.map((declaration) => (
                        <div
                          className="flex flex-wrap justify-between gap-3 py-3 text-sm"
                          key={declaration.claim_ref.claim_id}
                        >
                          <span>
                            Declared {declaration.assertion.value} ·{" "}
                            {declaration.status}
                            <span className="block text-xs text-slate-500 mt-2">
                              {
                                snapshot.profile.claims.find(
                                  (claim) =>
                                    claim.id === declaration.claim_ref.claim_id,
                                )?.text
                              }
                            </span>
                          </span>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy}
                            onClick={() =>
                              send(
                                `profile/claims/${declaration.claim_ref.claim_id}/synthetic-review`,
                                {
                                  schema_version: "actual-api-v1",
                                  expected_generation: state!.generation,
                                  expected_revision:
                                    declaration.claim_ref.revision,
                                  expected_digest:
                                    declaration.claim_ref.content_digest,
                                },
                              )
                            }
                          >
                            Review exact synthetic claim
                          </Button>
                        </div>
                      ))}
                      <details
                        className="mt-3 text-sm"
                        open={
                          expandedSources[`${row.kind}:${row.subject}`] ?? false
                        }
                        onToggle={(event) => {
                          const open = event.currentTarget.open;
                          setExpandedSources((current) => ({
                            ...current,
                            [`${row.kind}:${row.subject}`]: open,
                          }));
                        }}
                      >
                        <summary>Evidence references</summary>
                        <pre className="mt-3">
                          {JSON.stringify(
                            {
                              eligible: row.eligible_evidence_refs,
                              reviewed: row.reviewed_source_refs,
                              unreviewed: row.unreviewed_evidence_refs,
                              contrary: row.contrary_evidence_refs,
                              contextual: row.contextual_evidence_refs,
                              withdrawn: row.withdrawn_evidence_refs,
                            },
                            null,
                            2,
                          )}
                        </pre>
                        {[
                          ...row.unreviewed_evidence_refs,
                          ...row.reviewed_source_refs,
                          ...row.contextual_evidence_refs,
                        ]
                          .filter(
                            (ref, index, all) =>
                              all.findIndex(
                                (other) =>
                                  other.evidence_id === ref.evidence_id,
                              ) === index,
                          )
                          .map((ref) => (
                            <div
                              key={ref.evidence_id}
                              className="flex flex-wrap gap-2 my-3"
                            >
                              <span className="text-xs break-all w-full">
                                {ref.evidence_id}
                              </span>
                              <p className="w-full whitespace-pre-wrap text-sm">
                                {sourceText(ref.evidence_id, "excerpt")}
                              </p>
                              <p className="w-full text-xs text-slate-500">
                                Source:{" "}
                                {sourceText(
                                  ref.evidence_id,
                                  "source_reference",
                                )}
                                {" · "}
                                {sourceText(ref.evidence_id, "source_kind")}
                                {" · revision "}
                                {ref.revision}
                              </p>
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={busy}
                                onClick={() =>
                                  send(
                                    `profile/evidence/${ref.evidence_id}/synthetic-review`,
                                    {
                                      schema_version: "actual-api-v1",
                                      expected_generation: state!.generation,
                                      expected_revision: ref.revision,
                                      expected_digest: ref.content_digest,
                                    },
                                  )
                                }
                              >
                                Review exact synthetic source
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={busy}
                                onClick={() =>
                                  send(
                                    `profile/evidence/${ref.evidence_id}/withdraw`,
                                    {
                                      schema_version: "actual-api-v1",
                                      expected_generation: state!.generation,
                                      expected_revision: ref.revision,
                                      expected_digest: ref.content_digest,
                                    },
                                  )
                                }
                              >
                                Withdraw source
                              </Button>
                            </div>
                          ))}
                      </details>
                    </div>
                  ))
              )}
              {evidence.data?.profile.rows.length === 0 && (
                <p className="text-sm text-slate-500">No recorded facts yet.</p>
              )}
              {evidence.data?.profile.experience.map((item) => (
                <div
                  key={item.evidence_ref.evidence_id}
                  className="border-t py-4"
                >
                  <Badge>{item.context.category}</Badge>
                  <p className="text-sm mt-2">
                    Source-authored {item.assertion.value} months ·{" "}
                    {item.context.started_at ?? "start unknown"} →{" "}
                    {item.context.ended_at ?? "end unknown"}. No duration is
                    inferred.
                  </p>
                </div>
              ))}
            </Card>
            <ClaimForm
              busy={busy}
              submit={(command) =>
                send("profile/claims", {
                  ...command,
                  schema_version: "actual-api-v1",
                  expected_generation: state!.generation,
                  id: id("claim"),
                })
              }
            />
            <EvidenceForm
              busy={busy}
              claims={snapshot.profile.claims}
              submit={(command) =>
                send("profile/evidence", {
                  ...command,
                  schema_version: "actual-api-v1",
                  expected_generation: state!.generation,
                  id: id("evidence"),
                  source_kind: "synthetic_fixture",
                  collected_at: now(),
                })
              }
            />
          </div>
        )}
        {snapshot && screen === "Applications" && (
          <Card>
            <h2 className="font-semibold mb-3">Application tracker</h2>
            <p className="text-sm text-slate-500 mb-5">
              Transitions are validated by the backend. Recording “applied” is a
              user report, never proof of delivery.
            </p>
            <Table items={snapshot.applications} columns={appColumns} />
          </Card>
        )}
        {screen === "Settings" && (
          <Card>
            <h2 className="text-xl font-semibold mb-5">
              Local development boundary
            </h2>
            <dl className="space-y-4 text-sm">
              <div>
                <dt className="text-slate-500">Mode</dt>
                <dd>
                  Synthetic development · no real accounts or personal documents
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Runtime</dt>
                <dd>
                  FastAPI → PostgreSQL; local Qwen through the accepted
                  ModelGateway
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">External actions</dt>
                <dd>Unavailable in this interface</dd>
              </div>
              <div>
                <dt className="text-slate-500">Acceptance</dt>
                <dd>
                  Office checks recorded; personal canonical validation pending
                </dd>
              </div>
            </dl>
          </Card>
        )}
        <footer className="mt-10 text-xs text-slate-400">
          ACTUAL · Synthetic career workspace · generation{" "}
          {state?.generation ?? "unavailable"}
        </footer>
      </main>
    </div>
  );
}

function JobForm({
  busy,
  submit,
}: {
  busy: boolean;
  submit: (job: components["schemas"]["ManualJob"]) => void;
}) {
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    submit({
      schema_version: "actual-api-v1",
      id: id("job"),
      opportunity_id: id("opportunity"),
      company: {
        schema_version: "actual-api-v1",
        id: id("company"),
        name: String(data.get("company")),
        context: "Fabricated UI development company",
      },
      title: String(data.get("title")),
      text: String(data.get("text")),
      source_reference: "synthetic:manual-ui-intake",
      posted_at: new Date().toISOString(),
    });
  }
  return (
    <Card>
      <h2 className="font-semibold mb-3">Add a fabricated opportunity</h2>
      <form onSubmit={save}>
        <div className="grid md:grid-cols-2 gap-4">
          <Field title="Synthetic job title">
            <input
              name="title"
              required
              maxLength={240}
              defaultValue="Synthetic Backend Engineer"
            />
          </Field>
          <Field title="Synthetic company">
            <input
              name="company"
              required
              maxLength={240}
              defaultValue="Synthetic Example Studio"
            />
          </Field>
        </div>
        <Field title="Fabricated posting text">
          <textarea
            name="text"
            required
            rows={4}
            maxLength={12000}
            defaultValue="Synthetic posting: Python required. All details are fabricated for development."
          />
        </Field>
        <Button disabled={busy}>Add synthetic job</Button>
      </form>
    </Card>
  );
}
function ClaimForm({
  busy,
  submit,
}: {
  busy: boolean;
  submit: (command: { assertion: Assertion; text: string }) => void;
}) {
  const [kind, setKind] = useState<Assertion["kind"]>("skill");
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    submit({
      assertion: {
        schema_version: "actual-core-v1",
        kind,
        subject:
          kind === "experience" ? "experience" : String(data.get("subject")),
        unit:
          kind === "skill"
            ? "skill_level"
            : kind === "language"
              ? "cefr_level"
              : "months",
        value: Number(data.get("value")),
      },
      text: String(data.get("text")),
    });
  }
  return (
    <Card>
      <h2 className="font-semibold">Add a synthetic declaration</h2>
      <form onSubmit={save}>
        <div className="grid md:grid-cols-3 gap-4">
          <Field title="Kind">
            <select
              value={kind}
              onChange={(event) =>
                setKind(event.target.value as Assertion["kind"])
              }
            >
              <option value="skill">Skill</option>
              <option value="language">Language</option>
              <option value="experience">Unscoped experience</option>
            </select>
          </Field>
          <Field title="Subject">
            <input
              name="subject"
              defaultValue="python"
              disabled={kind === "experience"}
              required
              pattern="[a-z][a-z0-9_]*"
            />
          </Field>
          <Field
            title={
              kind === "language"
                ? "CEFR level (0 unknown; 1 A1 to 6 C2)"
                : kind === "skill"
                  ? "Declared skill level (0–3)"
                  : "Source-authored months"
            }
          >
            <input
              name="value"
              type="number"
              min={0}
              max={kind === "skill" ? 3 : kind === "language" ? 6 : 600}
              required
              defaultValue={1}
            />
          </Field>
        </div>
        <Field title="Fabricated declaration text">
          <input
            name="text"
            defaultValue="Synthetic candidate declaration, not independently verified."
            maxLength={12000}
            required
          />
        </Field>
        <Button disabled={busy}>Record self-reported claim</Button>
      </form>
    </Card>
  );
}
function EvidenceForm({
  busy,
  claims,
  submit,
}: {
  busy: boolean;
  claims: components["schemas"]["Claim"][];
  submit: (command: {
    claim_id: string;
    assertion: Assertion;
    relation: "supports" | "contradicts";
    source_reference: string;
    excerpt: string;
  }) => void;
}) {
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const claim = claims.find((item) => item.id === data.get("claim"));
    if (claim)
      submit({
        claim_id: claim.id,
        assertion: { ...claim.assertion, value: Number(data.get("value")) },
        relation: data.get("relation") as "supports" | "contradicts",
        source_reference: "synthetic:manual-ui-evidence",
        excerpt: String(data.get("excerpt")),
      });
  }
  return (
    <Card>
      <h2 className="font-semibold">Attach a fabricated source</h2>
      <p className="text-sm text-slate-500 mt-2">
        Attachment remains unreviewed. Source and claim reviews are separate
        actions.
      </p>
      <form onSubmit={save}>
        <div className="grid md:grid-cols-3 gap-4">
          <Field title="Claim">
            <select name="claim" required>
              {claims.map((claim) => (
                <option key={claim.id} value={claim.id}>
                  {claim.assertion.subject} · {claim.assertion.unit} ·{" "}
                  {claim.id.slice(-6)}
                </option>
              ))}
            </select>
          </Field>
          <Field title="Relation">
            <select name="relation">
              <option value="supports">Supports</option>
              <option value="contradicts">Contradicts</option>
            </select>
          </Field>
          <Field title="Source-authored value">
            <input
              name="value"
              required
              type="number"
              min={0}
              max={600}
              defaultValue={1}
            />
          </Field>
        </div>
        <Field title="Fabricated source excerpt">
          <textarea
            name="excerpt"
            required
            maxLength={12000}
            defaultValue="Synthetic fixture source describes the structured assertion above."
          />
        </Field>
        <Button disabled={busy || !claims.length}>
          Attach unreviewed synthetic source
        </Button>
      </form>
    </Card>
  );
}
function StatusForm({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (state: Application["state"], manual: boolean) => void;
}) {
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit(
      data.get("state") as Application["state"],
      data.get("manual") === "on",
    );
  }
  return (
    <form onSubmit={save} className="min-w-48">
      <select name="state" aria-label="Next reported status">
        {[
          "preparing",
          "ready_for_review",
          "reviewed",
          "applied",
          "interview",
          "offer",
          "closed",
        ].map((state) => (
          <option key={state} value={state}>
            {state.replaceAll("_", " ")}
          </option>
        ))}
      </select>
      <label className="text-xs flex gap-2 items-center">
        <input name="manual" type="checkbox" className="w-auto" />
        Manually applied outside ACTUAL
      </label>
      <Button size="sm" variant="outline" disabled={busy}>
        Record status
      </Button>
    </form>
  );
}
