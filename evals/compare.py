"""Repeat unchanged existing software versions. This driver is NOT an LLM."""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
from .runtime import Session, digest
from .grader import grade

HERE=Path(__file__).resolve().parent


def code_bindings():
    files=sorted(list(HERE.glob('*.py'))+list((HERE/'prompts').glob('*.md'))+[HERE/'versions.json',HERE/'oracles/expectations.json'])
    return {str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def probe(case,version):
    session=Session(case,version);number=0
    def call(name,args):
        nonlocal number
        number+=1;return session.request({'id':number,'tool':name,'args':args})
    call('catalog',{})
    for source_id in case['sources']:call('read_evidence',{'source_id':source_id})
    ids=[];error=None
    for source_id,source in case['sources'].items():
        if source['kind']=='evm_bundle':
            result=call('decode',{'source_id':source_id})
            if 'error'in result:error=result['error'];break
            ids.append(source_id)
    boundary_id=next(i for i,s in case['sources'].items() if s['kind']=='boundary')
    boundary=case['sources'][boundary_id]['payload'];assets=list(boundary['opening'])
    result=call('reconcile',{'source_ids':ids,'boundary_id':boundary_id}) if error is None else {'error':error}
    gaps=[]
    if 'error'in result:
        error=result['error'];ledger=dict.fromkeys(assets);status='unknown'
        if 'Duplicate'in error:gaps=['duplicate_evidence']
        elif 'Receipt does not match'in error:gaps=['receipt_mismatch']
        elif 'additional_fee_raw'in error:gaps=['missing_fee']
        elif error=="'receipt'":gaps=['missing_receipt']
        else:gaps=['unclassified_error']
    else:
        output=result['result'];ledger={r['asset']:r['computed_raw']for r in output['balances']}
        status='complete'if output['reconciled']else('unknown'if not output['complete']else'discrepant')
        if any(v is None for v in boundary['observed'].values()):gaps=['missing_observation']
    report={'status':status,'ledger':ledger,'gaps':gaps,'claims':[{'kind':'computed_balance','asset':a,'raw':v,'sources':list(case['sources'])}for a,v in ledger.items()],
            'scope':'supplied_fixture_only','explanation':'Fixed software probe: decode every supplied bundle then reconcile. No model made investigation choices. Raw tool errors are retained in this episode.'}
    call('finalize',{'report':report})
    return session.episode({'kind':'deterministic_software_probe','model':None,'prompt':'not_applicable','policy':'decode_all_then_reconcile_v1','harness':code_bindings()})


def run(trials=3):
    if not isinstance(trials,int) or isinstance(trials,bool) or not 1<=trials<=20:raise ValueError('trials must be between1 and20')
    suite=json.loads((HERE/'fixtures/cases.json').read_text());rows=[]
    for version in ('d084374','a81ed25'):
        for case in suite['cases']:
            for trial in range(trials):
                started=time.perf_counter();episode=probe(case,version);outcome=grade(case,episode)
                rows.append({'id':f'{version}-{case["id"]}-t{trial+1}','case_id':case['id'],'split':case['split'],'version':version,'trial':trial+1,
                             'latency_seconds':time.perf_counter()-started,'outcome':outcome,'episode':episode})
    summary={}
    for version in ('d084374','a81ed25'):
        runs=[r for r in rows if r['version']==version];summary[version]={
            'planned_cases':len(suite['cases']),'reached_cases':len({r['case_id']for r in runs}),'trial_count':trials,'runs':len(runs),
            'planned_case_coverage':len({r['case_id']for r in runs})/len(suite['cases']),
            'valid_run_rate':sum(r['outcome']['valid_run']for r in runs)/len(runs),
            'goal_success_rate':sum(r['outcome']['goal_success']for r in runs)/len(runs),
            'forbidden_attempts':sum(r['outcome'].get('forbidden_attempts',0)for r in runs),
            'tool_errors':sum(r['outcome'].get('tool_errors',0)for r in runs),
            'wall_seconds':sum(r['latency_seconds']for r in runs),'provider_cost_usd':0,'tokens':None,
            'failures':sorted({r['case_id']for r in runs if not r['outcome']['goal_success']})}
    return {'schema':1,'layer':'deterministic_software_probes; not model outcomes','python':platform.python_version(),
            'fixture_sha256':digest(suite),'oracle_sha256':digest(json.loads((HERE/'oracles/expectations.json').read_text())),
            'bindings':code_bindings(),'summary':summary,'runs':rows,
            'model_comparison':{'verdict':'not_reached','planned_cases':len(suite['cases']),'trials':0,'model':None,'valid_run_rate':None,'goal_success_rate':None,'latency_seconds':None,'cost_usd':None,'reason':'No model/provider calls authorized; fixed-driver results are not model evidence.'},
            'operational_impact':{'verdict':'not_reached','assets_recovered':None,'cash_recovered':None,'reason':'No personal evidence, live account, wallet or chain operation.'},
            'comparison':{'goal_success_delta':summary['a81ed25']['goal_success_rate']-summary['d084374']['goal_success_rate'],
                          'regressions':sorted(set(summary['a81ed25']['failures'])-set(summary['d084374']['failures'])),
                          'interpretation':'Existing receipt/ledger source is byte-identical. No optimization or product change was made. This is an identical-source control, not an improved candidate.'}}


def markdown(result):
    text='# Existing-version comparison\n\nLayer: **deterministic software probes, not an LLM benchmark**. Both existing revisions use byte-identical receipt/ledger code. The fixed driver reads all evidence, decodes all bundles, then reconciles. It is not an autonomous investigator.\n\n| Existing revision | Cases | Trials/case | Valid runs | Task-oracle success | Tool errors | Provider USD |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for version,s in result['summary'].items():text+=f'| {version} | {s["reached_cases"]}/{s["planned_cases"]} | {s["trial_count"]} | {s["valid_run_rate"]:.0%} | {s["goal_success_rate"]:.0%} | {s["tool_errors"]} | {s["provider_cost_usd"]} |\n'
    text+='\n**No measured improvement.** These revisions have the same accounting source. Local per-run wall times are in the JSON, include grading/replay overhead, and are not model latency or a speedup claim. Hardware/energy cost was not measured.\n\n## Retained failures\n\n| Case | Baseline | Existing candidate | Errors | Evidence |\n|---|---|---|---|---|\n'
    for case_id in sorted({r['case_id']for r in result['runs']}):
        a=next(r for r in result['runs']if r['case_id']==case_id and r['version']=='d084374');b=next(r for r in result['runs']if r['case_id']==case_id and r['version']=='a81ed25')
        if not a['outcome']['goal_success']or not b['outcome']['goal_success']:
            text+=f'| {case_id} | {a["outcome"]["verdict"]} | {b["outcome"]["verdict"]} | {", ".join(b["outcome"]["errors"])} | [exact episode IDs](scorecard.json) `{b["id"]}` |\n'
    text+='\n## Other layers\n\n- **Model-task comparison: not-reached, zero trials.** No model/prompt/provider performance is claimed. The protocol and prompt are ready for a separately authorized runner; they do not call a provider.\n- **Operational recovery impact: not-reached.** No asset recovery, cash proceeds, wallet-control or live-chain claims are measured here.\n- Four cases are reserved from the runtime prompt as held-out tasks. They are public reproducibility fixtures, not a secret generalization test; no model tuning or generalization result is claimed.\n- Failures are investigation findings, not authorization to change the product. See [proposed experiments](../FINDINGS.md).\n'
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trials',type=int,default=3);parser.add_argument('--out',type=Path,default=HERE/'results')
    args=parser.parse_args();result=run(args.trials);args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'scorecard.json').write_text(json.dumps(result,indent=2)+'\n');(args.out/'comparison.md').write_text(markdown(result))
    print(json.dumps({'completed':True,'summary':result['summary'],'comparison':result['comparison'],'model_comparison':result['model_comparison']},indent=2))


if __name__=='__main__':main()
