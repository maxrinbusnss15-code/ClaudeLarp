"""Append-only decision log, so every decision (and every side flip) is auditable."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Decision


class Journal:
    def __init__(self, path: Path):
        self.path = path

    def last(self, kind: str, subject: str) -> dict | None:
        if not self.path.exists():
            return None
        found = None
        with self.path.open() as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("kind") == kind and rec.get("subject") == subject:
                    found = rec
        return found

    def append(self, d: Decision) -> str | None:
        """Write the decision; return a message if the side flipped since last time."""
        prev = self.last(d.kind, d.subject)
        rec = d.to_dict()
        # keep the journal compact: drop raw evidence, keep answers' summaries
        for a in rec["answers"]:
            a["evidence"] = [{"source": e["source"], "signal": round(e["signal"], 3), "summary": e["summary"]}
                             for e in a["evidence"]]
        with self.path.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        if prev and prev["side"] != d.side.value:
            return f"SIDE FLIP {d.kind} {d.subject}: {prev['side']} -> {d.side.value}"
        return None
