"""Run four real, potentially billable API analyses and save their actual execution modes."""
import argparse
from hashlib import sha256
import json
from itertools import permutations
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
from evaluate import SCENARIOS
from app.champions import local_champions
from app.scoring import draft_analysis
from app.llm import EXPLANATION_POLICY


def valid_grounded_text(req, data):
    recs=data['recommendations'][:3]
    lines=data['explanation'].splitlines()
    expected_tail=['점수는 교육용 규칙 평가이며 실제 승률 예측이 아닙니다.']
    if req.question:
        expected_tail.insert(0,'추가 질문에 대해 전적·실시간 상성 등 제공되지 않은 정보는 답변하지 않습니다.')
    if len(lines)!=len(recs)+len(expected_tail) or lines[len(recs):]!=expected_tail:
        return False
    for rank,c in enumerate(recs,1):
        allowed={f"{rank}순위 {c['name']}({c['score']}점). 근거: {' / '.join(reasons)}."
                 for count in (1,2) for reasons in permutations(c['reasons'],count)}
        if lines[rank-1] not in allowed:return False
    return data.get('explanation_policy')==EXPLANATION_POLICY


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8600')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    expected_trace=['validate_input','mcp_retrieve','rule_scoring','llm_explanation']
    report={'started_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
            'tested_app_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'source_hashes':{name:sha256(Path(name).read_bytes()).hexdigest() for name in ('app/llm.py','app/scoring.py','app/agent.py','app/mcp_client.py')},
            'validation_scope':'HTTP status, actual execution modes, graph trace, unchanged recommendations, server-owned evidence text contract and history; not independent game-data accuracy',
            'base_url':args.base_url,'real_requests':True,'cases':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with httpx.Client(base_url=args.base_url,timeout=40) as client:
        health=client.get('/api/health');health.raise_for_status()
        report['health']=health.json()
        if not report['health']['openai_configured']:
            report['passed']=False;report['error']='API key not configured; no real model call attempted';save()
            raise SystemExit(report['error'])
        session_id=None
        for title,req in SCENARIOS:
            payload=req.model_dump(exclude_none=True)
            if session_id: payload['session_id']=session_id
            record={'title':title,'request':payload,'started_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}
            started=time.perf_counter()
            response=client.post('/api/analyze',json=payload)
            record['http_wall_ms']=(time.perf_counter()-started)*1000
            record['http_status']=response.status_code
            record['response']=response.json()
            data=record['response']
            expected=draft_analysis(req,local_champions())
            record['grounding_contract_passed']=response.status_code==200 and valid_grounded_text(req,data)
            record['passed']=(record['grounding_contract_passed'] and response.status_code==200 and data.get('llm_mode')=='openai'
                              and data.get('graph_mode')=='langgraph' and data.get('mcp_mode')=='mcp_stdio'
                              and data.get('trace')==expected_trace
                              and data.get('recommendations')==expected['recommendations'])
            session_id=data.get('session_id',session_id)
            report['cases'].append(record);save()
            print(title,{k:data.get(k) for k in ('llm_mode','graph_mode','mcp_mode','latency_ms')},
                  'http_wall_ms=',round(record['http_wall_ms'],3),'passed=',record['passed'],flush=True)
        history=client.get('/api/history/'+session_id);history.raise_for_status()
        report['history_count']=len(history.json()['items'])
        report['passed']=all(r['passed'] for r in report['cases']) and report['history_count']>=4
        report['finished_at']=datetime.now(ZoneInfo('Asia/Seoul')).isoformat();save()
    if not report['passed']: raise SystemExit('Integration verification failed; see evidence JSON.')


if __name__=='__main__':
    main()
