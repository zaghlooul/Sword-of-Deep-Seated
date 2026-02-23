"""
SwordSuite — Session Manager
Save / load / export scan sessions as JSON.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


SESSIONS_DIR = Path.home() / ".swordsuite" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DorkResult:
    url:     str
    title:   str = ""
    snippet: str = ""
    dork:    str = ""


@dataclass
class KatanaResult:
    url:       str
    depth:     int  = 0
    kind:      str  = "endpoint"   # endpoint | form | js | file
    method:    str  = "GET"
    params:    List[str] = field(default_factory=list)


@dataclass
class SqlmapResult:
    url:       str
    param:     str  = ""
    technique: str  = ""
    payload:   str  = ""
    database:  str  = ""
    tables:    List[str] = field(default_factory=list)
    dump_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    name:         str
    target:       str        = ""
    created_at:   float      = field(default_factory=time.time)
    updated_at:   float      = field(default_factory=time.time)
    dork_results:   List[DorkResult]   = field(default_factory=list)
    katana_results: List[KatanaResult] = field(default_factory=list)
    sqlmap_results: List[SqlmapResult] = field(default_factory=list)
    notes:        str        = ""
    tags:         List[str]  = field(default_factory=list)
    chain_config: Dict[str, Any] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # File I/O
    # ----------------------------------------------------------------
    def save(self, path: Optional[Path] = None) -> Path:
        self.updated_at = time.time()
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in self.name)
        fpath = path or (SESSIONS_DIR / f"{safe_name}_{int(self.created_at)}.json")
        fpath.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return fpath

    @classmethod
    def load(cls, path: Path) -> "Session":
        data = json.loads(path.read_text(encoding="utf-8"))
        s = cls(name=data.get("name", path.stem))
        s.target       = data.get("target", "")
        s.created_at   = data.get("created_at", 0)
        s.updated_at   = data.get("updated_at", 0)
        s.notes        = data.get("notes", "")
        s.tags         = data.get("tags", [])
        s.chain_config = data.get("chain_config", {})
        s.dork_results   = [DorkResult(**r)   for r in data.get("dork_results", [])]
        s.katana_results = [KatanaResult(**r) for r in data.get("katana_results", [])]
        s.sqlmap_results = [SqlmapResult(**r) for r in data.get("sqlmap_results", [])]
        return s

    def export_txt(self, path: Path) -> None:
        lines = [
            f"SwordSuite Session Export — {self.name}",
            f"Target : {self.target}",
            f"Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.created_at))}",
            "",
        ]
        if self.dork_results:
            lines += ["=== Dork Results ==="]
            for r in self.dork_results:
                lines += [f"  {r.url}", f"  Dork: {r.dork}", f"  {r.snippet}", ""]

        if self.katana_results:
            lines += ["=== Katana Endpoints ==="]
            for r in self.katana_results:
                lines += [f"  [{r.kind.upper()}] {r.method} {r.url}", ""]

        if self.sqlmap_results:
            lines += ["=== SQLMap Findings ==="]
            for r in self.sqlmap_results:
                lines += [
                    f"  URL      : {r.url}",
                    f"  Param    : {r.param}",
                    f"  Technique: {r.technique}",
                    f"  Database : {r.database}",
                    f"  Payload  : {r.payload}",
                    "",
                ]

        path.write_text("\n".join(lines), encoding="utf-8")

    # ----------------------------------------------------------------
    # Stats helpers
    # ----------------------------------------------------------------
    @property
    def total_findings(self) -> int:
        return len(self.dork_results) + len(self.katana_results) + len(self.sqlmap_results)


# ---------------------------------------------------------------------------
# Session registry helpers
# ---------------------------------------------------------------------------
def list_sessions() -> List[Path]:
    return sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def delete_session(path: Path) -> None:
    if path.exists():
        path.unlink()
