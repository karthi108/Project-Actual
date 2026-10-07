# Typed workflow IR

IMPLEMENTED; canonical acceptance PENDING. Graphs are synthetic, closed, immutable and bounded. No executor is introduced in this phase. Existing Career schemas and persistence are unchanged.

Problem: proposals need a representation that cannot hide executable code or weaken capability requirements. The simplest solution is a small registered capability catalog, typed scalar bindings and acyclic outcome-labelled graphs. Each capability pins schema, effects, permission requirements, idempotency and review metadata. These are requirements, never authority.

Validation rejects unknown fields/capabilities, duplicate IDs, cycles, unreachable nodes, missing outcome routes, type mismatches, unavailable output references and budget excess. Every path to a consequential step must pass successful policy and approval gates protecting that exact step. Denial paths cannot contribute those facts. Runtime authorization and approval are still required later.

Trade-offs: no arbitrary Python, shell, expressions, unbounded loops, real data or third-party capability registration. Acyclic graphs are sufficient for the first workflows; durable retries and waits arrive in Phase 11. AI is declarative only, with a model budget and review requirement; it has no authority or execution here.

Examples live in `actual.workflows.examples`; JSON Schema is `workflow-v1.schema.json`. Adversarial checks live in `tests/workflows/test_ir.py`. Office checks and pending canonical gates are recorded in the debt register.
