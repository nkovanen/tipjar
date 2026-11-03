"""Packaged JSON Schemas (draft 2020-12 subset) for each command's JSON output.

Every object states additionalProperties, so standard validators and the bundled
validator agree. A shape change bumps VERSION; output values never carry it."""
import importlib.resources
import json

from . import core

VERSION = '4'
SCHEMAS = ('badge', 'audit', 'authorization-request', 'card', 'dependencies', 'discover', 'drift', 'error', 'evidence-init', 'feedback', 'find', 'init', 'inspect', 'instructions', 'jar', 'jar-check',
           'impact', 'receipt', 'lint', 'ownership', 'pr-body', 'prepare', 'scope-check', 'session', 'skill', 'verify')
DIRECTORY = f'schemas/output/{VERSION}'


def output_schema(name, version=None):
    if name not in SCHEMAS or version is not None and version not in ('1','2','3','4'):
        raise core.ProtocolError('unsupported_schema', 'Unsupported output schema')
    path = f'schemas/output/{version or VERSION}/{name}.schema.json'
    resource = importlib.resources.files('agent_contribute').joinpath(path)
    if not resource.is_file():
        raise core.ProtocolError('unsupported_schema', 'Unsupported output schema in this version')
    return json.loads(resource.read_text('utf-8'))
