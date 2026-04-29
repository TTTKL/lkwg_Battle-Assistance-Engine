from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent


def get_default_data_dir() -> Path:
    candidates = [
        _ROOT / "apps" / "calculator_web" / "Data",
        _ROOT / "calculator_workspace" / "Calculator" / "Data",
        _ROOT / "legacy_workspace" / "Calculator" / "Data",
        _ROOT / "legacy_calculator_workspace" / "Calculator" / "Data",
        _ROOT / "20260402114626" / "Calculator" / "Data",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
