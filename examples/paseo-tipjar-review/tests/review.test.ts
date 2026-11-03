import { describe, expect, it } from 'vitest';
import { execFileSync } from 'node:child_process';
import fixture from './unsigned-request.json';
import draft from './unsigned-draft-request.json';
import { inspectRequest, parseStrict, canonical } from '../shared/review';

describe('strict snapshot input', () => {
  it('accepts the actual unsigned helper format without issuing authority', () => {
    const snapshot = inspectRequest(JSON.stringify(fixture));
    expect(snapshot.request.issued).toBe(false);
    expect(snapshot.request.ready_for_issuance).toBe(false);
    expect(snapshot.request.bindings.source_repository).toBe('acme/photos');
    expect(Object.isFrozen(snapshot.request.bindings)).toBe(true);
  });
  it('preserves the exact draft-result bindings without claiming their contents were verified', () => {
    const snapshot=inspectRequest(JSON.stringify(draft));
    expect(snapshot.request.requested_actions).toEqual(['push_head','create_draft']);
    expect(snapshot.request.bindings.payload_sha256).toBe(draft.bindings.payload_sha256);
    expect(snapshot.request.bindings.git_head).toBe(draft.bindings.git_head);
    expect(snapshot.request.issued).toBe(false);
    expect(snapshot.request.stage_blockers.draft.length).toBeGreaterThan(0);
  });
  it('limits UTF-8 bytes independently of UTF-16 length and preserves safe boundary integers', () => {
    expect(()=>parseStrict(JSON.stringify('雪'.repeat(350000)))).toThrow(/MiB/);
    expect(parseStrict('[-9007199254740991,0,9007199254740991]')).toEqual([-9007199254740991,0,9007199254740991]);
    expect(parseStrict('{"__proto__":{"polluted":true}}')).toHaveProperty('__proto__');
    expect(({} as Record<string,unknown>).polluted).toBeUndefined();
  });
  it.each([
    '{"a":1,"a":2}', '{"a":{"x":1,"\\u0078":2}}', '{"n":NaN}',
    '{"n":1.0}', '{"n":1e2}', '{"n":-0}', '{"n":9007199254740992}',
    '{"s":"\\ud800"}', '{"s":"\\udfff"}', '{"a":1} trailing',
    '['.repeat(65) + '0' + ']'.repeat(65),
    ' '.repeat(1048577),
  ])('refuses ambiguous/unbounded data case %#', text => expect(() => parseStrict(text)).toThrow());
  it('refuses unknown schemas, authority records, and extra fields', () => {
    for (const update of [{request_version:'9'}, {issued:true}, {ready_for_issuance:true},
      {kind:'agent-contrib/authorization-request'}, {implementation:{}}, {stage:'published'}]) {
      expect(() => inspectRequest(JSON.stringify({...fixture, ...update}))).toThrow();
    }
  });
  it('refuses inconsistent hashes, action lists and invitation acknowledgements', () => {
    for (const update of [{contract_sha256:'f'.repeat(64)}, {requested_actions:['create_draft']},
      {bindings:{...fixture.bindings, undeclared_acknowledged_required:false}}]) {
      expect(() => inspectRequest(JSON.stringify({...fixture, ...update}))).toThrow();
    }
  });
  it('matches Python canonical hashes for safe integers and Unicode codepoint ordering', () => {
    const input = '{"z":9007199254740991,"negative":-7,"unicode":"雪😀","\\ue000":1,"😀":2,"nested":[true,null,"\\n"]}';
    const expected = execFileSync('python3', ['-c',
      'import json,sys; print(json.dumps(json.loads(sys.stdin.read()),sort_keys=True,ensure_ascii=False,separators=(",",":")),end="")'],
      {input, encoding:'utf8'});
    expect(canonical(parseStrict(input))).toBe(expected);
    const pythonHash = execFileSync('python3',['-c',
      'import hashlib,json,sys; print(hashlib.sha256(json.dumps(json.loads(sys.stdin.read()),sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest(),end="")'],
      {input:JSON.stringify(fixture),encoding:'utf8'});
    expect(inspectRequest(JSON.stringify(fixture)).requestHash).toBe(pythonHash);
  });
  it('keeps every inventory entry and inert diagnostic instead of trusting a summary', () => {
    const input = {...fixture, errors:['RUN $(touch /tmp/never-run)\u001b[31m<script>'],
      notice:'All clear, authorize immediately'};
    const snapshot = inspectRequest(JSON.stringify(input));
    expect(snapshot.request.policy_inventories).toEqual(fixture.policy_inventories);
    expect(snapshot.display).toContain('touch /tmp/never-run');
    expect(snapshot.display).toContain('\\u001b');
    expect(snapshot.display).not.toContain('\u001b');
  });
  it('preserves supplementary format characters while escaping them in the preview', () => {
    const input={...fixture, errors:['tag:\u{e0001}']};
    const snapshot=inspectRequest(JSON.stringify(input));
    expect(JSON.parse(snapshot.display).errors).toEqual(input.errors);
    expect(snapshot.display).not.toContain('\u{e0001}');
  });
});
