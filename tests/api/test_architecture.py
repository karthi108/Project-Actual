"""Guard the trust and dependency boundaries rather than internal implementation details."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "actual"


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_domain_contracts_remain_independent_of_http_application_and_storage() -> None:
    forbidden = {"fastapi", "starlette", "sqlalchemy", "actual.api", "actual.application"}
    for responsibility in ("core", "career", "profile"):
        for path in (ROOT / responsibility).rglob("*.py"):
            assert not any(
                module == prefix or module.startswith(prefix + ".")
                for module in imports(path)
                for prefix in forbidden
            ), path.name


def test_runtime_boundary_does_not_import_careerlab_generator_or_answers() -> None:
    # Observable development fixtures are test inputs, never a runtime data source.
    for responsibility in ("api", "application", "persistence"):
        for path in (ROOT / responsibility).rglob("*.py"):
            assert not any(
                module == "actual.careerlab" or module.startswith("actual.careerlab.")
                for module in imports(path)
            ), path.name
