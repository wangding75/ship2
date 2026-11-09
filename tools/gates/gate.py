"""Fail-closed candidate gate. Trust must be provisioned by an independent operator.

The trust document and reviewer public keys MUST live outside the candidate and
be read-only to producers. Local fixture keys are never production authority.
"""
import argparse, hashlib, json, pathlib, subprocess

def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def evaluate(candidate, reviews, trust, root):
    errors = []
    def require(ok, reason):
        if not ok: errors.append(reason)
    require(candidate.get('repair_attempt', 99) <= 2, 'G11 repair budget')
    require(candidate.get('contract_review') == 'PASS', 'G14 contract not approved')
    require(candidate.get('merged_build') == 'PASS', 'G08 merged build missing')
    for task in candidate.get('required_tasks', []):
        require(task.get('status') == 'PASS', 'G05 required task incomplete')
    roles = set()
    for review in reviews:
        role = review.get('role')
        roles.add(role)
        require(review.get('reviewer_agent_uuid') != candidate.get('producer_agent_uuid'), 'G01 same author')
        require(review.get('reviewer_run_id') != candidate.get('producer_run_id'), 'G01 same run')
        require(review.get('reviewer_agent_uuid') not in candidate.get('contributors', []), 'G02 reviewer modified candidate')
        for field in ('candidate_commit', 'artifact_sha256', 'spec_sha256', 'test_version', 'contract_sha256'):
            require(bool(candidate.get(field)) and review.get(field) == candidate.get(field), 'G03 stale ' + field)
        require(review.get('verdict') == 'PASS', 'G04 verdict not PASS')
        require(review.get('source_unchanged') is True and review.get('before_sha256') == candidate.get('source_sha256') == review.get('after_sha256'), 'G06 source changed')
        checks = {x.get('id'): x for x in review.get('checks', [])}
        for check_id in candidate.get('required_checks', []):
            check = checks.get(check_id, {})
            require(check.get('status') == 'PASS' and bool(check.get('evidence')), 'G04 missing/failed check ' + check_id)
        for evidence in review.get('evidence_paths', []):
            path = (root / evidence['path']).resolve()
            require(path.is_relative_to(root) and path.is_file() and sha(path) == evidence['sha256'], 'G03 evidence hash')
        require(bool(review.get('evidence_paths')), 'G04 no original evidence')
        if candidate.get('requires_gpu'):
            require(review.get('gpu_capture_sha256') in [e['sha256'] for e in review.get('evidence_paths', [])], 'G09 no GPU capture')
        if candidate.get('stage_final'):
            require(role == 'A15' and review.get('key_cases_rerun') is True, 'G13 final review missing')
        identity = trust.get('reviewers', {}).get(role, {})
        require(bool(identity) and identity.get('agent_uuid') == review.get('reviewer_agent_uuid'), 'G10 unauthorized reviewer')
    require(set(candidate.get('required_roles', [])) == roles and len(reviews) == len(roles), 'G07 missing/duplicate reviewer')
    require(bool(candidate.get('required_checks')) and bool(candidate.get('required_roles')), 'G04 empty requirements')
    return errors

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True); p.add_argument('--candidate', required=True)
    p.add_argument('--trust', required=True); p.add_argument('--openssl', required=True)
    p.add_argument('--review', action='append', default=[])
    args = p.parse_args()
    root = pathlib.Path(args.root).resolve()
    trust_path = pathlib.Path(args.trust).resolve()
    if trust_path.is_relative_to(root): raise ValueError('G10 trust cannot be candidate-controlled')
    trust = json.loads(trust_path.read_text(encoding='utf-8-sig'))
    candidate = json.loads(pathlib.Path(args.candidate).read_text(encoding='utf-8-sig'))
    # Freeze requirements as well as payload: a producer cannot supply fewer checks.
    if trust.get('candidates', {}).get(candidate.get('candidate_commit')) != sha(args.candidate):
        raise ValueError('G10 candidate requirements not independently authorized')
    reviews = []
    for name in args.review:
        path = pathlib.Path(name)
        review = json.loads(path.read_text(encoding='utf-8-sig'))
        identity = trust['reviewers'][review['role']]
        key = (trust_path.parent / identity['public_key']).resolve()
        if key.is_relative_to(root) or sha(key) != identity['key_sha256']: raise ValueError('G10 untrusted key')
        subprocess.run([args.openssl, 'dgst', '-sha256', '-verify', str(key), '-signature', str(path)+'.sig', str(path)], check=True, capture_output=True)
        reviews.append(review)
    errors = evaluate(candidate, reviews, trust, root)
    artifact = (root / candidate['artifact_path']).resolve()
    if not artifact.is_relative_to(root) or sha(artifact) != candidate['artifact_sha256']: errors.append('G03 artifact mismatch')
    print(json.dumps({'verdict':'FAIL' if errors else 'PASS', 'errors':errors}, indent=2))
    return int(bool(errors))

if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(json.dumps({'verdict':'BLOCKED', 'error':str(e)})); raise SystemExit(2)
