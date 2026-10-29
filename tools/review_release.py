"""Review the exact allowlisted export, synthetic identities and source integrity."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def review(root):
    root=Path(root);errors=[];files=[]
    forbidden_parts={'.git','cache','output','private','private-review','product','logs','actual-source-candidate'}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():errors.append('symlink:'+str(path.relative_to(root)));continue
        if not path.is_file() or '__pycache__' in path.parts:continue
        relative=str(path.relative_to(root))
        if set(path.relative_to(root).parts)&forbidden_parts:errors.append('forbidden_path:'+relative)
        text=path.read_text()
        # Match actual values, not generic documentation or detector source literals.
        if re.search(r'/(?:Users|home|var/folders)/[A-Za-z0-9_.-]+/',text):errors.append('local_path:'+relative)
        emails=re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',text)
        if any(not email.endswith('.invalid') for email in emails):errors.append('email:'+relative)
        if re.search(r'(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,})',text):errors.append('credential_pattern:'+relative)
        for value in re.findall(r'0x[0-9a-fA-F]{40}(?![0-9a-fA-F])',text):
            if len(set(value[2:].lower()))!=1:errors.append('non_synthetic_address:'+relative)
        if path.name == 'FULL_SCOPE_EXTRACTION_PLAN.md':errors.append('private_plan_file:'+relative)
        files.append({'path':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest=json.loads((root/'evals/versions.json').read_text())
    for version in manifest['versions'].values():
        for record in version['files'].values():
            if hashlib.sha256((root/'evals'/record['snapshot']).read_bytes()).hexdigest()!=record['sha256']:errors.append('snapshot_hash')
    provenance=json.loads((root/'actual-source/provenance.json').read_text())
    for source in provenance['sources']:
        if hashlib.sha256((root/'actual-source'/source['candidate']).read_bytes()).hexdigest()!=source['candidate_sha256']:errors.append('original_component_hash')
    score=json.loads((root/'evals/results/scorecard.json').read_text())
    if len(score['runs'])!=120 or score['model_comparison']['trials']!=0:errors.append('unexpected_scorecard_scope')
    for name, expected in score['bindings'].items():
        if hashlib.sha256((root/'evals'/name).read_bytes()).hexdigest()!=expected:errors.append('stale_harness_binding:'+name)
    for run in score['runs']:
        if run['episode']['bindings'].get('kind')!='deterministic_software_probe' or run['episode']['bindings'].get('model') is not None:errors.append('non_software_receipt')
    return {'result':'PASS'if not errors else'FAIL','errors':sorted(set(errors)),'files':files,
            'boundary':'Pattern/source review of this exact export; not a universal secret detector. No real model or financial evidence is permitted.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args();result=review(args.directory)
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['result']=='PASS'else 1)
