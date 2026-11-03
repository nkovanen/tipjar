#!/usr/bin/env python3
"""Source-only public submission observations for human review, never enrollment."""
import argparse
import hashlib
import os
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_contribute import core, receipts
from tools import tipjar_board as board

CONTROLLER_ID = 1444643470
BODY_LIMIT = 256 * 1024
OUTPUT_LIMIT = 2 * 1024 * 1024
CHECKLIST = (
    'Review the saved untrusted body: it names the explicit PR, opts in its identity/proof/merge/size data, and has no withdrawal or contradiction.',
    'Review explicit agent assistance and no control of the receiving repository/organization/project; owner inequality does not prove independence.',
    'Review reverts, duplicate/split/farming concerns, authenticated owner opt-outs, exclusions and all other consent entries for this PR.',
    'Check numeric repo/PR, number/author/name and submission identity/digest conflicts; validate the complete proposed registry offline.',
    'Refresh intake before acceptance; authorize registry edits/publication separately; the normal collector must re-read pins before counting.',
)


def require(condition):
    if not condition:
        raise core.ProtocolError('intake_refused', 'Submission intake refused; human review remains required.')


class IntakeClient:
    """Exact invocation sequence; gh's internal HTTP redirects remain inherited."""
    def __init__(self, submission, reference, client=None, *, clock=None):
        require(type(submission) is int and 1 <= submission <= 9999999999)
        repository, number = core.parse_issue(reference)
        controller = 'repos/' + board.CONTROLLER
        issue = f'{controller}/issues/{submission}'
        repo = 'repos/' + repository
        self.routes = (controller, issue, repo, f'{repo}/pulls/{number}', issue, repo, controller)
        self.reads = board.BudgetClient(client, limit=7, clock=clock)
        self.position = 0

    def request(self, endpoint, attempts=1):
        return self.request_once(endpoint)

    def request_once(self, endpoint):
        require(self.position < 7 and endpoint == self.routes[self.position])
        self.position += 1
        return self.reads.request_once(endpoint)


def issue_observation(value, number):
    require(isinstance(value, dict) and 'pull_request' not in value)
    require(type(value.get('id')) is int and 0 < value['id'] <= board.SAFE)
    require(type(value.get('number')) is int and value['number'] == number)
    require(value.get('html_url') == f'https://github.com/{board.CONTROLLER}/issues/{number}')
    actor = value.get('user')
    require(isinstance(actor, dict) and actor.get('type') == 'User')
    require(type(actor.get('id')) is int and 0 < actor['id'] <= board.SAFE)
    body = value.get('body')
    require(isinstance(body, str))
    try:
        require(len(body.encode('utf-8')) <= BODY_LIMIT)
    except UnicodeError:
        raise core.ProtocolError('intake_refused', 'Submission body is not bounded UTF-8.') from None
    return (value['id'], number, value['html_url'], actor['id'], body)


def intake(submission: int, reference: str, client=None, *, clock=None) -> dict:
    clock = clock or board.utcnow
    guard = IntakeClient(submission, reference, client, clock=clock)
    controller = guard.request_once(guard.routes[0])
    identity = board._public_meta(controller, CONTROLLER_ID, board.CONTROLLER)
    first = issue_observation(guard.request_once(guard.routes[1]), submission)
    receipt = receipts.observe(reference, guard)
    metadata, pr = guard.reads.last_repository, guard.reads.last_pr
    repo, observed = receipt['repository'], receipt['pull_request']
    pins = dict(repository_id=repo['id'], repository=repo['full_name'],
                pull_request_id=observed['id'], number=observed['number'], author_id=observed['author']['id'],
                submission=dict(controller_repository=board.CONTROLLER, controller_repository_id=CONTROLLER_ID,
                                issue_id=first[0], number=submission,
                                body_sha256=hashlib.sha256(first[4].encode('utf-8')).hexdigest()))
    require(all(type(pins[key]) is int and 0 < pins[key] <= board.SAFE
                for key in ('repository_id', 'pull_request_id', 'number', 'author_id')))
    require(first[3] == pins['author_id'])
    times = [event[1] for event in guard.reads.events]
    board._tip(pins, receipt, metadata, pr,
               dict(controller=times[0], consent=times[1], repository=times[2], pull_request=times[3]))
    require(issue_observation(guard.request_once(guard.routes[4]), submission) == first)
    require(board._public_meta(guard.request_once(guard.routes[5]), repo['id'], repo['full_name']) ==
            board._public_meta(metadata, repo['id'], repo['full_name']))
    require(board._public_meta(guard.request_once(guard.routes[6]), CONTROLLER_ID, board.CONTROLLER) == identity)
    require(guard.position == 7)
    checks = [event[1] for event in guard.reads.events]
    generated = board.iso(clock())
    require(all(board.timestamp(check) <= board.timestamp(generated) for check in checks))
    result = dict(format='tipjar-board-intake/1', status='review-required', generated_at=generated,
                  checks=checks, pins=pins, submission_body=first[4], review_checklist=list(CHECKLIST))
    require(len(board.encode(result) + b'\n') <= OUTPUT_LIMIT)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Submission intake usage error.\n')


def submission_number(value):
    try:
        return core.parse_issue(board.CONTROLLER + '#' + value)[1]
    except core.ProtocolError:
        raise argparse.ArgumentTypeError('Invalid submission number') from None


def reference_value(value):
    try:
        core.parse_issue(value)
        return value
    except core.ProtocolError:
        raise argparse.ArgumentTypeError('Invalid pull request reference') from None


def destination(path):
    """Retain a symlink-free POSIX parent descriptor throughout the observations."""
    require(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW'))
    path = Path(path).absolute()
    require(bool(path.name) and path.name not in ('.', '..'))
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        try:
            os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return parent, path.name
        raise core.ProtocolError('intake_output', 'Output already exists.')
    except BaseException:
        os.close(parent)
        raise


def save(parent, name, data):
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    identity = os.fstat(descriptor)
    try:
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, 'wb')
        descriptor = None
        with handle:
            require(handle.write(data) == len(data))
            handle.flush()
    except BaseException:
        try:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                os.unlink(name, dir_fd=parent)
        except FileNotFoundError:
            pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--submission', required=True, type=submission_number)
    parser.add_argument('--pull-request', required=True, type=reference_value)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        parent, name = destination(args.output)
        try:
            candidate = intake(args.submission, args.pull_request)
            data = board.encode(candidate) + b'\n'
            require(len(data) <= OUTPUT_LIMIT)
            save(parent, name, data)
        finally:
            os.close(parent)
        print('review-required')
        return 0
    except (core.ProtocolError, OSError, ValueError):
        print('Submission intake refused: invalid, unavailable, unsafe or existing output.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
