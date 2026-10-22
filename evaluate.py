"""Measure a fixed four-case comparison; no network or LLM calls in timed kernels."""
import argparse
import json
import math
import platform
import statistics
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from app.champions import local_champions
from app.scoring import DraftRequest, draft_analysis

SCENARIOS = [
    ('AD 편중 / AP 정글 요청', DraftRequest(role='JUNGLE', allies=['Yasuo','Jinx'], pool=['Zyra','Ekko','Zac'])),
    ('앞라인 부재', DraftRequest(role='JUNGLE', allies=['Jayce','Zed','Jinx'], pool=['Zac','Ekko'], style='team')),
    ('AP 편중 / AD 정글 요청', DraftRequest(role='JUNGLE', allies=['Ahri','Gwen','Lux'], pool=['Vi','Graves'], style='team')),
    ('밴 제한', DraftRequest(role='JUNGLE', allies=['Yasuo','Jinx'], bans=['Zyra','Ekko'], pool=['Zyra','Ekko','Zac'])),
]
GOALS = [('AP', '픽·밴을 준수하며 AP 피해 보완'),
         ('frontline', '픽·밴을 준수하며 tank >= 2인 앞라인 보완'),
         ('AD', '픽·밴을 준수하며 AD 피해 보완'),
         ('AP', '자이라·에코 밴을 준수하며 AP 피해 보완')]


def baseline(req, roster):
    excluded = set(req.allies + req.enemies + req.bans)
    available = sorted((c for c in roster if req.role in c['roles'] and c['id'] not in excluded
                        and (not req.pool_only or c['id'] in req.pool)), key=lambda c: c['name'])
    return available[0] if available else None


def succeeds(req, champion, goal):
    if not champion or req.role not in champion['roles'] or champion['id'] in req.allies + req.enemies + req.bans:
        return False
    if req.pool_only and champion['id'] not in req.pool:
        return False
    return champion['tank'] >= 2 if goal == 'frontline' else champion['damage'] == goal


def benchmark(repeats):
    assert repeats > 0
    roster = local_champions()
    by_id = {c['id']: c for c in roster}
    # Check the evaluator itself against a correct type, a wrong type and an excluded pick.
    probe = DraftRequest(role='JUNGLE', bans=['Zac'])
    assert succeeds(probe, by_id['Vi'], 'AD')
    assert not succeeds(probe, by_id['Vi'], 'AP')
    assert not succeeds(probe, by_id['Zac'], 'frontline')
    rows = []
    for (title, req), (goal, criterion) in zip(SCENARIOS, GOALS, strict=True):
        def improved():
            recs = draft_analysis(req, roster)['recommendations']
            return by_id[recs[0]['id']] if recs else None
        methods = {'baseline': lambda: baseline(req, roster), 'improved': improved}
        for method in methods.values():
            for _ in range(20): method()
        samples = {name: [] for name in methods}
        chosen = {}
        for iteration in range(repeats):
            order = list(methods) if iteration % 2 == 0 else list(reversed(methods))
            for name in order:
                start = time.perf_counter_ns()
                champion = methods[name]()
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                samples[name].append(elapsed_ms)
                chosen[name] = champion
        row = {'title': title, 'request': req.model_dump(exclude_none=True), 'criterion': criterion}
        for name in methods:
            champion = chosen[name]
            ordered = sorted(samples[name])
            row[name] = {'champion_id': champion['id'] if champion else None,
                         'champion_name': champion['name'] if champion else None,
                         'success': succeeds(req, champion, goal),
                         'mean_ms': statistics.mean(ordered), 'median_ms': statistics.median(ordered),
                         'p95_ms': ordered[math.ceil(len(ordered) * .95) - 1], 'samples_ms': samples[name]}
        rows.append(row)
    return {'measured_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
            'python': platform.python_version(), 'repeats_per_case_method': repeats,
            'warmups_per_case_method': 20, 'timer': 'time.perf_counter_ns',
            'scope': 'preloaded roster; local selection/scoring only; excludes validation construction, file I/O, HTTP, MCP, LangGraph and LLM',
            'baseline_definition': 'same position/pick/ban/pool-only constraints; first Korean-alphabetical champion',
            'limitation': 'four curated cases, one process; success is a predefined trait check, not measured game win rate; improved kernel performs more work',
            'cases': rows, 'success_counts': {name: sum(row[name]['success'] for row in rows) for name in methods}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=200)
    args = parser.parse_args()
    if args.repeats < 1: parser.error('--repeats must be positive')
    result = benchmark(args.repeats)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for row in result['cases']:
        print(row['title'], '/', row['criterion'])
        for method in ('baseline', 'improved'):
            value = row[method]
            print(f"  {method}: {value['champion_name']}, success={value['success']}, median={value['median_ms']:.6f} ms, p95={value['p95_ms']:.6f} ms")
    print('Success counts / 4:', result['success_counts'])
    print('Timing excludes network, MCP, LangGraph and OpenAI; this is not a win-rate experiment.')


if __name__ == '__main__':
    main()
