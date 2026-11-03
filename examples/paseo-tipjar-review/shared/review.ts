import { Ajv2020 } from 'ajv/dist/2020.js';
import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex, utf8ToBytes } from '@noble/hashes/utils';
import schema from './authorization-request.schema.json';

type Json = null | boolean | number | string | Json[] | { [key:string]: Json };
export interface UnsignedRequest {
  kind: 'agent-contrib/external-authorization-request';
  request_version: '0.1'; issued: false; ready_for_issuance: false;
  stage: 'implementation' | 'draft'; complete: boolean;
  contract_sha256: string;
  bindings: { [key:string]: Json; contract_sha256:string; invitation_basis:string;
    undeclared_acknowledged_required:boolean; source_repository:string; head_repository:string };
  requested_actions: string[]; policy_inventories: Json[];
  stage_blockers: { implementation:string[]; draft:string[]; published:string[] };
  errors:string[]; evidence_errors:string[]; unresolved_fields:string[];
}
const validate = new Ajv2020({strict:false, allErrors:false}).compile(schema);

// Deliberately narrower than JSON numbers: Python/JS canonical hashes agree only
// within this example's integer domain. Never silently round GitHub numeric IDs.
export function parseStrict(text:string): Json {
  if (text.length > 1048576 || utf8ToBytes(text).length > 1048576) throw Error('Input exceeds 1 MiB UTF-8');
  let i = 0;
  const ws = () => { while (/[ \t\r\n]/.test(text[i] ?? '') && i < text.length) i++; };
  const fail = (): never => { throw Error('Invalid strict JSON; safe integer tokens only, depth at most 64'); };
  function string(): string {
    const start = i++;
    while (i < text.length) {
      if (text[i] === '\\') { i += 2; continue; }
      if (text[i++] === '"') {
        const value:string = JSON.parse(text.slice(start,i));
        for (let k=0;k<value.length;k++) {
          const unit=value.charCodeAt(k);
          if (unit>=0xd800 && unit<=0xdbff) {
            const next=value.charCodeAt(++k);
            if (!(next>=0xdc00 && next<=0xdfff)) fail();
          } else if (unit>=0xdc00 && unit<=0xdfff) fail();
        }
        return value;
      }
    }
    return fail();
  }
  function value(depth:number): Json {
    if (depth>64) fail();
    ws(); const ch=text[i];
    if (ch==='"') return string();
    if (ch==='{' || ch==='[') {
      const object=ch==='{'; const end=object?'}':']'; i++; ws();
      const result:Record<string,Json> = Object.create(null);
      const array:Json[]=[];
      if (text[i]===end) {i++;return object?result:array;}
      while (i<text.length) {
        ws();
        if (object) {
          if (text[i]!=='"') fail();
          const key=string(); ws();
          if (Object.hasOwn(result,key) || text[i++]!==':') fail();
          result[key]=value(depth+1);
        } else array.push(value(depth+1));
        ws(); const sep=text[i++];
        if (sep===end) return object?result:array;
        if (sep!==',') fail();
      }
      return fail();
    }
    for (const [token,result] of [['true',true],['false',false],['null',null]] as const) {
      if (text.startsWith(token,i)) {i+=token.length;return result;}
    }
    const token=text.slice(i).match(/^-?(?:0|[1-9][0-9]*)/)?.[0];
    if (!token || token==='-0' || !Number.isSafeInteger(Number(token))) return fail();
    i+=token.length; return Number(token);
  }
  const result=value(0); ws(); if (i!==text.length) fail(); return result;
}

function codepointCompare(a:string,b:string):number {
  const aa=Array.from(a,c=>c.codePointAt(0)!); const bb=Array.from(b,c=>c.codePointAt(0)!);
  for(let i=0;i<Math.min(aa.length,bb.length);i++) if(aa[i]!==bb[i]) return aa[i]-bb[i];
  return aa.length-bb.length;
}
export function canonical(value:Json):string {
  if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
  if (value!==null && typeof value==='object') return '{'+Object.keys(value).sort(codepointCompare)
    .map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}';
  return JSON.stringify(value);
}
function freeze(value:Json):void {
  if(value!==null && typeof value==='object') { Object.values(value).forEach(freeze); Object.freeze(value); }
}
export function inertJson(value:Json):string {
  // Preserve surrogate pairs when escaping supplementary format characters.
  return JSON.stringify(value,null,2).replace(/[\p{Cc}\p{Cf}\u2028\u2029]/gu,c=>
    c==='\n'?c:c.split('').map(unit=>'\\u'+unit.charCodeAt(0).toString(16).padStart(4,'0')).join(''));
}
export function inspectRequest(original:string) {
  const data=parseStrict(original);
  if (!validate(data) || (data as unknown as UnsignedRequest).kind!=='agent-contrib/external-authorization-request') {
    throw Error('Unsupported unsigned request schema; expected external request 0.1 from the pinned helper');
  }
  const request=data as unknown as UnsignedRequest;
  if (request.contract_sha256!==request.bindings.contract_sha256 ||
      request.bindings.undeclared_acknowledged_required!==(request.bindings.invitation_basis==='explicit-undeclared') ||
      JSON.stringify(request.requested_actions)!==JSON.stringify(request.stage==='implementation'?['implement']:['push_head','create_draft'])) {
    throw Error('Inconsistent unsigned request bindings or actions');
  }
  freeze(data);
  // Escape terminal/bidi/format controls in the preview only. Copy retains original bytes.
  const display=inertJson(data);
  return Object.freeze({request, original, display, requestHash:bytesToHex(sha256(utf8ToBytes(canonical(data))))});
}
export type Snapshot = ReturnType<typeof inspectRequest>;
