from __future__ import annotations

import difflib
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import (
    COMMITS_FILE,
    CONFIG_FILE,
    HEAD_FILE,
    HEADS_DIR,
    INDEX_FILE,
    MERGE_HEAD_FILE,
    MERGE_MSG_FILE,
    OBJECTS_DIR,
    REFS_DIR,
    TAGS_DIR,
    VCS_DIR,
    ensure_text,
    read_json,
    rel_posix,
    sha1_bytes,
    walk_working_files,
    write_json,
)


@dataclass
class StatusResult:
    staged_new: list[str]
    staged_modified: list[str]
    unstaged_modified: list[str]
    untracked: list[str]
    deleted: list[str]


@dataclass
class MergeResult:
    merged: bool
    fast_forward: bool
    target_name: str
    target_commit: str
    conflicts: list[str]
    message: str


class MiniVCSRepo:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.vcs = self.root / VCS_DIR
        self.objects = self.vcs / OBJECTS_DIR
        self.refs = self.vcs / REFS_DIR
        self.heads = self.refs / HEADS_DIR
        self.tags = self.refs / TAGS_DIR
        self.index_file = self.vcs / INDEX_FILE
        self.commits_file = self.vcs / COMMITS_FILE
        self.config_file = self.vcs / CONFIG_FILE
        self.head_file = self.vcs / HEAD_FILE
        self.merge_head_file = self.vcs / MERGE_HEAD_FILE
        self.merge_msg_file = self.vcs / MERGE_MSG_FILE

    @classmethod
    def discover(cls, start: Path | None = None) -> 'MiniVCSRepo':
        current = (start or Path.cwd()).resolve()
        for candidate in [current, *current.parents]:
            if (candidate / VCS_DIR).exists():
                return cls(candidate)
        raise FileNotFoundError('Not inside a MiniVCS repository. Run `python main.py init`.')

    def exists(self) -> bool:
        return self.vcs.exists()

    def init(self) -> None:
        if self.exists():
            raise FileExistsError('Repository already initialized.')
        self.objects.mkdir(parents=True)
        self.heads.mkdir(parents=True)
        self.tags.mkdir(parents=True)
        write_json(self.index_file, {})
        write_json(self.commits_file, {})
        write_json(self.config_file, {'user': {'name': 'Student', 'email': 'student@example.com'}})
        (self.heads / 'main').write_text('', encoding='utf-8')
        self.head_file.write_text('ref: refs/heads/main', encoding='utf-8')

    def set_user(self, name: str, email: str) -> None:
        config = read_json(self.config_file, {})
        config['user'] = {'name': name, 'email': email}
        write_json(self.config_file, config)

    def _read_head_ref(self) -> str:
        raw = self.head_file.read_text(encoding='utf-8').strip()
        if raw.startswith('ref: '):
            return raw[5:]
        return raw

    def current_branch(self) -> str | None:
        raw = self.head_file.read_text(encoding='utf-8').strip()
        if raw.startswith('ref: refs/heads/'):
            return raw.split('/')[-1]
        return None

    def head_commit(self) -> str | None:
        ref = self._read_head_ref()
        if ref.startswith('refs/'):
            path = self.vcs / ref
            if not path.exists():
                return None
            value = path.read_text(encoding='utf-8').strip()
            return value or None
        return ref or None

    def merge_in_progress(self) -> bool:
        return self.merge_head_file.exists()

    def merge_target(self) -> str | None:
        if not self.merge_in_progress():
            return None
        value = self.merge_head_file.read_text(encoding='utf-8').strip()
        return value or None

    def _set_head_commit(self, commit_id: str) -> None:
        ref = self._read_head_ref()
        if ref.startswith('refs/'):
            path = self.vcs / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(commit_id, encoding='utf-8')
        else:
            self.head_file.write_text(commit_id, encoding='utf-8')

    def _load_index(self) -> dict[str, dict[str, Any]]:
        return read_json(self.index_file, {})

    def _save_index(self, data: dict[str, dict[str, Any]]) -> None:
        write_json(self.index_file, data)

    def _load_commits(self) -> dict[str, Any]:
        return read_json(self.commits_file, {})

    def _save_commits(self, data: dict[str, Any]) -> None:
        write_json(self.commits_file, data)

    def _hash_file(self, path: Path) -> tuple[str, bytes]:
        data = path.read_bytes()
        return sha1_bytes(data), data

    def _store_blob(self, file_hash: str, data: bytes) -> None:
        obj = self.objects / file_hash
        if not obj.exists():
            obj.write_bytes(data)

    def _load_commit_tree(self, commit_id: str | None) -> dict[str, dict[str, Any]]:
        if not commit_id:
            return {}
        commits = self._load_commits()
        commit = commits.get(commit_id)
        if not commit:
            return {}
        return commit.get('tree', {})

    def _blob_bytes(self, file_hash: str | None) -> bytes:
        if not file_hash:
            return b''
        return (self.objects / file_hash).read_bytes()

    def _blob_text_lines(self, file_hash: str | None) -> list[str]:
        if not file_hash:
            return []
        return ensure_text(self.objects / file_hash).splitlines(keepends=True)

    def _working_tree(self) -> dict[str, dict[str, Any]]:
        working: dict[str, dict[str, Any]] = {}
        for file_path in walk_working_files(self.root):
            rel = rel_posix(file_path, self.root)
            h, data = self._hash_file(file_path)
            working[rel] = {'hash': h, 'size': len(data)}
        return working

    def add(self, paths: list[str]) -> list[str]:
        index = self._load_index()
        added: list[str] = []
        expanded: list[Path] = []
        for raw in paths:
            p = (self.root / raw).resolve()
            if p.is_dir():
                expanded.extend(sorted(x for x in p.rglob('*') if x.is_file() and VCS_DIR not in x.parts))
            else:
                expanded.append(p)
        seen = set()
        for p in expanded:
            if not p.exists() or not p.is_file():
                continue
            rel = rel_posix(p, self.root)
            if rel in seen or rel.startswith(f'{VCS_DIR}/'):
                continue
            seen.add(rel)
            h, data = self._hash_file(p)
            self._store_blob(h, data)
            index[rel] = {'hash': h, 'size': len(data)}
            added.append(rel)
        self._save_index(index)
        return added

    def remove(self, paths: list[str], keep_working: bool = False) -> list[str]:
        index = self._load_index()
        removed: list[str] = []
        for raw in paths:
            rel = rel_posix((self.root / raw).resolve(), self.root)
            if rel in index:
                del index[rel]
                removed.append(rel)
            target = self.root / rel
            if target.exists() and target.is_file() and not keep_working:
                target.unlink()
        self._save_index(index)
        return removed

    def status(self) -> StatusResult:
        index = self._load_index()
        head_tree = self._load_commit_tree(self.head_commit())
        working = self._working_tree()

        staged_new: list[str] = []
        staged_modified: list[str] = []
        unstaged_modified: list[str] = []
        untracked: list[str] = []
        deleted: list[str] = []

        for rel, meta in index.items():
            if rel not in head_tree:
                staged_new.append(rel)
            elif head_tree[rel]['hash'] != meta['hash']:
                staged_modified.append(rel)

        for rel, meta in working.items():
            if rel not in index:
                untracked.append(rel)
            elif index[rel]['hash'] != meta['hash']:
                unstaged_modified.append(rel)

        for rel in set(index) | set(head_tree):
            if rel not in working and rel in head_tree:
                deleted.append(rel)

        return StatusResult(
            staged_new=sorted(staged_new),
            staged_modified=sorted(staged_modified),
            unstaged_modified=sorted(unstaged_modified),
            untracked=sorted(untracked),
            deleted=sorted(deleted),
        )

    def _require_clean_worktree(self) -> None:
        status = self.status()
        if any([
            status.staged_new,
            status.staged_modified,
            status.unstaged_modified,
            status.untracked,
            status.deleted,
        ]):
            raise ValueError('Working tree must be clean before checkout or merge.')

    def commit(self, message: str) -> str:
        if self.merge_in_progress() and self.status().unstaged_modified:
            raise ValueError('Resolve merge conflicts and stage the files before committing.')
        index = self._load_index()
        parent = self.head_commit()
        commits = self._load_commits()
        parent_tree = self._load_commit_tree(parent)
        if index == parent_tree:
            raise ValueError('Nothing to commit.')
        config = read_json(self.config_file, {})
        user = config.get('user', {'name': 'Student', 'email': 'student@example.com'})
        payload: dict[str, Any] = {
            'parent': parent,
            'message': message,
            'author': user,
            'timestamp': int(time.time()),
            'tree': index,
        }
        if self.merge_in_progress():
            merge_parent = self.merge_target()
            if merge_parent:
                payload['merge_parent'] = merge_parent
        commit_id = sha1_bytes(str(payload).encode('utf-8'))
        commits[commit_id] = payload
        self._save_commits(commits)
        self._set_head_commit(commit_id)
        self._clear_merge_state()
        return commit_id

    def log(self, limit: int = 20) -> list[dict[str, Any]]:
        commits = self._load_commits()
        out = []
        current = self.head_commit()
        count = 0
        while current and current in commits and count < limit:
            entry = {'id': current, **commits[current]}
            out.append(entry)
            current = commits[current].get('parent')
            count += 1
        return out

    def show_commit(self, commit_id: str) -> dict[str, Any]:
        commits = self._load_commits()
        if commit_id not in commits:
            raise KeyError(f'Unknown commit: {commit_id}')
        return {'id': commit_id, **commits[commit_id]}

    def diff(self, target: str | None = None) -> str:
        index = self._load_index()
        if target == '--staged':
            old_tree = self._load_commit_tree(self.head_commit())
            new_tree = index
        else:
            old_tree = index
            new_tree = self._working_tree()

        paths = sorted(set(old_tree) | set(new_tree))
        chunks: list[str] = []
        for rel in paths:
            old_hash = old_tree.get(rel, {}).get('hash')
            new_hash = new_tree.get(rel, {}).get('hash')
            if old_hash == new_hash:
                continue
            old_text = self._blob_text_lines(old_hash)
            if target == '--staged':
                new_text = self._blob_text_lines(new_hash)
            else:
                work_path = self.root / rel
                new_text = ensure_text(work_path).splitlines(keepends=True) if work_path.exists() else []
            chunks.extend(difflib.unified_diff(old_text, new_text, fromfile=f'a/{rel}', tofile=f'b/{rel}'))
        return ''.join(chunks) or 'No differences found.\n'

    def branch(self, name: str) -> None:
        head = self.head_commit() or ''
        ref = self.heads / name
        if ref.exists():
            raise FileExistsError(f'Branch {name} already exists.')
        ref.write_text(head, encoding='utf-8')

    def branches(self) -> list[tuple[str, bool]]:
        current = self.current_branch()
        out = []
        for p in sorted(self.heads.glob('*')):
            out.append((p.name, p.name == current))
        return out

    def _resolve_ref_to_commit(self, name: str) -> tuple[str, str]:
        branch_ref = self.heads / name
        if branch_ref.exists():
            return name, branch_ref.read_text(encoding='utf-8').strip()
        commits = self._load_commits()
        if name in commits:
            return name, name
        raise KeyError(f'Unknown branch or commit: {name}')

    def checkout(self, name: str) -> None:
        self._require_clean_worktree()
        branch_ref = self.heads / name
        target_commit: str | None = None
        if branch_ref.exists():
            self.head_file.write_text(f'ref: refs/heads/{name}', encoding='utf-8')
            raw = branch_ref.read_text(encoding='utf-8').strip()
            target_commit = raw or None
        else:
            commits = self._load_commits()
            if name not in commits:
                raise KeyError(f'Unknown branch or commit: {name}')
            self.head_file.write_text(name, encoding='utf-8')
            target_commit = name
        self._restore_tree(self._load_commit_tree(target_commit))
        self._save_index(self._load_commit_tree(target_commit))
        self._clear_merge_state()

    def restore(self, path: str) -> None:
        index = self._load_index()
        rel = rel_posix((self.root / path).resolve(), self.root)
        if rel not in index:
            raise KeyError(f'{rel} is not tracked in index.')
        blob = self.objects / index[rel]['hash']
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(blob, target)

    def tag(self, name: str, commit_id: str | None = None) -> None:
        target = commit_id or self.head_commit()
        if not target:
            raise ValueError('No commit available to tag.')
        (self.tags / name).write_text(target, encoding='utf-8')

    def list_tags(self) -> list[tuple[str, str]]:
        out = []
        for p in sorted(self.tags.glob('*')):
            out.append((p.name, p.read_text(encoding='utf-8').strip()))
        return out

    def _restore_tree(self, tree: dict[str, dict[str, Any]]) -> None:
        tracked_now = set()
        for file_path in walk_working_files(self.root):
            tracked_now.add(rel_posix(file_path, self.root))
        for rel in tracked_now:
            if rel not in tree:
                (self.root / rel).unlink(missing_ok=True)
        for rel, meta in tree.items():
            src = self.objects / meta['hash']
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    def _ancestors(self, commit_id: str | None) -> list[str]:
        commits = self._load_commits()
        seen: list[str] = []
        current = commit_id
        while current and current in commits and current not in seen:
            seen.append(current)
            current = commits[current].get('parent')
        return seen

    def _merge_base(self, left: str | None, right: str | None) -> str | None:
        if not left or not right:
            return None
        left_chain = set(self._ancestors(left))
        current = right
        commits = self._load_commits()
        while current and current in commits:
            if current in left_chain:
                return current
            current = commits[current].get('parent')
        return None

    def _clear_merge_state(self) -> None:
        self.merge_head_file.unlink(missing_ok=True)
        self.merge_msg_file.unlink(missing_ok=True)

    def _write_merge_conflict(self, rel: str, current_hash: str | None, target_hash: str | None, target_name: str) -> None:
        current_text = self._blob_bytes(current_hash).decode('utf-8', errors='replace') if current_hash else ''
        target_text = self._blob_bytes(target_hash).decode('utf-8', errors='replace') if target_hash else ''
        merged_text = (
            '<<<<<<< HEAD\n'
            f'{current_text}'
            '=======\n'
            f'{target_text}'
            f'>>>>>>> {target_name}\n'
        )
        dst = self.root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(merged_text, encoding='utf-8')

    def merge(self, name: str) -> MergeResult:
        if self.merge_in_progress():
            raise ValueError('A merge is already in progress. Resolve it and commit first.')
        self._require_clean_worktree()
        current_commit = self.head_commit()
        current_branch = self.current_branch()
        if not current_branch:
            raise ValueError('Merge requires being on a branch, not detached HEAD.')
        target_name, target_commit = self._resolve_ref_to_commit(name)
        if not target_commit:
            raise ValueError(f'Nothing to merge from {target_name}.')
        if target_commit == current_commit:
            return MergeResult(True, False, target_name, target_commit, [], 'Already up to date.')

        base_commit = self._merge_base(current_commit, target_commit)
        if base_commit == target_commit:
            return MergeResult(True, False, target_name, target_commit, [], 'Already up to date.')

        target_tree = self._load_commit_tree(target_commit)
        if base_commit == current_commit:
            self._set_head_commit(target_commit)
            self._restore_tree(target_tree)
            self._save_index(target_tree)
            return MergeResult(True, True, target_name, target_commit, [], f'Fast-forward merge from {target_name}.')

        base_tree = self._load_commit_tree(base_commit)
        current_tree = self._load_commit_tree(current_commit)
        merged_tree = dict(current_tree)
        conflicts: list[str] = []

        for rel in sorted(set(base_tree) | set(current_tree) | set(target_tree)):
            base_hash = base_tree.get(rel, {}).get('hash')
            current_hash = current_tree.get(rel, {}).get('hash')
            target_hash = target_tree.get(rel, {}).get('hash')

            if current_hash == target_hash:
                if current_hash is None:
                    merged_tree.pop(rel, None)
                else:
                    merged_tree[rel] = target_tree[rel]
                continue

            if base_hash == current_hash:
                if target_hash is None:
                    merged_tree.pop(rel, None)
                else:
                    merged_tree[rel] = target_tree[rel]
                continue

            if base_hash == target_hash:
                if current_hash is None:
                    merged_tree.pop(rel, None)
                else:
                    merged_tree[rel] = current_tree[rel]
                continue

            conflicts.append(rel)

        self._restore_tree(merged_tree)
        self._save_index(merged_tree)

        for rel in conflicts:
            self._write_merge_conflict(
                rel,
                current_tree.get(rel, {}).get('hash'),
                target_tree.get(rel, {}).get('hash'),
                target_name,
            )
            self._load_index().pop(rel, None)
        if conflicts:
            index = self._load_index()
            for rel in conflicts:
                index.pop(rel, None)
            self._save_index(index)
            self.merge_head_file.write_text(target_commit, encoding='utf-8')
            self.merge_msg_file.write_text(f'Merge branch {target_name}', encoding='utf-8')
            return MergeResult(False, False, target_name, target_commit, conflicts, 'Merge has conflicts. Resolve them, add the files, and commit.')

        merge_message = f'Merge branch {target_name} into {current_branch}'
        self.merge_head_file.write_text(target_commit, encoding='utf-8')
        self.merge_msg_file.write_text(merge_message, encoding='utf-8')
        commit_id = self.commit(merge_message)
        return MergeResult(True, False, target_name, target_commit, [], f'Merged {target_name} into {current_branch} as {commit_id[:7]}.')
