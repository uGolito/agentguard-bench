"""Append/flush journals preserve partial runs without exposing headers or credentials."""

import json
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Sink = Callable[[dict[str, Any]], None]


class EventLog(list):
    def __init__(self, sink: Sink | None = None) -> None:
        super().__init__()
        self.sink = sink

    def append(self, event: dict[str, Any]) -> None:
        event = {"event_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat(), **event}
        if self.sink:
            self.sink(event)
        super().append(event)

    def extend(self, events: Iterable[dict[str, Any]]) -> None:
        for event in events:
            self.append(event)


class Journal:
    def __init__(self, path: Path) -> None:
        self.stream = path.open("x", encoding="utf-8")
        self.seen: set[str] = set()

    def __call__(self, event: dict[str, Any]) -> None:
        identity = event["event_id"]
        if identity not in self.seen:
            self.stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            self.stream.flush()
            self.seen.add(identity)

    def close(self) -> None:
        self.stream.close()
