"""Basic tracked-file credential scan; prints locations, never matching values.

This deliberately small check is not a substitute for dedicated secret scanning
or a human publication review. Synthetic canaries are not credentials.
"""

import re
import subprocess
from pathlib import Path

PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{50,}"),
    re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:password|api_key|access_token)\s*[=:]\s*['\"][A-Za-z0-9_/-]{16,}"),
    re.compile(r"(?i)C:[\\/]Users[\\/](?!Public[\\/])"),
]


def main() -> int:
    files = (
        subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True)
        .stdout.decode()
        .split("\0")
    )
    findings = []
    for name in filter(None, files):
        path = Path(name)
        content = path.read_text(encoding="utf-8-sig")
        for number, line in enumerate(content.splitlines(), 1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append(f"{name}:{number}")
    if findings:
        print("Potential credentials or private paths at: " + ", ".join(findings))
        return 1
    print(f"Basic credential scan passed for {len([f for f in files if f])} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
