# Controlled synthetic activation

IMPLEMENTED; canonical acceptance PENDING. No personal-account activation is enabled.

`controlled(...)` is the application composition for fake connector execution. It combines separate permissions and owner/principal-scoped step activation with exact action approval. Both missing permissions and missing activation deny by default. Explicit operator migration is required; construction never creates tables. Deterministic local graph operations remain available, while integration capabilities require activation in this composition.

Each activation records a pinned workflow hash, exact step/capability, principal, disabled/shadow/enabled state, reviewed shadow-evidence digest, revision and audit. Changes use compare-and-swap. Workflow upgrades require new activation. Read execution and both write reservation/dispatch checks consult the same current combined authorizer. Disabling activation after approval prevents dispatch.

Shadow observations remain evidence, including disagreements; they never grant authority or automatically switch state. `ActivationStore.set` is an explicit trusted operator decision with exact reviewed evidence and current scoped permission. Enabling a fake write allows only execution behind the Phase-13 human action gate; it does not approve an action. AI/provider integration remains unavailable.

Trade-off: synthetic trusted local composition and fixed fake capabilities. Individual low-level ports remain useful for contract tests, but are not an authenticated product interface. No live account, blanket autonomy, end-user authentication or real personal activation is claimed. Canonical activation policy, human UI, revocation/concurrency and real integration review remain pending.
