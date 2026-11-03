#!/usr/bin/env python3
"""Bounded public predeploy checks for the trusted Tipjar Pages workflow only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import re
import signal
import stat
import sys
import tarfile
import time
from urllib.parse import quote

# This is source tooling, never an installed CLI command.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CONTROLLER = 'nkovanen/tipjar'
CONTROLLER_ID = 1444643470
READ_SECONDS = 30
MAX_JSON = 4 * 1024 * 1024
MAX_HTTP = 8 * 1024 * 1024
MAX_ARTIFACT = 64 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{40}\Z')


def strict_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('invalid number')))
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError('invalid public JSON') from exc


def fetch(host, path, limit):
    """One unauthenticated HTTPS GET, no redirect/retry, bounded bytes and time."""
    if (host, path) != ('nkovanen.github.io', '/tipjar/board.json') and not (
        host == 'api.github.com' and (path == '/repos/nkovanen/tipjar' or
                                     re.fullmatch(r'/repos/nkovanen/tipjar/git/ref/heads/[A-Za-z0-9%._~-]+', path))
    ):
        raise ValueError('unsupported public endpoint')
    # Socket timeouts alone do not bound DNS or a peer trickling response headers.
    if not hasattr(signal, 'setitimer') or signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError('Linux Pages read deadline unavailable')
    def timed_out(signum, frame):
        raise ValueError('public read timed out')
    previous = signal.signal(signal.SIGALRM, timed_out)
    connection = None
    try:
        signal.setitimer(signal.ITIMER_REAL, READ_SECONDS)
        deadline = time.monotonic() + READ_SECONDS
        connection = http.client.HTTPSConnection(host, timeout=READ_SECONDS)
        connection.request('GET', path, headers={
            'Accept': 'application/json', 'User-Agent': 'tipjar-board-predeploy',
            'Cache-Control': 'no-cache, no-store', 'Pragma': 'no-cache',
        })
        response = connection.getresponse()
        chunks, size = [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('public read timed out')
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise ValueError('public response exceeds limit')
        if time.monotonic() > deadline:
            raise ValueError('public read timed out')
        return response.status, b''.join(chunks)
    except (OSError, http.client.HTTPException) as exc:
        raise ValueError('public read failed') from exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if connection is not None:
            connection.close()


def public_get(host, path, limit):
    try:
        return fetch(host, path, limit)
    except OSError as exc:
        raise ValueError('public state unreadable') from exc


def http_status_suffix(status):
    if type(status) is int and 100 <= status <= 599:
        return f' (HTTP {status})'
    return ''


def current_source():
    status, data = public_get('api.github.com', '/repos/nkovanen/tipjar', MAX_HTTP)
    if status != 200:
        raise ValueError('controller metadata unreadable' + http_status_suffix(status))
    repo = strict_json(data)
    if not isinstance(repo, dict) or type(repo.get('id')) is not int or repo['id'] != CONTROLLER_ID or (
        repo.get('full_name') != CONTROLLER or repo.get('private') is not False or
        repo.get('visibility') != 'public'
    ):
        raise ValueError('controller identity changed')
    branch = repo.get('default_branch')
    if not isinstance(branch, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,199}', branch) or (
        '..' in branch or '//' in branch or branch.endswith(('/', '.', '.lock'))
    ):
        raise ValueError('invalid default branch')
    status, data = public_get('api.github.com', '/repos/nkovanen/tipjar/git/ref/heads/' + quote(branch, safe=''), MAX_HTTP)
    if status != 200:
        raise ValueError('default branch unreadable' + http_status_suffix(status))
    ref = strict_json(data)
    obj = ref.get('object') if isinstance(ref, dict) else None
    if not isinstance(ref, dict) or ref.get('ref') != 'refs/heads/' + branch or not isinstance(obj, dict) or (
        obj.get('type') != 'commit' or not isinstance(obj.get('sha'), str) or not SHA.fullmatch(obj['sha'])
    ):
        raise ValueError('invalid default branch identity')
    return obj['sha']


def served_board():
    status, data = public_get('nkovanen.github.io', '/tipjar/board.json', MAX_JSON)
    if status == 404:
        return None
    if status != 200:
        raise ValueError('served board unreadable; redirects are not followed' + http_status_suffix(status))
    return data


def read_artifact(path):
    """Read the exact uploaded Pages tar; never extract any member."""
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARTIFACT:
        raise ValueError('invalid Pages artifact file')
    try:
        found = None
        paths = {}
        with tarfile.open(path, mode='r:') as archive:
            for count, member in enumerate(archive):
                if count >= 1000:
                    raise ValueError('too many Pages artifact members')
                # GNU tar's normal ./ prefix is allowed; extraction-equivalent aliases are not.
                name = member.name
                if name.startswith('./'):
                    name = name[2:]
                if member.isdir() and name.endswith('/'):
                    name = name[:-1]
                if name in ('', '.') and member.isdir():
                    name = '.'
                elif ('\\' in name or any(part in ('', '.', '..') for part in name.split('/'))):
                    raise ValueError('noncanonical Pages artifact path')
                if not (member.isdir() or member.isfile()) or name in paths:
                    raise ValueError('linked or colliding Pages artifact path')
                parents = [('/'.join(name.split('/')[:i])) for i in range(1, len(name.split('/')))]
                if any(parent in paths and not paths[parent] for parent in parents) or (
                    not member.isdir() and any(existing.startswith(name + '/') for existing in paths)
                ):
                    raise ValueError('Pages artifact file/directory collision')
                paths[name] = member.isdir()
                if name == 'board.json':
                    if found is not None or not member.isfile() or member.size > MAX_JSON:
                        raise ValueError('invalid or duplicate board.json in artifact')
                    with archive.extractfile(member) as stream:
                        found = stream.read(MAX_JSON + 1)
                    if len(found) != member.size:
                        raise ValueError('truncated board.json')
            if found is None:
                raise ValueError('artifact has no root board.json')
        return found
    except (tarfile.TarError, OSError) as exc:
        raise ValueError('unreadable Pages artifact') from exc


def checked_board(data, *, now, fresh=False):
    from agent_contribute.core import ProtocolError
    from tools.tipjar_board import validate_board, require_fresh
    try:
        board = validate_board(data, now=now)
        if fresh:
            require_fresh(board, now=now)
        return board
    except ProtocolError as exc:
        raise ValueError('invalid or expired board snapshot') from exc


def check_publication(candidate, served, *, current_source, now, bootstrap=False):
    board = checked_board(candidate, now=now, fresh=True)
    if not isinstance(current_source, str) or not SHA.fullmatch(current_source) or board['source_commit'] != current_source:
        raise ValueError('artifact source is no longer the trusted default branch')
    if served is None:
        if not bootstrap:
            raise ValueError('first 404 requires explicit controller bootstrap')
    else:
        old = checked_board(served, now=now)
        if timestamp(board['generated_at']) <= timestamp(old['generated_at']):
            raise ValueError('artifact generation must be newer than the served board')
    return board


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--artifact', type=Path, help='exact downloaded github-pages artifact.tar')
    inputs.add_argument('--board', type=Path, help='local snapshot for post-build freshness check only')
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--bootstrap', action='store_true', help='controller-authorized first publication; only excuses HTTP 404')
    args = parser.parse_args(argv)
    try:
        if args.board:
            if args.bootstrap:
                raise ValueError('bootstrap is only for predeploy artifact checks')
            info = args.board.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_JSON:
                raise ValueError('invalid snapshot file')
            data = args.board.read_bytes()
            now = datetime.now(timezone.utc)
            board = checked_board(data, now=now, fresh=True)
            if board['source_commit'] != args.source_commit or not SHA.fullmatch(args.source_commit):
                raise ValueError('snapshot source differs from trusted checkout')
        else:
            data = read_artifact(args.artifact)
            source = current_source()
            if source != args.source_commit:
                raise ValueError('workflow source differs from current default branch')
            served = served_board()
            board = check_publication(data, served, current_source=source,
                                      now=datetime.now(timezone.utc), bootstrap=args.bootstrap)
        checked_board(board, now=datetime.now(timezone.utc), fresh=True)
        print('Fresh board checked: ' + board['generated_at'])
        return 0
    except (ValueError, OSError) as exc:
        print('Predeploy refused: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
