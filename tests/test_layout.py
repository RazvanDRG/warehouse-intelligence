import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_layout_folders_exist():
    for folder in ("core", "adapters/warehouse", "api", "pipelines", "infra"):
        assert (ROOT / folder).is_dir(), f"missing folder {folder}/"


def test_core_does_not_import_adapters():
    offenders = []
    for path in (ROOT / "core").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            offenders += [f"{path.relative_to(ROOT)}: {n}" for n in names if n.split(".")[0] == "adapters"]
    assert not offenders, "core/ must stay generic:\n" + "\n".join(offenders)
