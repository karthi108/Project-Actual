import pytest
from pydantic import SecretStr, ValidationError

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.connectors import ToolError
from actual.workflows.teams import ConnectorReference, Member, Organization, Workspace, token_digest


def test_untrusted_authority_and_real_connector_fields_are_closed():
    with pytest.raises(ValidationError):
        Organization(id="synthetic_org", capabilities=("shell",))
    with pytest.raises(ValidationError):
        Member(principal=ActorId("actor_" + "1" * 32), role="root")
    with pytest.raises(ValidationError):
        ConnectorReference(
            id="mail",
            capability="fake_write",
            resource="synthetic_inbox",
            refresh_token="Fabricated",
        )
    with pytest.raises(ValidationError):
        ConnectorReference(id="mail", capability="fake_read", resource="synthetic_inbox")
    with pytest.raises(ValidationError):
        Workspace(id=WorkspaceId("workspace_" + "1" * 32), organization="synthetic_org", members=())
    with pytest.raises(ToolError, match="denied"):
        token_digest(SecretStr("Caller-supplied actor/admin assertion"))
