"""Compare a fresh SIMULATED build with the checked-in static assets."""

import hashlib
import json
import sys
from pathlib import Path


def verify(fresh: Path, published: Path) -> None:
    expected = {"demo.json", "traces.jsonl", "metrics.csv", "report.md", "manifest.json"}
    for directory in (fresh, published):
        if {p.name for p in directory.iterdir()} != expected:
            raise ValueError("Unexpected public artifact files")
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        for name, digest in manifest["files_sha256"].items():
            if (
                name not in expected
                or hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest
            ):
                raise ValueError("Public artifact hash mismatch")
    for name in expected:
        if (fresh / name).read_bytes() != (published / name).read_bytes():
            raise ValueError(f"Non-reproducible SIMULATED artifact: {name}")
    print("All five SIMULATED artifacts reproduce byte-for-byte; SHA-256 manifest verified.")


if __name__ == "__main__":
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
