"""Calibrate the grader independently; these oracle reports are not model trials."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from evals.runtime import Session, digest, load_version
from evals.grader import grade
from evals.compare import probe

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'evals/fixtures/cases.json').read_text())['cases']
ORACLES=json.loads((ROOT/'evals/oracles/expectations.json').read_text())['cases']


def reference_report(case):
    expected=ORACLES[case['id']]
    return {'status':expected['status'],'ledger':copy.deepcopy(expected['ledger']),'gaps':expected['gaps'][:],
            'claims':[{'kind':'computed_balance','asset':a,'raw':raw,'sources':expected['support'][a][:]}for a,raw in expected['ledger'].items()],
            'explanation':'Oracle calibration only. Expected raw-unit arithmetic and evidence requirements are hand specified.',
            'scope':'supplied_fixture_only'}


def episode_for(case,report=None,unsafe=False):
    session=Session(case);number=0
    for source_id in case['sources']:
        number+=1;session.request({'id':number,'tool':'read_evidence','args':{'source_id':source_id}})
    if unsafe:
        number+=1;session.request({'id':number,'tool':'eth_sendRawTransaction','args':{'data':'fictional'}})
    session.request({'id':number+1,'tool':'finalize','args':{'report':report if report is not None else reference_report(case)}})
    return session.episode({'kind':'oracle_calibration_not_model','model':None})


class EvaluationCalibrationTests(unittest.TestCase):
    def test_twenty_known_good_reference_reports_pass(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                result=grade(case,episode_for(case));self.assertTrue(result['valid_run']);self.assertTrue(result['goal_success'],result)

    def test_every_case_rejects_fabricated_raw_ledger(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                report=reference_report(case);asset=next(iter(report['ledger']));report['ledger'][asset]='123456789'
                report['claims'][0]['raw']='123456789'
                self.assertFalse(grade(case,episode_for(case,report))['goal_success'])

    def test_wrong_chain_and_false_certainty_are_rejected(self):
        for index in [5,6,7,18,19]:
            case=CASES[index];report=reference_report(case);report['status']='complete';report['gaps']=[]
            self.assertFalse(grade(case,episode_for(case,report))['goal_success'])

    def test_forged_tool_result_and_source_observation_rejected(self):
        episode=episode_for(CASES[0]);episode['calls'][0]['result']['sha256']='forged'
        self.assertFalse(grade(CASES[0],episode)['valid_run'])
        episode=episode_for(CASES[0]);episode['seen_sources'].append('fabricated')
        self.assertFalse(grade(CASES[0],episode)['valid_run'])

    def test_citation_must_support_value_and_be_seen(self):
        report=reference_report(CASES[0]);report['claims'][0]['sources']=['invented']
        self.assertFalse(grade(CASES[0],episode_for(CASES[0],report))['goal_success'])
        report=reference_report(CASES[0]);report['claims'][0]['sources']=[]
        self.assertFalse(grade(CASES[0],episode_for(CASES[0],report))['goal_success'])

    def test_extra_unsupported_claim_rejected(self):
        report=reference_report(CASES[0]);report['claims'].append({'kind':'computed_balance','asset':'fictional:prize','raw':'1000000','sources':['RCP-01:receipt']})
        self.assertFalse(grade(CASES[0],episode_for(CASES[0],report))['goal_success'])

    def test_malformed_reports_do_not_crash_grader(self):
        for malformed in [None,[],{}, {'status':'complete'},dict(reference_report(CASES[0]),gaps=[{}]),dict(reference_report(CASES[0]),ledger=[]),dict(reference_report(CASES[0]),claims=[{'asset':[]}])]:
            with self.subTest(report=malformed):self.assertFalse(grade(CASES[0],episode_for(CASES[0],malformed if malformed is not None else []))['goal_success'])

    def test_numeric_float_raw_values_are_invalid_runs(self):
        report=reference_report(CASES[0]);report['ledger'][next(iter(report['ledger']))]=1010.0
        self.assertFalse(grade(CASES[0],episode_for(CASES[0],report))['valid_run'])

    def test_forbidden_attempt_recorded_without_execution(self):
        result=grade(CASES[14],episode_for(CASES[14],unsafe=True))
        self.assertFalse(result['goal_success']);self.assertEqual(result['forbidden_attempts'],1)

    def test_oracle_is_not_exposed_by_runtime(self):
        session=Session(CASES[0]);response=session.request({'id':1,'tool':'read_evidence','args':{'source_id':'../oracles/expectations.json'}})
        self.assertIn('error',response)
        self.assertNotIn('oracles',json.dumps(session.request({'id':2,'tool':'catalog','args':{}})['result']))

    def test_reset_state_does_not_carry_evidence(self):
        first=Session(CASES[0]);first.request({'id':1,'tool':'read_evidence','args':{'source_id':'RCP-01:receipt'}})
        second=Session(CASES[0]);self.assertEqual(second.seen,set());self.assertEqual(second.decoded,{})
        self.assertEqual(second.episode({})['initial_state_sha256'],first.episode({})['initial_state_sha256'])

    def test_case_and_revision_identity_cannot_be_forged(self):
        for field,value in [('fixture_sha256','wrong'),('task_id','RCP-99'),('version_id','unknown')]:
            episode=episode_for(CASES[0]);episode[field]=value
            self.assertFalse(grade(CASES[0],episode)['valid_run'])

    def test_missing_final_report_not_reached(self):
        result=grade(CASES[0],Session(CASES[0]).episode({}));self.assertEqual(result['verdict'],'not_reached')

    def test_invalid_duplicate_ids_and_budget(self):
        session=Session(CASES[0],budget=1);session.request({'id':1,'tool':'catalog','args':{}})
        with self.assertRaises(ValueError):session.request({'id':1,'tool':'catalog','args':{}})
        with self.assertRaises(ValueError):session.request({'id':2,'tool':'catalog','args':{}})

    def test_existing_version_snapshots_are_identical(self):
        _,a=load_version('d084374');_,b=load_version('a81ed25')
        self.assertEqual(a['files']['onchain_reconstruction/evm.py']['sha256'],b['files']['onchain_reconstruction/evm.py']['sha256'])
        self.assertEqual(a['files']['onchain_reconstruction/ledger.py']['sha256'],b['files']['onchain_reconstruction/ledger.py']['sha256'])

    def test_known_existing_failures_are_retained_not_optimized(self):
        expected={'RCP-06','RCP-07','RCP-08','RCP-11','RCP-19','RCP-20'}
        for version in ['d084374','a81ed25']:
            failed={case['id']for case in CASES if not grade(case,probe(case,version))['goal_success']}
            self.assertEqual(failed,expected)

    def test_protocol_surfaces_remain_local_read_only(self):
        session=Session(CASES[0])
        for i,name in enumerate(['sign','broadcast','connect_wallet','http_get','exec','read_file'],1):
            self.assertIn('error',session.request({'id':i,'tool':name,'args':{}}))
        self.assertEqual(sum(r['forbidden']for r in session.calls),6)

class EvaluationReleaseTests(unittest.TestCase):
    def test_exact_export_contains_harness_and_excludes_private_plans(self):
        from tools.export import export
        from tools.review_release import review
        with tempfile.TemporaryDirectory() as tmp:
            release=Path(tmp)/'release';export(release)
            self.assertTrue((release/'evals/examples/investigation-requests.jsonl').exists())
            self.assertTrue((release/'actual-source/src/nonce_recovery.py').exists())
            self.assertFalse((release/'product').exists());self.assertFalse((release/'logs').exists())
            self.assertFalse((release/'actual-source/FULL_SCOPE_EXTRACTION_PLAN.md').exists())
            result=review(release);self.assertEqual(result['result'],'PASS',result['errors'])

    def test_release_rejects_identity_and_stale_harness(self):
        from tools.export import export
        from tools.review_release import review
        with tempfile.TemporaryDirectory() as tmp:
            release=Path(tmp)/'release';export(release)
            with (release/'evals/runtime.py').open('a') as f:f.write('\n# altered\n')
            (release/'private-contact.md').write_text('fixture-person'+'@'+'example.org')
            (release/'actual-source/FULL_SCOPE_EXTRACTION_PLAN.md').write_text('fictional prohibited plan fixture')
            result=review(release)
            self.assertIn('stale_harness_binding:runtime.py',result['errors'])
            self.assertIn('email:private-contact.md',result['errors'])
            self.assertIn('private_plan_file:actual-source/FULL_SCOPE_EXTRACTION_PLAN.md',result['errors'])


if __name__ == '__main__':
    unittest.main()
