# Synthetic Teach Mode

IMPLEMENTED semantic-session/privacy harness; canonical acceptance PENDING. Real device/browser capture and product UI integration remain pending.

`Teach` admits explicitly synthetic semantic observations only after an explicit start with a unique application allowlist and an acknowledged visible display. Pause/stop close intake; resume needs a visible state again. Losing the display blocks intake. The denylist wins over allowlist. Password/sensitive fields and sensitive classifications are dropped locally before event construction. The closed observation schema admits no raw screenshot, text, password or token field.

Events derive owner/actor/session from the trusted controller and preserve occurrence/recording time, source identity and typed business-object token. Exact duplicates are no-ops; changed content conflicts. Session size is bounded. One session records one observed example and never a complete inferred process. Transient events are available for review and explicit downstream analysis; stopped-session `delete` drops controller references. Starting a new session resets transient observations, so review/export the immutable event tuple first. There is no permanent automatic archive or secure memory-erasure claim.

`python scripts/teach_demo.py` shows active, paused, resumed and stopped console states around one fabricated event. It opens no screen, device, browser history or microphone. Tests exercise state, visibility, application rules, sensitive exclusions, deduplication and schema rejection.

Trade-off: a testable semantic/display port without office surveillance or capture dependencies. Synthetic/sensitivity labels cannot detect deliberately mislabeled private data. Native/browser extension, accessible persistent UI, retention/archive and real permission mechanisms require personal-environment integration and review. No hidden/background recording exists.
