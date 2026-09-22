"""Tool-manifest parsing: dynamic tool definitions, read-only vs state-modifying.

Guide §3.2.4: "Parse dynamic tool definitions (read-only vs. state-modifying)
from manifests" — definitions arrive per-scenario and must be parsed at
runtime (unseen tools are a scored scenario category). Classification uses an
explicit flag when the manifest provides one; otherwise a verb heuristic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_READ_ONLY_VERBS = (
    "search",
    "find",
    "get",
    "lookup",
    "list",
    "query",
    "check",
    "read",
    "fetch",
)


class UnknownTool(KeyError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: dict[str, Any]
    state_modifying: bool

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "ToolSpec":
        name = str(raw.get("name", ""))
        if not name:
            raise ValueError("manifest tool entry missing 'name'")
        explicit = raw.get("mutates_state")
        if explicit is None:
            verb = name.split("_", 1)[0].lower()
            explicit = verb not in _READ_ONLY_VERBS
        return cls(
            name=name,
            description=str(raw.get("description", "")),
            params=dict(raw.get("parameters", {})),
            state_modifying=bool(explicit),
        )


@dataclass
class Manifest:
    tools: dict[str, ToolSpec]

    @classmethod
    def from_list(cls, raw_tools: list[dict[str, Any]]) -> "Manifest":
        return cls({spec.name: spec for spec in (ToolSpec.from_raw(r) for r in raw_tools)})

    def spec(self, name: str) -> ToolSpec:
        try:
            return self.tools[name]
        except KeyError:
            raise UnknownTool(name) from None
