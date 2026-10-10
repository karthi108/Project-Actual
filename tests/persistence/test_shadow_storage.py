from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from actual.core.primitives import WorkspaceId
from actual.workflows.storage import Conflict
from actual.worklab.fixtures import observations
from actual.worklab.shadow import ShadowStore, Transition, compare, migrate, records


def test_shadow_metadata_durable_owner_scoped_and_deduplicated(pg_engine):
    migrate(pg_engine)
    owner = WorkspaceId("workspace_" + "1" * 32)
    repo = ShadowStore(pg_engine, owner)
    case = observations()[0]
    result = compare(case, (Transition(step="start", outcome="success"),))
    now = datetime(2026, 10, 7, tzinfo=UTC)
    assert repo.record("observation_one", result, now) == result
    assert ShadowStore(pg_engine, owner).record("observation_one", result, now) == result
    with pytest.raises(Conflict):
        repo.record("observation_one", compare(case, ()), now)
    other = ShadowStore(pg_engine, WorkspaceId("workspace_" + "2" * 32))
    other.record("observation_one", compare(case, ()), now)
    with pg_engine.connect() as connection:
        rows = connection.execute(select(records.c.payload)).scalars().all()
    assert len(rows) == 2 and all("Fabricated" not in str(row) for row in rows)
    migrate(pg_engine)
