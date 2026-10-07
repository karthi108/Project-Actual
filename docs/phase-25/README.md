# Phase 25 — Deployment preparation

Status: IMPLEMENTED private synthetic configuration, commands and instrumentation; Docker/Terraform/TLS/Collector/cloud runtime and hosted CI validation PENDING. This office laptop has no Docker or Terraform and deploys nothing. See [ADR 0013](../adr/0013-private-deployment-preparation.md).

## Contents and compatibility

`deploy/Dockerfile.api` uses the accepted Python 3.13.13 and uv 0.11.7 lock without changing `uv.lock`; `Dockerfile.web` uses accepted Node 24.19.0/pnpm 11.19.0 and the frontend lock. Version-tag image availability/digests, Linux wheel availability, non-root PostgreSQL 18.6 volume initialization and image execution must be checked on the personal environment. Official image catalogs were inspected; registry tag endpoints were unavailable during office review, so no digest is invented. [Python catalog](https://github.com/docker-library/python/blob/master/versions.json), [Node catalog](https://github.com/nodejs/docker-node/blob/main/versions.json)

The root Docker context is an allowlist of source/lock/build inputs. Evaluator storage, Git, private data, models, runtime databases, credentials and office tooling are excluded. API/web startup remains loopback and synthetic. Host networking requires supported Linux behavior; it is not a sandbox for generated code. No model server or model weights are added to Compose.

The optional Collector profile pins 0.162.0, has a loopback receiver and basic local diagnostics only. `ObservedRuntime` wraps an explicitly composed synthetic runtime; the Career API is not auto-instrumented. No SDK dependency, collector or telemetry service was installed. The existing frontend transitive `js-yaml` 4.3.2 parses YAML for syntax checks; this is not native platform validation. [Collector release](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.162.0)

CI uses SHA-pinned checkout v5.0.0, setup-python v6.0.0 and setup-node v4.4.0, read-only repository permissions and no deployment/publication. Its database password is explicitly fake and disposable. Python 3.13.13/3.14.4 have real PostgreSQL regression jobs; the frontend has frozen installation, unit/type/format/build checks. Hosted runner/artifact/image resolution is pending, with no configured remote. [Checkout pin](https://github.com/actions/checkout/commit/08c6903cd8c0fde910a37f88322edcfb5dd907a8), [Python pin](https://github.com/actions/setup-python/commit/e797f83bcb11b83ae66e0230d6156d7c80228e7c), [Node pin](https://github.com/actions/setup-node/commit/49933ea5288caeca8642d1e84afbd3f7d6820020)

## Personal-environment rehearsal

Use a dedicated synthetic Linux environment. Provision ignored `local-data/deployment` files: `postgres_password`, `migration_url` and `runtime_url`. Both URLs use `postgresql+psycopg` with `127.0.0.1:55432/actual_synthetic`; migration uses `actual_migrator`, runtime uses separately provisioned `actual_runtime`. Do not put values in command arguments, Git or terminal output. Ensure mount permissions permit only the appropriate trusted container/host user; actual Compose permissions require review. No secret is available to the frontend, telemetry collector or model.

```sh
docker compose -f deploy/compose.yaml config --quiet
docker compose -f deploy/compose.yaml build
docker compose -f deploy/compose.yaml up -d postgres
docker compose -f deploy/compose.yaml --profile operator run --rm migrate
```

Before API startup, run `deploy/runtime-role.sql` as the database operator, then assign the runtime role's separate password through psql's interactive `\password actual_runtime`. SQL grants append-only audit access and no DDL/admin privileges. Mount its URL only to the API. Run native role checks and inspect grants; do not substitute the migration credential for a failing runtime role.

```sh
docker compose -f deploy/compose.yaml up -d api web
docker compose -f deploy/compose.yaml exec api python -m actual.deployment check
curl --fail http://127.0.0.1:8765/health/live
curl --fail http://127.0.0.1:8765/health/ready
docker compose -f deploy/compose.yaml --profile telemetry run --rm collector validate --config=/etc/otelcol/config.yaml
```

Liveness is the existing process endpoint; readiness checks the accepted schema/current synthetic workspace without startup DDL. Workflow schemas are explicitly migrated and guarded; this API exposes no workflow/teams service. Initialize synthetic Career data through existing commands/UI only. Check ports/firewalls and container users/limits before any runtime claim. Shut down with `docker compose -f deploy/compose.yaml down`; preserve the volume. Volume deletion is a separate operator decision.

Validate `deploy/tls-probe.conf` with a selected supported Nginx/OpenSSL runtime, mounted operator certificates and hostname validation. It accepts TLS 1.3 on loopback port 8443 and exposes only `/health/tls`; it grants no API access. Certificate generation/trust/rotation and domain TLS are PENDING_PERSONAL_ENVIRONMENT. [Nginx TLS configuration](https://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_protocols)

For OVH preparation, supply reviewed ignored variables and credentials, then run `terraform -chdir=deploy/terraform fmt -check`, `init -backend=false`, and `validate`. Review the generated dependency lock/checksums before later use. Do not run `apply` from the office laptop. Resource enablement defaults false; there is no application ingress, automatic package install or deployment secret in cloud-init. No provider/cloud compatibility is claimed.

## Backup and recovery

Back up the **whole database**, including workflow, intent, approval, activation, audit and deletion records, using a restricted backup role and PostgreSQL 18 `pg_dump --format=custom`. Use a protected password file outside Git and an encrypted destination; never include secrets in process arguments. Verify archive integrity and independently retain deletion tombstones and newer dispatch/receipt evidence. [PostgreSQL dump/restore guidance](https://www.postgresql.org/docs/18/backup-dump.html)

Restore into a separately named isolated database with workers, connectors and telemetry disabled. Verify accepted migration head, provisional table shapes and manifests before enabling reads. Reconcile deletion tombstones before access. Compare the restored intent ledger against the provider and retained newer audit: an old backup can forget a successful effect. Never redispatch an uncertain or missing intent simply because the backup looks ready. Require reconciliation and a new reviewed recovery decision. Test restore round trips and crash/receipt recovery using synthetic data; physical/cloud recovery, encrypted off-device retention and measured RPO/RTO remain pending.

The office checks cover secret failures, payload-free spans, lost exporter behavior, export deadline and explicit migration/runtime-role permissions on real PostgreSQL. They do not prove container deployment, TLS trust, hosted CI, cloud recovery, provider interoperability or production readiness.
