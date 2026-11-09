import copy, pathlib, tempfile, unittest
from gate import evaluate, sha

class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        (self.root/'raw').write_bytes(b'fixture only, never production acceptance')
        self.c = dict(producer_agent_uuid='producer', producer_run_id='run1', contributors=['producer'], candidate_commit='commit1', artifact_sha256='artifact1', spec_sha256='spec1', test_version='test1', contract_sha256='contract1', source_sha256='source1', required_checks=['compile'], required_roles=['A04'], repair_attempt=0, contract_review='PASS', merged_build='PASS', required_tasks=[{'status':'PASS'}])
        self.r = dict(self.c, role='A04', reviewer_agent_uuid='reviewer', reviewer_run_id='run2', verdict='PASS', source_unchanged=True, before_sha256='source1', after_sha256='source1', checks=[{'id':'compile','status':'PASS','evidence':['raw']}], evidence_paths=[{'path':'raw','sha256':sha(self.root/'raw')}])
        self.trust={'reviewers':{'A04':{'agent_uuid':'reviewer'}}}
    def errors(self): return evaluate(self.c, [self.r], self.trust, self.root)
    def test_fixture_valid_structure(self): self.assertEqual([], self.errors())
    def test_same_agent(self): self.r['reviewer_agent_uuid']='producer'; self.assertIn('G01 same author',self.errors())
    def test_same_run(self): self.r['reviewer_run_id']='run1'; self.assertIn('G01 same run',self.errors())
    def test_reviewer_contributor(self): self.c['contributors'].append('reviewer'); self.assertIn('G02 reviewer modified candidate',self.errors())
    def test_old_sha(self): self.r['artifact_sha256']='old'; self.assertIn('G03 stale artifact_sha256',self.errors())
    def test_no_evidence(self): self.r['evidence_paths']=[]; self.assertIn('G04 no original evidence',self.errors())
    def test_not_run(self): self.r['checks'][0]['status']='NOT_RUN'; self.assertTrue(self.errors())
    def test_fail(self): self.r['verdict']='FAIL'; self.assertTrue(self.errors())
    def test_cancelled(self): self.c['required_tasks'][0]['status']='cancelled'; self.assertIn('G05 required task incomplete',self.errors())
    def test_test_threshold_changed(self): self.r['test_version']='relaxed'; self.assertIn('G03 stale test_version',self.errors())
    def test_source_changed(self): self.r['after_sha256']='changed'; self.assertIn('G06 source changed',self.errors())
    def test_missing_role(self): self.c['required_roles'].append('A13'); self.assertIn('G07 missing/duplicate reviewer',self.errors())
    def test_forged_role(self): self.r['reviewer_agent_uuid']='attacker'; self.assertIn('G10 unauthorized reviewer',self.errors())
    def test_missing_gpu(self): self.c['requires_gpu']=True; self.assertIn('G09 no GPU capture',self.errors())
    def test_budget(self): self.c['repair_attempt']=3; self.assertIn('G11 repair budget',self.errors())
    def test_tamper_evidence(self): (self.root/'raw').write_bytes(b'tamper'); self.assertIn('G03 evidence hash',self.errors())

if __name__ == '__main__': unittest.main(verbosity=2)
