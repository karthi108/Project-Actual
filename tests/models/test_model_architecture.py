"""Guard independent model contracts and the synthetic proposal-only integration."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "actual"


def imports(path: Path) -> set[str]:
    result = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = ("actual", *path.relative_to(ROOT).parent.parts)
                base = package[: len(package) - node.level + 1]
                if node.module is not None:
                    result.add(".".join((*base, node.module)))
                else:
                    result.update(".".join((*base, alias.name)) for alias in node.names)
            else:
                if node.module is not None:
                    result.add(node.module)
    return result


def forbidden_imports(path: Path, forbidden: set[str]) -> set[str]:
    return {
        module
        for module in imports(path)
        if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden)
    }


def test_domain_application_and_http_remain_free_of_provider_dependencies() -> None:
    forbidden = {"ollama", "httpx2", "actual.models.ollama", "actual.models.config"}
    for responsibility in ("core", "career", "profile", "application", "api", "persistence"):
        for path in (ROOT / responsibility).rglob("*.py"):
            assert not forbidden_imports(path, forbidden), path


def test_gateway_and_capability_do_not_import_provider_transport_or_evaluator_code() -> None:
    for path in [
        ROOT / "models" / "gateway.py",
        ROOT / "models" / "contracts.py",
        *(ROOT / "capabilities").rglob("*.py"),
    ]:
        assert not forbidden_imports(
            path,
            {
                "httpx2",
                "ollama",
                "actual.models.ollama",
                "actual.models.config",
                "actual.careerlab",
            },
        ), path
    for path in (ROOT / "models").rglob("*.py"):
        assert not forbidden_imports(path, {"actual.careerlab", "actual.persistence"}), path


def test_provider_transport_has_no_career_reasoning_database_or_effect_dependencies() -> None:
    assert not forbidden_imports(
        ROOT / "models" / "ollama.py",
        {
            "actual.career",
            "actual.profile",
            "actual.application",
            "actual.capabilities",
            "actual.persistence",
            "subprocess",
            "sqlalchemy",
            "fastapi",
        },
    )


def test_api_paths_and_migration_inventory_remain_accepted() -> None:
    # Phase5 is callable through its local probe, without exposing general inference
    # or adding storage just because a model exists.
    repository = ROOT.parents[1]
    assert sorted(path.name for path in (repository / "migrations" / "versions").glob("*.py")) == [
        "0001_career_persistence.py"
    ]
    for path in (ROOT / "api").rglob("*.py"):
        assert not forbidden_imports(path, {"actual.models", "actual.capabilities"}), path
