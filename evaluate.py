"""Compare seeded random picks and DraftWise on ten generated drafts; no API calls."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
import platform
import random
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from app.champions import local_champions
from app.scoring import DraftRequest, draft_analysis, team_summary

# Historical fixed inputs remain available to the separate real-API integration check.
SCENARIOS = [
    ('AD 편중 / AP 정글 요청', DraftRequest(role='JUNGLE', allies=['Yasuo','Jinx'], pool=['Zyra','Ekko','Zac'])),
    ('앞라인 부재', DraftRequest(role='JUNGLE', allies=['Jayce','Zed','Jinx'], pool=['Zac','Ekko'], style='team')),
    ('AP 편중 / AD 정글 요청', DraftRequest(role='JUNGLE', allies=['Ahri','Gwen','Lux'], pool=['Vi','Graves'], style='team')),
    ('밴 제한', DraftRequest(role='JUNGLE', allies=['Yasuo','Jinx'], bans=['Zyra','Ekko'], pool=['Zyra','Ekko','Zac'])),
]
ROLE_ORDER = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT']


def eligible(req, roster):
    excluded = set(req.allies + req.enemies + req.bans)
    return [c for c in roster if req.role in c['roles'] and c['id'] not in excluded
            and (not req.pool_only or c['id'] in req.pool)]


def baseline(req, roster, rng):
    available = eligible(req, roster)
    return rng.choice(available) if available else None


def random_scenarios(count, seed, roster):
    rng = random.Random(seed)
    scenarios = []
    for index in range(count):
        role = ROLE_ORDER[index % len(ROLE_ORDER)]
        bans = rng.sample([c['id'] for c in roster], 10)
        used = set(bans)
        def pick(position):
            c = rng.choice([c for c in roster if position in c['roles'] and c['id'] not in used])
            used.add(c['id'])
            return c['id']
        allies = [pick(r) for r in ROLE_ORDER if r != role]
        enemies = [pick(r) for r in ROLE_ORDER]
        pool = rng.sample([c['id'] for c in roster if role in c['roles'] and c['id'] not in used], 3)
        req = DraftRequest(role=role, allies=allies, enemies=enemies, bans=bans,
                           pool=pool, pool_only=True, style='balanced')
        scenarios.append((f'R{index+1:02} {role}', req))
    return scenarios


def composition(champions):
    summary = team_summary(champions)
    # A separate structural rubric, independent of recommendation weights/rank.
    checks = {'AD': summary['ad'] >= 1, 'AP': summary['ap'] >= 1,
              'frontline': summary['frontline'] >= 1, 'hard_cc': summary['hard_cc'] >= 1}
    return {'score': sum(checks.values()) * 25, 'checks': checks}


def benchmark(repeats, case_count=10, seed=20261022):
    if repeats < 1 or case_count < 1:
        raise ValueError('repeats and case_count must be positive')
    roster = local_champions()
    by_id = {c['id']: c for c in roster}
    # Outcome draws do not depend on timing repetitions or warmups.
    outcomes_rng = random.Random(seed + 100_000)
    rows = []
    for index, (title, req) in enumerate(random_scenarios(case_count, seed, roster)):
        analysis = draft_analysis(req, roster)
        scores = {c['id']: c['score'] for c in analysis['recommendations']}
        candidates = eligible(req, roster)
        assert len(candidates) == 3 and set(scores) == {c['id'] for c in candidates}
        chosen = {'baseline': baseline(req, roster, outcomes_rng),
                  'improved': by_id[analysis['recommendations'][0]['id']]}
        timing_rng = random.Random(seed + 200_000 + index)
        def improved():
            recs = draft_analysis(req, roster)['recommendations']
            return by_id[recs[0]['id']] if recs else None
        methods = {'baseline': lambda: baseline(req, roster, timing_rng), 'improved': improved}
        for method in methods.values():
            for _ in range(20): method()
        samples = {name: [] for name in methods}
        for iteration in range(repeats):
            order = list(methods) if iteration % 2 == 0 else list(reversed(methods))
            for name in order:
                start = time.perf_counter_ns()
                methods[name]()
                samples[name].append((time.perf_counter_ns() - start) / 1_000_000)
        before = composition([by_id[cid] for cid in req.allies])
        row = {'title': title, 'request': req.model_dump(exclude_none=True),
               'eligible_ids': [c['id'] for c in candidates], 'before': before}
        for name, champion in chosen.items():
            valid = champion is not None and champion['id'] in row['eligible_ids']
            assert valid, (title, name)
            after = composition([by_id[cid] for cid in req.allies] + [champion])
            ordered = sorted(samples[name])
            row[name] = {'champion_id': champion['id'], 'champion_name': champion['name'],
                         'valid': valid, 'recommendation_score': scores[champion['id']],
                         'composition_after': after, 'complete': after['score'] == 100,
                         'repair_success': before['score'] < 100 and after['score'] > before['score'],
                         'mean_ms': statistics.mean(ordered), 'median_ms': statistics.median(ordered),
                         'p95_ms': ordered[math.ceil(len(ordered) * .95) - 1], 'samples_ms': samples[name]}
        rows.append(row)
    summary = {}
    for name in ('baseline', 'improved'):
        summary[name] = {
            'valid_count': sum(r[name]['valid'] for r in rows),
            'mean_recommendation_score': statistics.mean(r[name]['recommendation_score'] for r in rows),
            'mean_composition_score': statistics.mean(r[name]['composition_after']['score'] for r in rows),
            'complete_count': sum(r[name]['complete'] for r in rows),
            'repair_success_count': sum(r[name]['repair_success'] for r in rows),
            'mean_of_case_medians_ms': statistics.mean(r[name]['median_ms'] for r in rows)}
    return {'measured_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
            'started_from_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'source_hashes': {f: sha256(Path(f).read_bytes()).hexdigest()
                              for f in ('evaluate.py','app/scoring.py','data/champions.json')},
            'python': platform.python_version(), 'case_count': case_count, 'seed': seed,
            'role_counts': dict(Counter(r['request']['role'] for r in rows)),
            'outcome_seed': seed + 100_000, 'timing_seed_start': seed + 200_000,
            'generation': '10 random bans, four allies and five enemies picked by role without reuse, three random unpicked/unbanned pool candidates; balanced style, pool_only=true; no output-based case filtering',
            'baseline_definition': 'one uniform random choice per case from the same three eligible pool candidates; outcome RNG separate from timing RNG',
            'composition_rubric': '25 points each for AD>=1, AP>=1, tank>=2 count>=1 and cc>=2 count>=1 in the final allied five; MIXED is not counted as AD or AP, matching stored metadata',
            'recommendation_score_caveat': 'Both choices scored by the existing recommendation rule. Improved selects its maximum, so a higher value is expected by construction, not independent accuracy evidence.',
            'repair_opportunity_count': sum(r['before']['score'] < 100 for r in rows),
            'repeats_per_case_method': repeats, 'warmups_per_case_method': 20,
            'timer': 'time.perf_counter_ns',
            'scope': 'preloaded roster; random filtering/selection versus full local scoring; excludes input generation, outcome evaluation, file I/O, HTTP, MCP, LangGraph and OpenAI',
            'limitation': 'one seed, ten synthetic drafts and one random outcome per draft; structural rubric and app score are not game win rate or externally validated accuracy; improved performs more work',
            'cases': rows, 'summary': summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=200)
    parser.add_argument('--cases', type=int, default=10)
    parser.add_argument('--seed', type=int, default=20261022)
    args = parser.parse_args()
    if args.repeats < 1 or args.cases < 1:
        parser.error('--repeats and --cases must be positive')
    result = benchmark(args.repeats, args.cases, args.seed)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for row in result['cases']:
        print(row['title'], 'before=', row['before']['score'])
        for method in ('baseline', 'improved'):
            v = row[method]
            print(f"  {method}: {v['champion_name']}, app_score={v['recommendation_score']}, composition={v['composition_after']['score']}, complete={v['complete']}, median={v['median_ms']:.6f} ms")
    print('Cases:', result['case_count'], 'seed:', result['seed'], 'repair opportunities:', result['repair_opportunity_count'])
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    print('Local synthetic comparison only; not API latency, game win rate or independent accuracy.')


if __name__ == '__main__':
    main()
