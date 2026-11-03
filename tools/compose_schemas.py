#!/usr/bin/env python3
"""Compose new output artifacts from immutable output/3 and explicit invitation definitions."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'agent_contribute/schemas/output'


def obj(properties, required=None):
    return dict(type='object', properties=properties, required=list(properties) if required is None else required, additionalProperties=False)


def invitation(legacy):
    common = copy.deepcopy(legacy['properties'])
    common.update(repository_id={'type':['integer','null'], 'minimum':1},
                  tree_sha=copy.deepcopy(common['commit']), manifest_present={'type':['boolean','null']},
                  source_kind={'enum':['manifest','readme','absent','unknown']},
                  badge={'anyOf':[obj({'protocol':{'const':'readme-welcome/1'}, 'repository':{'type':'string','minLength':1,'maxLength':200}}), {'type':'null'}]})
    common['path'] = {'enum':['.tipjar.json','README.md',None]}
    variants = []
    def add(values, nonnull=()):
        props = copy.deepcopy(common)
        for key, value in values.items(): props[key] = {'const':value}
        for key in nonnull:
            field = props[key]
            if isinstance(field.get('type'),list): field['type'] = [v for v in field['type'] if v != 'null']
        variants.append(obj(props, [k for k in props if k != 'api_budget']))
    identity = ('repository_id','default_branch','commit','tree_sha')
    for state in ('welcome','closed'):
        props = dict(source_kind='manifest', path='.tipjar.json', manifest_present=True, state=state,
                     complete=True, badge=None, errors=[])
        add(props, identity + ('blob_sha','sha256'))
        variants[-1]['properties']['manifest'] = copy.deepcopy(legacy['$defs']['tipjar_manifest'])
        variants[-1]['properties']['manifest']['properties']['status'] = {'const':state}
    for state in ('welcome','undeclared'):
        add(dict(source_kind='readme',path='README.md',manifest_present=False,state=state,complete=True,manifest=None,errors=[],
                 **({'badge':None} if state == 'undeclared' else {})), identity + ('blob_sha','sha256'))
        if state == 'welcome': variants[-1]['properties']['badge'] = common['badge']['anyOf'][0]
    add(dict(source_kind='absent',path=None,manifest_present=False,state='undeclared',complete=True,manifest=None,badge=None,blob_sha=None,sha256=None,errors=[]), identity)
    # Failure variants keep verified metadata/selection and never imply completeness.
    base = dict(state='unknown',complete=False,manifest=None,badge=None)
    for stage in ('identity','metadata','commit','tree'):
        values = dict(base,source_kind='unknown',path=None,manifest_present=None,blob_sha=None,sha256=None)
        nonnull = ()
        if stage == 'identity': values.update(repository_id=None,default_branch=None,commit=None,tree_sha=None)
        if stage == 'metadata': values.update(commit=None,tree_sha=None); nonnull=identity[:2]
        if stage == 'commit': values.update(tree_sha=None); nonnull=identity[:3]
        if stage == 'tree': nonnull=identity
        add(values,nonnull)
        variants[-1]['properties']['errors']['minItems']=1
    for kind,path,present in (('manifest','.tipjar.json',True),('readme','README.md',False)):
        for stage in ('selection','blob','bytes'):
            values=dict(base,source_kind=kind,path=path,manifest_present=present)
            nonnull=identity
            if stage == 'selection': values.update(blob_sha=None,sha256=None)
            if stage == 'blob': values.update(sha256=None); nonnull+=('blob_sha',)
            if stage == 'bytes': nonnull+=('blob_sha','sha256')
            add(values,nonnull)
            variants[-1]['properties']['errors']['minItems']=1
    return {'anyOf':variants}


def bounded(node):
    if isinstance(node, list): return [bounded(v) for v in node]
    if not isinstance(node,dict): return node
    node={k:bounded(v) for k,v in node.items()}
    if 'pattern' in node:
        node.setdefault('maxLength',64)
        if node['pattern'].endswith('$'): node['pattern']=node['pattern'][:-1]+'(?![\\s\\S])'
    return node


def compose():
    oldjar = json.loads((OUT/'3/jar.schema.json').read_text())
    newjar = invitation(oldjar)
    for path in sorted((OUT/'3').glob('*.json')):
        value = json.loads(path.read_text())
        def walk(node):
            if isinstance(node,list): return [walk(v) for v in node]
            if not isinstance(node,dict): return node
            props = node.get('properties',{})
            if {'jar_state','jar_sha256','inventory_format','invitation_basis'} <= props.keys():
                return bounded(json.loads((ROOT/'agent_contribute/schemas/0.3/task.schema.json').read_text())['properties']['source_review'])
            if set(props) == {'repository_id','inventory_format','inventory_sha256'} and props['inventory_format'].get('const') == 3:
                node = copy.deepcopy(node); node['properties']['inventory_format']['const'] = 4
                return node
            if {'manifest','blob_sha','fetched_at','notice','state','complete'} <= props.keys():
                return {'anyOf':[copy.deepcopy(node),{'$ref':'#/$defs/invitation_v2'}]}
            return {k:walk(v) for k,v in node.items()}
        result = walk(value)
        if path.stem == 'jar.schema':
            result = copy.deepcopy(newjar)
        result.update({'$schema':value['$schema'], '$id':value['$id'].replace(':3:',':4:')})
        if path.name == 'jar.schema.json': result['description'] = 'Pinned versioned invitation source; grants no authority.'
        result['$defs'] = copy.deepcopy(value.get('$defs',{}))
        # Rewrite nested jar reports in definitions as well.
        result['$defs'] = walk(result['$defs'])
        if path.name != 'jar.schema.json' and '#/$defs/invitation_v2' in json.dumps(result):
            result['$defs']['invitation_v2'] = copy.deepcopy(newjar)
            for key in ('api_budget','rate_limit_snapshot'):
                result['$defs'].setdefault(key, copy.deepcopy(oldjar['$defs'][key]))
        if path.name == 'drift.schema.json':
            review = result['properties']['tipjar']['properties']['reviewed']
            for name in ('source_kind','path','blob_sha','manifest_present'):
                review['properties'][name] = copy.deepcopy(oldjar['properties'].get(name, {'type':'string'}))
            review['properties'].update(source_kind={'enum':['manifest','readme','absent']},path={'enum':['.tipjar.json','README.md',None]},manifest_present={'type':'boolean'})
            review['required'] += ['source_kind','path','blob_sha','manifest_present']
        if path.name == 'find.schema.json':
            result['properties']['format']['const'] = 'find-jars-report/2'
            search = result['properties'].pop('search')
            search['properties']['per_page']['const'] = 5
            search['properties']['errors'] = {'type':'array','items':{'type':'string','maxLength':2147483647},'maxItems':2147483647}
            search['required'].append('errors')
            result['properties']['searches'] = dict(type='array',minItems=2,maxItems=2,items=search)
            result['required'] = ['searches' if k == 'search' else k for k in result['required']]
        yield OUT/'4'/path.name, result
    yield OUT/'4/badge.schema.json', {'$schema':oldjar['$schema'],'$id':'urn:agent-contrib:output:4:badge', 'description':'Offline repository-scoped official README invitation snippet; grants no authority.', **obj({k:{'type':'string','minLength':1,'maxLength':2000} for k in ('repository','snippet','notice')})}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    bad=[]
    for path,value in compose():
        data=json.dumps(value,indent=2,ensure_ascii=False)+'\n'
        if args.check:
            if not path.exists() or path.read_text()!=data: bad.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
    if bad: parser.exit(1,'Schema composition differs: '+', '.join(bad)+'\n')

if __name__=='__main__': main()
