from __future__ import annotations
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
TEXT_EXTS = {".py",".md",".yml",".yaml",".json",".toml",".ini",".cfg",".txt",".js",".ts",".tsx",".html",".css",".env"}

patterns = [
    ("non-empty FIRMS_MAP_KEY assignment", re.compile(r"(?im)^\s*FIRMS_MAP_KEY\s*=\s*[^\s#]+\s*$")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Google service-account private_key field", re.compile(r'"private_key"\s*:\s*"-----BEGIN PRIVATE KEY-----')),
]

violations=[]
for path in ROOT.rglob("*"):
    if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
        continue
    if path.name == ".env.example":
        continue
    if path.suffix.lower() not in TEXT_EXTS and path.name not in {"Dockerfile","Makefile"}:
        continue
    try:
        text=path.read_text(encoding="utf-8",errors="ignore")
    except Exception:
        continue
    for label, rx in patterns:
        if rx.search(text):
            violations.append(f"{path.relative_to(ROOT)}: {label}")

if violations:
    print("Potential secret(s) detected in tracked source:")
    print("\n".join(f"- {v}" for v in violations))
    sys.exit(1)

print("Secret scan passed: no obvious committed provider credentials detected.")
