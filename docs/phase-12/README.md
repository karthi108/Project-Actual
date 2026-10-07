# Controlled connectors

IMPLEMENTED; canonical acceptance PENDING.

Problem: a registered tool still needs a typed provider boundary, scoped deterministic permission and safe failure semantics. The smallest slice is a fabricated read provider, closed input/output schemas and an operator-configured default-deny authorizer. Its only resource names are explicit synthetic tokens. Arbitrary URLs, files, accounts, secrets and network access are unavailable.

The existing IR catalog fixes capabilities, effects, permissions and idempotency metadata. Read execution rechecks owner/principal/capability/policy before the provider. Provider output is untrusted data and revalidated; extra authority fields fail. Errors expose only registered codes. Transient failures use the runtime's bounded retry waits; denial and malformed output route to failure immediately.

`WritePort` declares keyed dispatch and reconciliation, but no write implementation or runtime dispatch is enabled in this phase. The read dispatcher rejects writes even if configured permissions mention them. Exact durable approval and intent recovery precede fake-write activation in Phase 13.

Trade-off: one fabricated provider proves the boundary with no OAuth or real provider dependency. Real Gmail/Calendar/file/network adapters, credential handling and live provider semantics remain pending future integration. No model sees a connector handle or secret.
