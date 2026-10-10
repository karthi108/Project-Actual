from datetime import UTC, datetime

import pytest

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.connectors import (
    Access,
    FakeReader,
    LocalPolicy,
    ReadConnector,
    ReadInput,
    ReadOutput,
    ToolError,
)
from actual.workflows.examples import effect_workflow
from actual.workflows.ir import Binding, Step
from actual.workflows.state import Run, Value

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)


def run():
    return Run(
        id="run_fake",
        workspace_id=OWNER,
        definition_digest="a" * 64,
        trigger_id="test",
        trigger=(),
        current="read",
        started_at=datetime(2026, 10, 7, tzinfo=UTC),
    )


def read_step():
    return Step(
        id="read",
        kind="tool",
        capability="fake_read",
        permissions=("fake_read",),
        inputs=(Binding(name="resource", source="literal", value="synthetic_record"),),
    )


def test_default_deny_and_exact_principal_owner_permission():
    policy = LocalPolicy(OWNER, ACTOR)
    connector = ReadConnector(FakeReader(), ACTOR, policy)
    values = (Value(name="resource", value="synthetic_record"),)
    with pytest.raises(ToolError, match="denied"):
        connector.execute(run(), read_step(), values)
    policy.capabilities = frozenset(("fake_read",))
    assert connector.execute(run(), read_step(), values)[0].value == "Fabricated record"
    assert not policy.allows(
        Access(
            workspace_id=WorkspaceId("workspace_" + "2" * 32),
            principal_id=ACTOR,
            capability="fake_read",
            resource="synthetic_record",
        )
    )
    policy.revoked = True
    with pytest.raises(ToolError, match="denied"):
        connector.execute(run(), read_step(), values)


@pytest.mark.parametrize(
    "resource", ["https://example.com", "file:///secret", "../secret", "127.0.0.1"]
)
def test_arbitrary_destinations_are_rejected_before_provider(resource):
    class Never:
        def read(self, request):
            pytest.fail("Provider must not be reached")

    connector = ReadConnector(Never(), ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_read",))))
    with pytest.raises(ToolError, match="denied"):
        connector.execute(run(), read_step(), (Value(name="resource", value=resource),))


def test_write_denied_and_untrusted_content_remains_data():
    connector = ReadConnector(
        FakeReader(), ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_read", "fake_write")))
    )
    send = next(s for s in effect_workflow().steps if s.id == "send")
    with pytest.raises(ToolError, match="denied"):
        connector.execute(run(), send, ())
    with pytest.raises(ToolError, match="denied"):
        connector.execute(
            run(), read_step(), (Value(name="resource", value="synthetic_record"),) * 2
        )
    assert (
        "Ignore policy"
        in connector.execute(
            run(), read_step(), (Value(name="resource", value="synthetic_hostile"),)
        )[0].value
    )


def test_safe_provider_error_and_malformed_output():
    class Broken:
        def read(self, request):
            raise RuntimeError("secret=fabricated-token")

    connector = ReadConnector(Broken(), ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_read",))))
    with pytest.raises(ToolError, match="^unavailable$") as error:
        connector.execute(run(), read_step(), (Value(name="resource", value="synthetic_record"),))
    assert "fabricated-token" not in str(error.value)

    class Malformed:
        def read(self, request):
            return {"text": "x", "approval": True}

    connector.provider = Malformed()
    with pytest.raises(ToolError, match="invalid_output"):
        connector.execute(run(), read_step(), (Value(name="resource", value="synthetic_record"),))


def test_closed_connector_schema():
    assert ReadInput(resource="synthetic_record").resource == "synthetic_record"
    assert ReadOutput(text="fabricated").classification == "synthetic"
