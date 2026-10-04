# Privacy model v0.1

Status: proposed defaults for implementation; no stored personal database exists in Phase 0.

## Data boundary and flows

Phase 1 uses synthetic inputs only. Real profiles, CVs, pasted job descriptions, drafts and notes stay in a private local data root outside the source checkout when introduced. The local application, database and allowed model process are inside the processing boundary. The repository and development partner are separate boundaries: do not expose real materials through commits, tool output or development prompts merely because ACTUAL itself is local.

Local runtime must not silently call a remote model, analytics service or arbitrary URL. Dependency/model downloads may use the network without application records. For local Ollama inference, use an explicit local-model allowlist and disable cloud features; the official FAQ documents `OLLAMA_NO_CLOUD=1` (or the server configuration equivalent). Verify actual configuration/egress when Phase 5 begins. [Ollama FAQ](https://docs.ollama.com/faq)

Redaction cannot guarantee removal of all personal data. The runtime's privacy claim depends on verified destinations, minimized prompts, configuration and observed traffic, not the presence of a filtering function.

## Classification and minimization

| Class | Examples | Rule |
| --- | --- | --- |
| Synthetic/public | Explicitly fabricated CareerLab records | Versionable development fixtures, with synthetic marker |
| Personal | CV facts, job/application notes, user preferences | Owner-scoped local storage; exclude from Git/default logs |
| Sensitive | Contact details, private correspondence and supporting personal documents | Minimum necessary use; local access and explicit review |
| Secret | Tokens, passwords, private keys | Separate credential storage; reject from events/model contexts/logs |

Classification governs allowed flows, not merely a decorative label. Unknown real imported data is treated conservatively. Logs store identifiers, sizes, durations and error classes; no request bodies, full CVs, raw prompts/responses or credentials by default. No external telemetry exporter is enabled without a deliberate later decision.

## Proposed retention and deletion defaults

| Data | Default policy when introduced |
| --- | --- |
| Owner's jobs/profile/CV/drafts | Retain while actively wanted; owner export/delete available before real use |
| Superseded generated draft revisions | Purge after 30 days unless owner explicitly keeps them |
| Raw model request/response | Memory only, not persisted by default |
| Diagnostic logs | Local rotation, 7 days, metadata only |
| Semantic events/audit metadata | 90 days; minimize personal text and remove/link-break on scoped deletion |
| Optional local backups | 30 days, owner-controlled protected location outside repo; no automatic cloud backup |
| Future raw capture/audio | Not collected in v0.1; later separate visible-session policy, zero durable retention by default |

These are design defaults, not claims that a purge job exists. With Phase 3, implement policies for data actually stored before admitting real personal data. Short retention of early audit metadata is appropriate to a personal assistant with no external automation; later consequential execution requires a separately reviewed retention policy.

Deleting an object removes source content and derived drafts/assessments, invalidates evidence links/reviews and removes unnecessary personal identifiers from retained metadata. Keep only a minimal deletion record needed to prevent restoration; even opaque IDs/hashes can be linkable personal metadata. Append-oriented audit permits policy-governed purge/redaction with a deletion record, not indefinite retention of original content.

Backups expire on schedule; deletion is not immediately physical in an offline backup. Restores must apply the deletion ledger before serving restored data. The owner may purge backup sets immediately. Do not promise secure erasure from an SSD or from backups merely because a database row was deleted.

Use OS/account access controls and a protected local backup location. Disk encryption is a deployment prerequisite to verify with the owner before sensitive real data, not an implemented ACTUAL feature. There is no compliance certification, enterprise governance or protection from host administrators.

## Future capture boundary

Teach Mode must begin explicitly and display capture state, provide pause/stop, app allowlists/denylists, sensitive-field/password exclusion, review and deletion. Local filtering happens before any remote boundary. A demonstration and voice explanation are observations/human claims, never automatically company policy. No employee productivity ranking or hidden monitoring is permitted.
