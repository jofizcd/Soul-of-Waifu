#!/usr/bin/env python3
"""Copy editable, tracked project files into the adjacent Release runtime.

The Git checkout is the source of truth.  The Release directory provides the
large, untracked runtime: Python, dependencies, FFmpeg, models, icons, and
other binary assets.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent
DEFAULT_RUNTIME = SOURCE_ROOT.parent / "Soul-of-Waifu-v2.4.0"
MANIFEST_NAME = ".dev-sync-manifest.json"

# Runtime-managed files contain user settings, downloaded models, or binaries.
# Never overwrite them during normal development syncs.
EXCLUDED_EXACT = {
    "app/configuration/api.json",
    "app/configuration/characters.json",
    "app/configuration/settings.json",
}
EXCLUDED_PREFIXES = (
    ".github/",
    "logs/",
    "app/data/",
    "app/ffmpeg/",
    "app/font/",
    "app/voices/",
    "assets/readme/",
)
INCLUDED_PREFIXES = (
    "app/configuration/",
    "app/gui/",
    "app/translations/",
    "app/utils/",
    "app/web_client/",
    "assets/",
)
INCLUDED_EXACT = {"main.py"}


def is_syncable(path: str) -> bool:
    """Return whether a Git-tracked file belongs in the editable runtime overlay."""
    if path.endswith("/.gitkeep") or path == ".gitkeep":
        return False
    if path in EXCLUDED_EXACT or path.startswith(EXCLUDED_PREFIXES):
        return False
    return path in INCLUDED_EXACT or path.startswith(INCLUDED_PREFIXES)


def tracked_syncable_files() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(SOURCE_ROOT), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Git was not found. Install Git or run this from a Git checkout."
        ) from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"Could not list Git-tracked files: {detail}") from error

    paths = set()
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8")
        if is_syncable(path):
            paths.add(path)
    return paths


def same_contents(left: Path, right: Path) -> bool:
    if not right.is_file() or left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as source_file, right.open("rb") as runtime_file:
        while True:
            source_chunk = source_file.read(1024 * 1024)
            runtime_chunk = runtime_file.read(1024 * 1024)
            if source_chunk != runtime_chunk:
                return False
            if not source_chunk:
                return True


def load_manifest(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data.get("files", [])
        if not isinstance(files, list) or not all(
            isinstance(item, str) for item in files
        ):
            raise ValueError("files is not a string list")
        return set(files)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Warning: ignored invalid sync manifest ({error}).")
        return set()


def safe_runtime_path(runtime_root: Path, relative_path: str) -> Path:
    candidate = runtime_root / relative_path
    # Git paths are relative, but keep the write boundary explicit.
    if (
        ".." in Path(relative_path).parts
        or candidate.parent != candidate.parent.resolve()
    ):
        raise RuntimeError(f"Unsafe tracked path: {relative_path}")
    return candidate


def main() -> int:
    runtime_root = (
        Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_RUNTIME.resolve()
    )
    if len(sys.argv) > 2:
        print("Usage: dev_sync.py [RUNTIME_DIRECTORY]", file=sys.stderr)
        return 2
    if not (runtime_root / "main.py").is_file():
        print(
            f"Runtime was not found or is incomplete: {runtime_root}", file=sys.stderr
        )
        return 1

    current_files = tracked_syncable_files()
    if not current_files:
        print("No editable tracked files were found.", file=sys.stderr)
        return 1

    manifest_path = runtime_root / MANIFEST_NAME
    previous_files = load_manifest(manifest_path)
    copied = 0
    unchanged = 0

    for relative_path in sorted(current_files):
        source_path = SOURCE_ROOT / relative_path
        runtime_path = safe_runtime_path(runtime_root, relative_path)
        if not source_path.is_file():
            raise RuntimeError(f"Tracked source file is missing: {source_path}")
        if same_contents(source_path, runtime_path):
            unchanged += 1
            continue
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, runtime_path)
        copied += 1

    removed = 0
    for relative_path in sorted(previous_files - current_files):
        runtime_path = safe_runtime_path(runtime_root, relative_path)
        if runtime_path.is_file():
            runtime_path.unlink()
            removed += 1

    manifest_path.write_text(
        json.dumps({"files": sorted(current_files)}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Dev sync complete: copied {copied}, unchanged {unchanged}, removed {removed}."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Dev sync failed: {error}", file=sys.stderr)
        raise SystemExit(1)
