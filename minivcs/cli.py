from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from .repo import MiniVCSRepo


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='minivcs', description='A tiny version control system built in Python.')
    sub = p.add_subparsers(dest='command', required=True)

    sub.add_parser('init')

    cfg = sub.add_parser('config')
    cfg.add_argument('name')
    cfg.add_argument('email')

    add = sub.add_parser('add')
    add.add_argument('paths', nargs='+')

    rm = sub.add_parser('rm')
    rm.add_argument('paths', nargs='+')
    rm.add_argument('--keep', action='store_true')

    commit = sub.add_parser('commit')
    commit.add_argument('-m', '--message', required=True)

    sub.add_parser('status')

    log = sub.add_parser('log')
    log.add_argument('-n', '--limit', type=int, default=20)

    diff = sub.add_parser('diff')
    diff.add_argument('--staged', action='store_true')

    branch = sub.add_parser('branch')
    branch.add_argument('name', nargs='?')

    checkout = sub.add_parser('checkout')
    checkout.add_argument('name')

    merge = sub.add_parser('merge')
    merge.add_argument('name')

    restore = sub.add_parser('restore')
    restore.add_argument('path')

    tag = sub.add_parser('tag')
    tag.add_argument('name', nargs='?')
    tag.add_argument('commit_id', nargs='?')
    tag.add_argument('--list', action='store_true')

    show = sub.add_parser('show')
    show.add_argument('commit_id')

    return p


def cmd_init() -> int:
    repo = MiniVCSRepo(Path.cwd())
    repo.init()
    print('Initialized empty MiniVCS repository in .minivcs/')
    return 0


def cmd_config(args) -> int:
    repo = MiniVCSRepo.discover()
    repo.set_user(args.name, args.email)
    print(f'Configured user: {args.name} <{args.email}>')
    return 0


def cmd_add(args) -> int:
    repo = MiniVCSRepo.discover()
    added = repo.add(args.paths)
    if not added:
        print('No files added.')
    else:
        for item in added:
            print(f'added: {item}')
    return 0


def cmd_rm(args) -> int:
    repo = MiniVCSRepo.discover()
    removed = repo.remove(args.paths, keep_working=args.keep)
    for item in removed:
        print(f'removed: {item}')
    return 0


def cmd_commit(args) -> int:
    repo = MiniVCSRepo.discover()
    commit_id = repo.commit(args.message)
    print(f'[{repo.current_branch() or "detached"} {commit_id[:7]}] {args.message}')
    return 0


def cmd_status() -> int:
    repo = MiniVCSRepo.discover()
    status = repo.status()
    print(f'On branch: {repo.current_branch() or "detached"}')
    if repo.merge_in_progress():
        print(f'Merge in progress with: {repo.merge_target()}')
    sections = [
        ('Staged new', status.staged_new),
        ('Staged modified', status.staged_modified),
        ('Unstaged modified', status.unstaged_modified),
        ('Deleted', status.deleted),
        ('Untracked', status.untracked),
    ]
    for title, items in sections:
        print(f'\n{title}:')
        if items:
            for item in items:
                print(f'  {item}')
        else:
            print('  none')
    return 0


def cmd_log(args) -> int:
    repo = MiniVCSRepo.discover()
    for item in repo.log(limit=args.limit):
        ts = dt.datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"commit {item['id']}")
        if item.get('merge_parent'):
            print(f"Merge:  {item['parent'][:7]} {item['merge_parent'][:7]}")
        print(f"Author: {item['author']['name']} <{item['author']['email']}>")
        print(f"Date:   {ts}")
        print(f"\n    {item['message']}\n")
    return 0


def cmd_diff(args) -> int:
    repo = MiniVCSRepo.discover()
    print(repo.diff('--staged' if args.staged else None), end='')
    return 0


def cmd_branch(args) -> int:
    repo = MiniVCSRepo.discover()
    if args.name:
        repo.branch(args.name)
        print(f'Created branch {args.name}')
    else:
        for name, active in repo.branches():
            print(f"{'*' if active else ' '} {name}")
    return 0


def cmd_checkout(args) -> int:
    repo = MiniVCSRepo.discover()
    repo.checkout(args.name)
    print(f'Checked out {args.name}')
    return 0


def cmd_merge(args) -> int:
    repo = MiniVCSRepo.discover()
    result = repo.merge(args.name)
    print(result.message)
    if result.conflicts:
        print('Conflicts:')
        for rel in result.conflicts:
            print(f'  {rel}')
    return 0


def cmd_restore(args) -> int:
    repo = MiniVCSRepo.discover()
    repo.restore(args.path)
    print(f'Restored {args.path}')
    return 0


def cmd_tag(args) -> int:
    repo = MiniVCSRepo.discover()
    if args.list:
        for name, commit_id in repo.list_tags():
            print(f'{name} -> {commit_id}')
        return 0
    if not args.name:
        raise SystemExit('tag name required unless --list is used')
    repo.tag(args.name, args.commit_id)
    print(f'Tagged {args.name}')
    return 0


def cmd_show(args) -> int:
    repo = MiniVCSRepo.discover()
    item = repo.show_commit(args.commit_id)
    ts = dt.datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"commit {item['id']}")
    if item.get('merge_parent'):
        print(f"Merge:  {item['parent'][:7]} {item['merge_parent'][:7]}")
    print(f"Author: {item['author']['name']} <{item['author']['email']}>")
    print(f"Date:   {ts}")
    print(f"\n    {item['message']}\n")
    print('Tracked files:')
    for rel in sorted(item['tree']):
        print(f'  {rel}')
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    cmd = args.command
    if cmd == 'init':
        return cmd_init()
    if cmd == 'config':
        return cmd_config(args)
    if cmd == 'add':
        return cmd_add(args)
    if cmd == 'rm':
        return cmd_rm(args)
    if cmd == 'commit':
        return cmd_commit(args)
    if cmd == 'status':
        return cmd_status()
    if cmd == 'log':
        return cmd_log(args)
    if cmd == 'diff':
        return cmd_diff(args)
    if cmd == 'branch':
        return cmd_branch(args)
    if cmd == 'checkout':
        return cmd_checkout(args)
    if cmd == 'merge':
        return cmd_merge(args)
    if cmd == 'restore':
        return cmd_restore(args)
    if cmd == 'tag':
        return cmd_tag(args)
    if cmd == 'show':
        return cmd_show(args)
    raise SystemExit(f'Unknown command: {cmd}')
