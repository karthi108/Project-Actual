"""Frozen initial PostgreSQL schema; independent of mutable runtime metadata.

The explicit DDL and triggers must be reviewed when changing storage behavior.
Downgrade is destructive and is intended only for an explicitly disposable database.
"""

from alembic import op

revision = "0001_career_persistence"
down_revision = None
branch_labels = None
depends_on = None

UPGRADE_STATEMENTS = (
    """
    CREATE TABLE career_workspaces (
            workspace_id TEXT NOT NULL,
            classification TEXT NOT NULL,
            as_of TIMESTAMP WITH TIME ZONE NOT NULL,
            generation BIGINT NOT NULL,
            snapshot_digest TEXT NOT NULL,
            CONSTRAINT pk_career_workspaces PRIMARY KEY (workspace_id),
            CONSTRAINT ck_career_workspaces_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_career_workspaces_classification CHECK ((classification IN
    ('synthetic', 'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_career_workspaces_generation CHECK ((generation > 0) IS TRUE),
            CONSTRAINT ck_career_workspaces_digest CHECK ((snapshot_digest ~ '^[0-9a-f]{64}$')
    IS TRUE)
    )
    """,
    """
    CREATE TABLE deletion_ledger (
            workspace_id TEXT NOT NULL,
            deleted_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT pk_deletion_ledger PRIMARY KEY (workspace_id),
            CONSTRAINT ck_deletion_ledger_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE)
    )
    """,
    """
    CREATE TABLE object_identities (
            workspace_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            digest TEXT NOT NULL,
            CONSTRAINT pk_object_identities PRIMARY KEY (workspace_id, object_id),
            CONSTRAINT ck_object_identities_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_object_identities_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_object_identities_kind CHECK ((kind IN ('company', 'job', 'profile',
    'claim', 'evidence', 'cv', 'draft', 'application', 'requirement')) IS TRUE),
            CONSTRAINT ck_object_identities_id_kind CHECK ((object_id ~ ('^' || kind ||
    '_[0-9a-f]{32}$')) IS TRUE),
            CONSTRAINT ck_object_identities_revision CHECK ((revision BETWEEN 1 AND 2147483647)
    IS TRUE),
            CONSTRAINT ck_object_identities_classification CHECK ((classification IN
    ('synthetic', 'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_object_identities_digest CHECK ((digest ~ '^[0-9a-f]{64}$') IS TRUE),
            CONSTRAINT uq_object_identities_kind UNIQUE (workspace_id, object_id, kind),
            CONSTRAINT uq_object_identities_snapshot UNIQUE (workspace_id, object_id, revision,
    classification, digest)
    )
    """,
    """
    CREATE TABLE work_events (
            workspace_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_event_id TEXT,
            occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
            recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
            classification TEXT NOT NULL,
            activity TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            CONSTRAINT pk_work_events PRIMARY KEY (workspace_id, event_id),
            CONSTRAINT ck_work_events_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_work_events_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_work_events_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_work_events_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_work_events_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$')
    IS TRUE),
            CONSTRAINT ck_work_events_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_work_events_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1',
    'event_id', event_id, 'workspace_id', workspace_id, 'privacy_classification',
    classification)) IS TRUE),
            CONSTRAINT uq_work_events_source_identity UNIQUE (workspace_id, source,
    source_event_id),
            CONSTRAINT ck_work_events_event_id CHECK ((event_id ~ '^event_[0-9a-f]{32}$') IS
    TRUE),
            CONSTRAINT ck_work_events_source_event_id CHECK ((source_event_id IS NULL OR
    source_event_id ~ '^source_event_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_work_events_source CHECK ((source IN
    ('manual','careerlab','local_domain')) IS TRUE),
            CONSTRAINT ck_work_events_activity CHECK ((activity IN ('job_added',
    'requirements_reviewed', 'fit_assessment_recorded', 'cv_recommended', 'draft_reviewed',
    'application_status_recorded')) IS TRUE),
            CONSTRAINT ck_work_events_chronology CHECK ((recorded_at >= occurred_at) IS TRUE),
            CONSTRAINT ck_work_events_event_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('source', source, 'source_event_id', source_event_id, 'activity',
    activity) AND payload::jsonb ?& ARRAY['occurred_at','recorded_at'] AND
    (payload::jsonb->>'occurred_at')::timestamptz IS NOT DISTINCT FROM occurred_at AND
    (payload::jsonb->>'recorded_at')::timestamptz IS NOT DISTINCT FROM recorded_at) IS TRUE)
    )
    """,
    """
    CREATE TABLE companies (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            CONSTRAINT pk_companies PRIMARY KEY (workspace_id, id),
            CONSTRAINT uq_companies_position UNIQUE (workspace_id, position) DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_companies_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_companies_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_companies_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_companies_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_companies_id CHECK ((id ~ '^company_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_companies_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_companies_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS
    TRUE),
            CONSTRAINT ck_companies_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_companies_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_companies_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_companies_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_companies_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_companies_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE event_object_refs (
            workspace_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            kind TEXT NOT NULL,
            object_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            digest TEXT NOT NULL,
            classification TEXT NOT NULL,
            CONSTRAINT pk_event_object_refs PRIMARY KEY (workspace_id, event_id, position),
            CONSTRAINT ck_event_object_refs_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_event_object_refs_revision CHECK ((revision BETWEEN 1 AND 2147483647)
    IS TRUE),
            CONSTRAINT ck_event_object_refs_digest CHECK ((digest ~ '^[0-9a-f]{64}$') IS TRUE),
            CONSTRAINT ck_event_object_refs_classification CHECK ((classification IN
    ('synthetic', 'personal', 'sensitive')) IS TRUE),
            CONSTRAINT uq_event_object_refs_object UNIQUE (workspace_id, event_id, kind,
    object_id),
            CONSTRAINT fk_event_object_refs_event FOREIGN KEY(workspace_id, event_id) REFERENCES
    work_events (workspace_id, event_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_event_object_refs_historical_object FOREIGN KEY(workspace_id,
    object_id, kind) REFERENCES object_identities (workspace_id, object_id, kind) ON DELETE NO
    ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
    )
    """,
    """
    CREATE TABLE profiles (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            CONSTRAINT pk_profiles PRIMARY KEY (workspace_id, id),
            CONSTRAINT uq_profiles_one_per_workspace UNIQUE (workspace_id),
            CONSTRAINT uq_profiles_position UNIQUE (workspace_id, position) DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT ck_profiles_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_profiles_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_profiles_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_profiles_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_profiles_id CHECK ((id ~ '^profile_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_profiles_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_profiles_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS TRUE),
            CONSTRAINT ck_profiles_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_profiles_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_profiles_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_profiles_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_profiles_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_profiles_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE claims (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            status TEXT NOT NULL,
            CONSTRAINT pk_claims PRIMARY KEY (workspace_id, id),
            CONSTRAINT fk_claims_profile FOREIGN KEY(workspace_id, profile_id) REFERENCES
    profiles (workspace_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT uq_claims_position UNIQUE (workspace_id, profile_id, position) DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT uq_claims_profile_identity UNIQUE (workspace_id, profile_id, id),
            CONSTRAINT ck_claims_profile_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('profile_id', profile_id)) IS TRUE),
            CONSTRAINT uq_claims_source_snapshot UNIQUE (workspace_id, profile_id, id, revision,
    payload_digest),
            CONSTRAINT ck_claims_status CHECK ((status IN ('self_reported', 'candidate_support',
    'reviewed_supported', 'contradicted', 'withdrawn')) IS TRUE),
            CONSTRAINT ck_claims_status_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('status', status)) IS TRUE),
            CONSTRAINT ck_claims_workspace_id CHECK ((workspace_id ~ '^workspace_[0-9a-f]{32}$')
    IS TRUE),
            CONSTRAINT fk_claims_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_claims_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_claims_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_claims_id CHECK ((id ~ '^claim_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_claims_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_claims_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS TRUE),
            CONSTRAINT ck_claims_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_claims_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_claims_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_claims_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_claims_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_claims_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE cvs (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            CONSTRAINT pk_cvs PRIMARY KEY (workspace_id, id),
            CONSTRAINT fk_cvs_profile FOREIGN KEY(workspace_id, profile_id) REFERENCES profiles
    (workspace_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT uq_cvs_position UNIQUE (workspace_id, profile_id, position) DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT uq_cvs_profile_identity UNIQUE (workspace_id, profile_id, id),
            CONSTRAINT ck_cvs_profile_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('profile_id', profile_id)) IS TRUE),
            CONSTRAINT ck_cvs_workspace_id CHECK ((workspace_id ~ '^workspace_[0-9a-f]{32}$') IS
    TRUE),
            CONSTRAINT fk_cvs_workspace FOREIGN KEY(workspace_id) REFERENCES career_workspaces
    (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_cvs_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_cvs_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_cvs_id CHECK ((id ~ '^cv_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_cvs_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_cvs_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS TRUE),
            CONSTRAINT ck_cvs_classification CHECK ((classification IN ('synthetic', 'personal',
    'sensitive')) IS TRUE),
            CONSTRAINT ck_cvs_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND 2000000)
    IS TRUE),
            CONSTRAINT ck_cvs_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_cvs_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_cvs_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) = 'object'
    AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id', id,
    'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_cvs_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE drafts (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            CONSTRAINT pk_drafts PRIMARY KEY (workspace_id, id),
            CONSTRAINT fk_drafts_profile FOREIGN KEY(workspace_id, profile_id) REFERENCES
    profiles (workspace_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT uq_drafts_position UNIQUE (workspace_id, profile_id, position) DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT uq_drafts_profile_identity UNIQUE (workspace_id, profile_id, id),
            CONSTRAINT ck_drafts_profile_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('profile_id', profile_id)) IS TRUE),
            CONSTRAINT ck_drafts_workspace_id CHECK ((workspace_id ~ '^workspace_[0-9a-f]{32}$')
    IS TRUE),
            CONSTRAINT fk_drafts_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_drafts_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_drafts_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_drafts_id CHECK ((id ~ '^draft_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_drafts_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_drafts_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS TRUE),
            CONSTRAINT ck_drafts_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_drafts_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_drafts_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_drafts_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_drafts_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_drafts_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE evidence (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            collected_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT pk_evidence PRIMARY KEY (workspace_id, id),
            CONSTRAINT fk_evidence_profile FOREIGN KEY(workspace_id, profile_id) REFERENCES
    profiles (workspace_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT uq_evidence_position UNIQUE (workspace_id, profile_id, position)
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT uq_evidence_profile_identity UNIQUE (workspace_id, profile_id, id),
            CONSTRAINT ck_evidence_profile_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('profile_id', profile_id)) IS TRUE),
            CONSTRAINT uq_evidence_source_snapshot UNIQUE (workspace_id, profile_id, id,
    revision, payload_digest),
            CONSTRAINT ck_evidence_collected_metadata CHECK ((payload::jsonb ? 'collected_at'
    AND (payload::jsonb->>'collected_at')::timestamptz IS NOT DISTINCT FROM collected_at) IS
    TRUE),
            CONSTRAINT ck_evidence_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_evidence_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_evidence_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_evidence_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_evidence_id CHECK ((id ~ '^evidence_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_evidence_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_evidence_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS TRUE),
            CONSTRAINT ck_evidence_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_evidence_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_evidence_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_evidence_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_evidence_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_evidence_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE jobs (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            company_id TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            posted_at TIMESTAMP WITH TIME ZONE NOT NULL,
            CONSTRAINT pk_jobs PRIMARY KEY (workspace_id, id),
            CONSTRAINT uq_jobs_position UNIQUE (workspace_id, position) DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT uq_jobs_opportunity UNIQUE (workspace_id, id, opportunity_id),
            CONSTRAINT uq_jobs_source_revision UNIQUE (workspace_id, id, revision,
    payload_digest),
            CONSTRAINT fk_jobs_company FOREIGN KEY(workspace_id, company_id) REFERENCES
    companies (workspace_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT ck_jobs_opportunity_id CHECK ((opportunity_id ~
    '^opportunity_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_jobs_source_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('company_id', company_id, 'opportunity_id', opportunity_id) AND
    (payload::jsonb->>'posted_at')::timestamptz IS NOT DISTINCT FROM posted_at AND
    payload::jsonb ? 'posted_at') IS TRUE),
            CONSTRAINT ck_jobs_workspace_id CHECK ((workspace_id ~ '^workspace_[0-9a-f]{32}$')
    IS TRUE),
            CONSTRAINT fk_jobs_workspace FOREIGN KEY(workspace_id) REFERENCES career_workspaces
    (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_jobs_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_jobs_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_jobs_id CHECK ((id ~ '^job_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_jobs_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_jobs_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS TRUE),
            CONSTRAINT ck_jobs_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_jobs_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND 2000000)
    IS TRUE),
            CONSTRAINT ck_jobs_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_jobs_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_jobs_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) = 'object'
    AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id', id,
    'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_jobs_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE applications (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            state TEXT NOT NULL,
            CONSTRAINT pk_applications PRIMARY KEY (workspace_id, id),
            CONSTRAINT fk_applications_profile FOREIGN KEY(workspace_id, profile_id) REFERENCES
    profiles (workspace_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED,
            CONSTRAINT uq_applications_position UNIQUE (workspace_id, profile_id, position)
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT uq_applications_profile_identity UNIQUE (workspace_id, profile_id, id),
            CONSTRAINT ck_applications_profile_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('profile_id', profile_id)) IS TRUE),
            CONSTRAINT uq_applications_intent UNIQUE (workspace_id, profile_id, opportunity_id),
            CONSTRAINT fk_applications_job FOREIGN KEY(workspace_id, job_id, opportunity_id)
    REFERENCES jobs (workspace_id, id, opportunity_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT ck_applications_state CHECK ((state IN ('preparing', 'ready_for_review',
    'reviewed', 'applied', 'interview', 'offer', 'closed')) IS TRUE),
            CONSTRAINT ck_applications_application_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('job_id', job_id, 'state', state)) IS TRUE),
            CONSTRAINT ck_applications_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_applications_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_applications_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_applications_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_applications_id CHECK ((id ~ '^application_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_applications_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_applications_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS
    TRUE),
            CONSTRAINT ck_applications_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_applications_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_applications_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$')
    IS TRUE),
            CONSTRAINT ck_applications_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_applications_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_applications_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE TABLE claim_evidence_links (
            workspace_id TEXT NOT NULL,
            claim_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            evidence_id TEXT NOT NULL,
            evidence_revision INTEGER NOT NULL,
            evidence_digest TEXT NOT NULL,
            CONSTRAINT pk_claim_evidence_links PRIMARY KEY (workspace_id, claim_id, position),
            CONSTRAINT ck_claim_evidence_links_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT uq_claim_evidence_links_source UNIQUE (workspace_id, claim_id,
    evidence_id),
            CONSTRAINT fk_claim_evidence_links_claim FOREIGN KEY(workspace_id, profile_id,
    claim_id) REFERENCES claims (workspace_id, profile_id, id) ON DELETE NO ACTION ON UPDATE NO
    ACTION DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_claim_evidence_links_evidence_snapshot FOREIGN KEY(workspace_id,
    profile_id, evidence_id, evidence_revision, evidence_digest) REFERENCES evidence
    (workspace_id, profile_id, id, revision, payload_digest) ON DELETE NO ACTION ON UPDATE NO
    ACTION DEFERRABLE INITIALLY DEFERRED
    )
    """,
    """
    CREATE TABLE cv_claim_links (
            workspace_id TEXT NOT NULL,
            cv_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            claim_id TEXT NOT NULL,
            claim_revision INTEGER NOT NULL,
            claim_digest TEXT NOT NULL,
            CONSTRAINT pk_cv_claim_links PRIMARY KEY (workspace_id, cv_id, position),
            CONSTRAINT ck_cv_claim_links_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT uq_cv_claim_links_source UNIQUE (workspace_id, cv_id, claim_id),
            CONSTRAINT fk_cv_claim_links_owner FOREIGN KEY(workspace_id, profile_id, cv_id)
    REFERENCES cvs (workspace_id, profile_id, id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_cv_claim_links_claim_snapshot FOREIGN KEY(workspace_id, profile_id,
    claim_id, claim_revision, claim_digest) REFERENCES claims (workspace_id, profile_id, id,
    revision, payload_digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED
    )
    """,
    """
    CREATE TABLE draft_claim_links (
            workspace_id TEXT NOT NULL,
            draft_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            claim_id TEXT NOT NULL,
            claim_revision INTEGER NOT NULL,
            claim_digest TEXT NOT NULL,
            assertion_position INTEGER NOT NULL,
            CONSTRAINT pk_draft_claim_links PRIMARY KEY (workspace_id, draft_id,
    assertion_position, position),
            CONSTRAINT ck_draft_claim_links_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_draft_claim_links_assertion_position CHECK ((assertion_position >= 0)
    IS TRUE),
            CONSTRAINT uq_draft_claim_links_source UNIQUE (workspace_id, draft_id,
    assertion_position, claim_id),
            CONSTRAINT fk_draft_claim_links_owner FOREIGN KEY(workspace_id, profile_id,
    draft_id) REFERENCES drafts (workspace_id, profile_id, id) ON DELETE NO ACTION ON UPDATE NO
    ACTION DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_draft_claim_links_claim_snapshot FOREIGN KEY(workspace_id, profile_id,
    claim_id, claim_revision, claim_digest) REFERENCES claims (workspace_id, profile_id, id,
    revision, payload_digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY
    DEFERRED
    )
    """,
    """
    CREATE TABLE event_evidence_refs (
            workspace_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            profile_id TEXT NOT NULL,
            evidence_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            digest TEXT NOT NULL,
            classification TEXT NOT NULL,
            CONSTRAINT pk_event_evidence_refs PRIMARY KEY (workspace_id, event_id, position),
            CONSTRAINT ck_event_evidence_refs_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_event_evidence_refs_revision CHECK ((revision BETWEEN 1 AND
    2147483647) IS TRUE),
            CONSTRAINT ck_event_evidence_refs_digest CHECK ((digest ~ '^[0-9a-f]{64}$') IS
    TRUE),
            CONSTRAINT ck_event_evidence_refs_classification CHECK ((classification IN
    ('synthetic', 'personal', 'sensitive')) IS TRUE),
            CONSTRAINT uq_event_evidence_refs_evidence UNIQUE (workspace_id, event_id,
    profile_id, evidence_id),
            CONSTRAINT fk_event_evidence_refs_event FOREIGN KEY(workspace_id, event_id)
    REFERENCES work_events (workspace_id, event_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_event_evidence_refs_historical_evidence FOREIGN KEY(workspace_id,
    profile_id, evidence_id) REFERENCES evidence (workspace_id, profile_id, id) ON DELETE NO
    ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
    )
    """,
    """
    CREATE TABLE requirements (
            workspace_id TEXT NOT NULL,
            id TEXT NOT NULL,
            position INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            classification TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            job_id TEXT NOT NULL,
            job_revision INTEGER NOT NULL,
            job_digest TEXT NOT NULL,
            opportunity_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            CONSTRAINT pk_requirements PRIMARY KEY (workspace_id, id),
            CONSTRAINT uq_requirements_position UNIQUE (workspace_id, position) DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT uq_requirements_subject UNIQUE (workspace_id, opportunity_id, subject),
            CONSTRAINT fk_requirements_job FOREIGN KEY(workspace_id, job_id, opportunity_id)
    REFERENCES jobs (workspace_id, id, opportunity_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_requirements_job_revision FOREIGN KEY(workspace_id, job_id,
    job_revision, job_digest) REFERENCES jobs (workspace_id, id, revision, payload_digest) ON
    DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT ck_requirements_source_metadata CHECK ((payload::jsonb @>
    jsonb_build_object('job_id', job_id, 'job_revision', job_revision, 'job_digest', job_digest)
    AND payload::jsonb->'assertion' @> jsonb_build_object('subject', subject)) IS TRUE),
            CONSTRAINT ck_requirements_workspace_id CHECK ((workspace_id ~
    '^workspace_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT fk_requirements_workspace FOREIGN KEY(workspace_id) REFERENCES
    career_workspaces (workspace_id) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT fk_requirements_identity FOREIGN KEY(workspace_id, id) REFERENCES
    object_identities (workspace_id, object_id) ON DELETE NO ACTION ON UPDATE NO ACTION
    DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_requirements_identity_snapshot FOREIGN KEY(workspace_id, id, revision,
    classification, payload_digest) REFERENCES object_identities (workspace_id, object_id,
    revision, classification, digest) ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE
    INITIALLY DEFERRED,
            CONSTRAINT ck_requirements_id CHECK ((id ~ '^requirement_[0-9a-f]{32}$') IS TRUE),
            CONSTRAINT ck_requirements_position CHECK ((position >= 0) IS TRUE),
            CONSTRAINT ck_requirements_revision CHECK ((revision BETWEEN 1 AND 2147483647) IS
    TRUE),
            CONSTRAINT ck_requirements_classification CHECK ((classification IN ('synthetic',
    'personal', 'sensitive')) IS TRUE),
            CONSTRAINT ck_requirements_payload_size CHECK ((octet_length(payload) BETWEEN 1 AND
    2000000) IS TRUE),
            CONSTRAINT ck_requirements_payload_digest CHECK ((payload_digest ~ '^[0-9a-f]{64}$')
    IS TRUE),
            CONSTRAINT ck_requirements_payload_hash CHECK ((payload_digest =
    encode(sha256(convert_to(payload, 'UTF8')), 'hex')) IS TRUE),
            CONSTRAINT ck_requirements_payload_metadata CHECK ((jsonb_typeof(payload::jsonb) =
    'object' AND payload::jsonb @> jsonb_build_object('schema_version', 'actual-core-v1', 'id',
    id, 'workspace_id', workspace_id, 'classification', classification)) IS TRUE),
            CONSTRAINT ck_requirements_payload_revision CHECK ((payload::jsonb @>
    jsonb_build_object('revision', revision)) IS TRUE)
    )
    """,
    """
    CREATE FUNCTION actual_guard_record_update() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    DECLARE
        previous_payload jsonb := OLD.payload::jsonb;
        next_payload jsonb := NEW.payload::jsonb;
        provenance_keys text[];
        item text;
        previous_history jsonb;
        next_history jsonb;
        ordinal integer;
    BEGIN
        IF NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
           OR NEW.id IS DISTINCT FROM OLD.id THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Stored object identity is immutable';
        END IF;
        IF NEW.payload IS DISTINCT FROM OLD.payload THEN
            IF NEW.revision <> OLD.revision + 1 THEN
                RAISE EXCEPTION USING ERRCODE = '23514',
                    MESSAGE = 'Changed payload requires exactly the next revision';
            END IF;
        ELSIF NEW.revision IS DISTINCT FROM OLD.revision THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Unchanged payload cannot advance revision';
        END IF;
        IF (next_payload -> 'profile_id') IS DISTINCT FROM
           (previous_payload -> 'profile_id') THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Stored profile ownership is immutable';
        END IF;
        provenance_keys := CASE TG_TABLE_NAME
            WHEN 'evidence' THEN ARRAY[
                'source_kind', 'source_reference', 'source_actor_id', 'collected_at'
            ]
            WHEN 'claims' THEN ARRAY['origin', 'asserted_by', 'asserted_at']
            WHEN 'jobs' THEN ARRAY[
                'source_reference', 'company_id', 'opportunity_id', 'posted_at'
            ]
            WHEN 'requirements' THEN ARRAY['origin', 'job_id']
            WHEN 'applications' THEN ARRAY['job_id']
            ELSE ARRAY[]::text[]
        END;
        FOREACH item IN ARRAY provenance_keys LOOP
            IF (next_payload -> item) IS DISTINCT FROM (previous_payload -> item) THEN
                RAISE EXCEPTION USING ERRCODE = '23514',
                    MESSAGE = 'Stored source provenance is immutable';
            END IF;
        END LOOP;
        IF TG_TABLE_NAME = 'applications' THEN
            previous_history := previous_payload -> 'history';
            next_history := next_payload -> 'history';
            IF jsonb_typeof(previous_history) IS DISTINCT FROM 'array'
               OR jsonb_typeof(next_history) IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION USING ERRCODE = '23514',
                    MESSAGE = 'Stored application history must be an array';
            END IF;
            IF jsonb_array_length(previous_history) < 1
               OR jsonb_array_length(next_history) < jsonb_array_length(previous_history) THEN
                RAISE EXCEPTION USING ERRCODE = '23514',
                    MESSAGE = 'Application history cannot be shortened';
            END IF;
            FOR ordinal IN 0..jsonb_array_length(previous_history) - 1 LOOP
                IF (previous_history -> ordinal) IS DISTINCT FROM (next_history -> ordinal) THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Application history cannot be rewritten';
                END IF;
            END LOOP;
        END IF;
        RETURN NEW;
    END
    $actual$
    """,
    """
    CREATE FUNCTION actual_guard_identity_update() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    BEGIN
        IF NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
           OR NEW.object_id IS DISTINCT FROM OLD.object_id
           OR NEW.kind IS DISTINCT FROM OLD.kind THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Stored object identity and kind are immutable';
        END IF;
        IF NEW.digest IS DISTINCT FROM OLD.digest
           OR NEW.classification IS DISTINCT FROM OLD.classification THEN
            IF NEW.revision <> OLD.revision + 1 THEN
                RAISE EXCEPTION USING ERRCODE = '23514',
                    MESSAGE = 'Changed identity snapshot requires next revision';
            END IF;
        ELSIF NEW.revision IS DISTINCT FROM OLD.revision THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Unchanged identity snapshot cannot advance revision';
        END IF;
        RETURN NEW;
    END
    $actual$
    """,
    """
    CREATE FUNCTION actual_guard_event_update() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    BEGIN
        RAISE EXCEPTION USING ERRCODE = '23514',
            MESSAGE = 'Historical events and references cannot be updated';
    END
    $actual$
    """,
    """
    CREATE FUNCTION actual_guard_workspace_write() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    DECLARE
        deleted boolean;
    BEGIN
        IF TG_OP = 'UPDATE' AND NEW.workspace_id IS DISTINCT FROM OLD.workspace_id THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Workspace identity is immutable';
        END IF;
        EXECUTE pg_catalog.format(
            'SELECT EXISTS (SELECT 1 FROM %I.deletion_ledger WHERE workspace_id=$1)',
            TG_TABLE_SCHEMA
        ) INTO deleted USING NEW.workspace_id;
        IF deleted THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Deleted workspace cannot be recreated';
        END IF;
        RETURN NEW;
    END
    $actual$
    """,
    """
    CREATE FUNCTION actual_guard_ledger_mutation() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    BEGIN
        RAISE EXCEPTION USING ERRCODE = '23514',
            MESSAGE = 'Deletion ledger entries are immutable';
    END
    $actual$
    """,
    """
    CREATE TRIGGER tr_companies_record_update
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_profiles_record_update
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_jobs_record_update
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_evidence_record_update
    BEFORE UPDATE ON evidence
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_claims_record_update
    BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_cvs_record_update
    BEFORE UPDATE ON cvs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_drafts_record_update
    BEFORE UPDATE ON drafts
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_applications_record_update
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_requirements_record_update
    BEFORE UPDATE ON requirements
    FOR EACH ROW EXECUTE FUNCTION actual_guard_record_update()
    """,
    """
    CREATE TRIGGER tr_object_identities_update
    BEFORE UPDATE ON object_identities
    FOR EACH ROW EXECUTE FUNCTION actual_guard_identity_update()
    """,
    """
    CREATE TRIGGER tr_work_events_immutable
    BEFORE UPDATE ON work_events
    FOR EACH ROW EXECUTE FUNCTION actual_guard_event_update()
    """,
    """
    CREATE TRIGGER tr_event_object_refs_immutable
    BEFORE UPDATE ON event_object_refs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_event_update()
    """,
    """
    CREATE TRIGGER tr_event_evidence_refs_immutable
    BEFORE UPDATE ON event_evidence_refs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_event_update()
    """,
    """
    CREATE TRIGGER tr_career_workspaces_guard
    BEFORE INSERT OR UPDATE ON career_workspaces
    FOR EACH ROW EXECUTE FUNCTION actual_guard_workspace_write()
    """,
    """
    CREATE TRIGGER tr_deletion_ledger_immutable
    BEFORE UPDATE OR DELETE ON deletion_ledger
    FOR EACH ROW EXECUTE FUNCTION actual_guard_ledger_mutation()
    """,
    """
    CREATE FUNCTION actual_guard_protected_delete() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    DECLARE
        deleted boolean;
    BEGIN
        EXECUTE pg_catalog.format(
            'SELECT EXISTS (SELECT 1 FROM %I.deletion_ledger WHERE workspace_id=$1)',
            TG_TABLE_SCHEMA
        ) INTO deleted USING OLD.workspace_id;
        IF deleted IS NOT TRUE THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Current records require an atomic workspace deletion';
        END IF;
        RETURN OLD;
    END
    $actual$
    """,
    """
    CREATE FUNCTION actual_guard_event_delete() RETURNS trigger
    LANGUAGE plpgsql AS $actual$
    DECLARE
        deleted boolean;
        observed_at timestamptz;
    BEGIN
        EXECUTE pg_catalog.format(
            'SELECT EXISTS (SELECT 1 FROM %I.deletion_ledger WHERE workspace_id=$1)',
            TG_TABLE_SCHEMA
        ) INTO deleted USING OLD.workspace_id;
        IF deleted THEN
            RETURN OLD;
        END IF;
        IF TG_TABLE_NAME = 'work_events' THEN
            observed_at := OLD.recorded_at;
        ELSE
            EXECUTE pg_catalog.format(
                'SELECT recorded_at FROM %I.work_events '
                'WHERE workspace_id=$1 AND event_id=$2',
                TG_TABLE_SCHEMA
            ) INTO observed_at USING OLD.workspace_id, OLD.event_id;
        END IF;
        IF observed_at IS NULL
           OR observed_at >= pg_catalog.clock_timestamp() - interval '90 days' THEN
            RAISE EXCEPTION USING ERRCODE = '23514',
                MESSAGE = 'Historical event retention has not expired';
        END IF;
        RETURN OLD;
    END
    $actual$
    """,
    """
    CREATE TRIGGER tr_companies_protected_delete
    BEFORE DELETE ON companies
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_jobs_protected_delete
    BEFORE DELETE ON jobs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_profiles_protected_delete
    BEFORE DELETE ON profiles
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_evidence_protected_delete
    BEFORE DELETE ON evidence
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_claims_protected_delete
    BEFORE DELETE ON claims
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_cvs_protected_delete
    BEFORE DELETE ON cvs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_drafts_protected_delete
    BEFORE DELETE ON drafts
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_applications_protected_delete
    BEFORE DELETE ON applications
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_requirements_protected_delete
    BEFORE DELETE ON requirements
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_object_identities_protected_delete
    BEFORE DELETE ON object_identities
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_career_workspaces_protected_delete
    BEFORE DELETE ON career_workspaces
    FOR EACH ROW EXECUTE FUNCTION actual_guard_protected_delete()
    """,
    """
    CREATE TRIGGER tr_work_events_retention_delete
    BEFORE DELETE ON work_events
    FOR EACH ROW EXECUTE FUNCTION actual_guard_event_delete()
    """,
    """
    CREATE TRIGGER tr_event_object_refs_retention_delete
    BEFORE DELETE ON event_object_refs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_event_delete()
    """,
    """
    CREATE TRIGGER tr_event_evidence_refs_retention_delete
    BEFORE DELETE ON event_evidence_refs
    FOR EACH ROW EXECUTE FUNCTION actual_guard_event_delete()
    """,
)

DOWNGRADE_STATEMENTS = (
    """
    DROP TRIGGER tr_event_evidence_refs_retention_delete ON event_evidence_refs
    """,
    """
    DROP TRIGGER tr_event_object_refs_retention_delete ON event_object_refs
    """,
    """
    DROP TRIGGER tr_work_events_retention_delete ON work_events
    """,
    """
    DROP TRIGGER tr_career_workspaces_protected_delete ON career_workspaces
    """,
    """
    DROP TRIGGER tr_object_identities_protected_delete ON object_identities
    """,
    """
    DROP TRIGGER tr_requirements_protected_delete ON requirements
    """,
    """
    DROP TRIGGER tr_applications_protected_delete ON applications
    """,
    """
    DROP TRIGGER tr_drafts_protected_delete ON drafts
    """,
    """
    DROP TRIGGER tr_cvs_protected_delete ON cvs
    """,
    """
    DROP TRIGGER tr_claims_protected_delete ON claims
    """,
    """
    DROP TRIGGER tr_evidence_protected_delete ON evidence
    """,
    """
    DROP TRIGGER tr_profiles_protected_delete ON profiles
    """,
    """
    DROP TRIGGER tr_jobs_protected_delete ON jobs
    """,
    """
    DROP TRIGGER tr_companies_protected_delete ON companies
    """,
    """
    DROP TRIGGER tr_deletion_ledger_immutable ON deletion_ledger
    """,
    """
    DROP TRIGGER tr_career_workspaces_guard ON career_workspaces
    """,
    """
    DROP TRIGGER tr_event_evidence_refs_immutable ON event_evidence_refs
    """,
    """
    DROP TRIGGER tr_event_object_refs_immutable ON event_object_refs
    """,
    """
    DROP TRIGGER tr_work_events_immutable ON work_events
    """,
    """
    DROP TRIGGER tr_object_identities_update ON object_identities
    """,
    """
    DROP TRIGGER tr_requirements_record_update ON requirements
    """,
    """
    DROP TRIGGER tr_applications_record_update ON applications
    """,
    """
    DROP TRIGGER tr_drafts_record_update ON drafts
    """,
    """
    DROP TRIGGER tr_cvs_record_update ON cvs
    """,
    """
    DROP TRIGGER tr_claims_record_update ON claims
    """,
    """
    DROP TRIGGER tr_evidence_record_update ON evidence
    """,
    """
    DROP TRIGGER tr_jobs_record_update ON jobs
    """,
    """
    DROP TRIGGER tr_profiles_record_update ON profiles
    """,
    """
    DROP TRIGGER tr_companies_record_update ON companies
    """,
    """
    DROP FUNCTION actual_guard_event_delete()
    """,
    """
    DROP FUNCTION actual_guard_protected_delete()
    """,
    """
    DROP FUNCTION actual_guard_ledger_mutation()
    """,
    """
    DROP FUNCTION actual_guard_workspace_write()
    """,
    """
    DROP FUNCTION actual_guard_event_update()
    """,
    """
    DROP FUNCTION actual_guard_identity_update()
    """,
    """
    DROP FUNCTION actual_guard_record_update()
    """,
    """
    DROP TABLE requirements
    """,
    """
    DROP TABLE event_evidence_refs
    """,
    """
    DROP TABLE draft_claim_links
    """,
    """
    DROP TABLE cv_claim_links
    """,
    """
    DROP TABLE claim_evidence_links
    """,
    """
    DROP TABLE applications
    """,
    """
    DROP TABLE jobs
    """,
    """
    DROP TABLE evidence
    """,
    """
    DROP TABLE drafts
    """,
    """
    DROP TABLE cvs
    """,
    """
    DROP TABLE claims
    """,
    """
    DROP TABLE profiles
    """,
    """
    DROP TABLE event_object_refs
    """,
    """
    DROP TABLE companies
    """,
    """
    DROP TABLE work_events
    """,
    """
    DROP TABLE object_identities
    """,
    """
    DROP TABLE deletion_ledger
    """,
    """
    DROP TABLE career_workspaces
    """,
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
