"""Deterministic, inspectable Japanese processing pipelines."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Step:
    name: str
    run: Callable[[Any], Any]
    version: str = "1"


@dataclass
class PipelineResult:
    value: Any
    manifest: list[dict[str, str]] = field(default_factory=list)


class Pipeline:
    def __init__(self, *steps: Step):
        names = [step.name for step in steps]
        if len(names) != len(set(names)):
            raise ValueError("pipeline step names must be unique")
        self.steps = list(steps)

    def run(self, value: Any) -> PipelineResult:
        manifest = []
        for step in self.steps:
            before = _digest(value)
            value = step.run(value)
            manifest.append({
                "step": step.name,
                "version": step.version,
                "input": before,
                "output": _digest(value),
            })
        return PipelineResult(value, manifest)


def _digest(value: Any) -> str:
    try:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode()).hexdigest()
