"""Complete event/action trace logging (JSONL) — the scoring source of truth.

Guide §5: each scenario is "scored 0-100 based strictly on trace logs".
Every input event, emitted action, cancellation, and registry transition is
recorded here with a reason code (BUILD_PLAN §3.2 decision 7).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Trace:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "w", encoding="utf-8")
        self.entries: list[dict[str, Any]] = []

    def log(self, kind: str, ts_ms: int, **fields: Any) -> dict[str, Any]:
        rec: dict[str, Any] = {"kind": kind, "ts_ms": ts_ms, **fields}
        self.entries.append(rec)
        self._fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()
        return rec

    def of_kind(self, kind: str) -> list[dict[str, Any]]:
        return [e for e in self.entries if e["kind"] == kind]

    def first(self, kind: str) -> dict[str, Any] | None:
        rows = self.of_kind(kind)
        return rows[0] if rows else None

    def close(self) -> None:
        self._fh.close()
