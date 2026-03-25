from pathlib import Path

RULES_DIR = Path(__file__).resolve().parents[2] / "docs" / "ai_rules"


def load_rules(filename: str) -> str:
    path = RULES_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()
