"""Agent-facing discovery of JP Core capabilities and implementations."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


def implementations() -> list[dict]:
    path = files("jp_core").joinpath("implementations.toml")
    if not path.is_file():
        path = Path(__file__).resolve().parents[2] / "IMPLEMENTATIONS.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle)["projects"]


def find_examples(capability: str, *, consumers_only: bool = False) -> list[dict]:
    matches = [item for item in implementations() if capability in item.get("capabilities", [])]
    if consumers_only:
        matches = [item for item in matches if item.get("status") == "consumer"]
    return matches


def capabilities() -> list[str]:
    return sorted({capability for item in implementations() for capability in item.get("capabilities", [])})
