from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

VCS_DIR = '.minivcs'
OBJECTS_DIR = 'objects'
REFS_DIR = 'refs'
HEADS_DIR = 'heads'
TAGS_DIR = 'tags'
INDEX_FILE = 'index.json'
COMMITS_FILE = 'commits.json'
CONFIG_FILE = 'config.json'
HEAD_FILE = 'HEAD'
MERGE_HEAD_FILE = 'MERGE_HEAD'
MERGE_MSG_FILE = 'MERGE_MSG'


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def ensure_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def is_subpath(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def rel_posix(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def walk_working_files(root: Path):
    vcs_root = root / VCS_DIR
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if current == vcs_root:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d != VCS_DIR and not d.startswith('.git')]
        for name in filenames:
            p = current / name
            if not p.is_file():
                continue
            if is_subpath(p, vcs_root):
                continue
            yield p
