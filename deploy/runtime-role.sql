-- Operator runs after explicit migrations, on an isolated synthetic database.
-- Assign its separate password interactively using psql \password actual_runtime.
CREATE ROLE actual_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO actual_runtime;
GRANT SELECT ON alembic_version TO actual_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON
  career_workspaces, object_identities, companies, profiles, jobs, claims,
  evidence, cvs, drafts, applications, requirements, claim_evidence_links,
  work_events, event_object_refs, event_evidence_refs
  TO actual_runtime;
GRANT SELECT, INSERT ON deletion_ledger TO actual_runtime;
GRANT SELECT ON actual_workflow_schema, actual_approval_schema,
  actual_activation_schema, actual_shadow_schema TO actual_runtime;
GRANT SELECT, INSERT ON actual_workflow_definitions, actual_workflow_audit,
  actual_workflow_dead_letters, actual_effect_audit, actual_activation_audit,
  actual_shadow_observations, actual_synthetic_provider_receipts TO actual_runtime;
GRANT SELECT, INSERT, UPDATE ON actual_workflow_runs, actual_effect_approvals,
  actual_effect_intents, actual_step_activation TO actual_runtime;
