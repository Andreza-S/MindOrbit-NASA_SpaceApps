"""Lista os textos marcados para tradução (chamadas t("...") e N_("...")) em todo o código.

Usado por tests/test_i18n.py e para completar support/i18n_en.py:
    python scripts/i18n_scan.py          # imprime os que ainda faltam em inglês
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"tests", ".venv", "venv", "__pycache__", "scripts"}


def keys_in_code() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP for part in path.relative_to(ROOT).parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("t", "N_")
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                found.setdefault(node.args[0].value, []).append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return found


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    from support.i18n_en import EN
    missing = [k for k in keys_in_code() if k not in EN]
    for k in missing:
        print(repr(k))
    print(f"-- {len(missing)} sem tradução, de {len(keys_in_code())}", file=sys.stderr)
