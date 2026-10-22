"""Compare against an alphabetical, role-only baseline on fixed, reproducible cases."""
from app.champions import local_champions
from app.scoring import DraftRequest,draft_analysis

SCENARIOS = [
 ('AD 편중 / AP 정글 요청',DraftRequest(role='JUNGLE',allies=['Yasuo','Jinx'],pool=['Zyra','Ekko','Zac'])),
 ('앞라인 부재',DraftRequest(role='JUNGLE',allies=['Jayce','Zed','Jinx'],pool=['Zac','Ekko'],style='team')),
 ('AP 편중 / AD 정글 요청',DraftRequest(role='JUNGLE',allies=['Ahri','Gwen','Lux'],pool=['Vi','Graves'],style='team')),
 ('밴 제한',DraftRequest(role='JUNGLE',allies=['Yasuo','Jinx'],bans=['Zyra','Ekko'],pool=['Zyra','Ekko','Zac'])),
]
roster=local_champions()
for title,req in SCENARIOS:
    result=draft_analysis(req,roster)
    pool={c['id']:c for c in roster}
    available=sorted([c for c in roster if req.role in c['roles'] and c['id'] not in set(req.allies+req.enemies+req.bans)],key=lambda c:c['name'])
    baseline=available[0] if available else None
    chosen=result['recommendations'][0] if result['recommendations'] else None
    print(f'{title}\n  Baseline (가나다순): {baseline["name"] if baseline else "없음"}\n  DraftWise: {chosen["name"] if chosen else "없음"}, 종합점수 {chosen["score"] if chosen else "-"}\n  검토한 후보: {result["considered"]}\n')
print('참고: 이것은 추천 시나리오 사례 비교일 뿐 승률 향상 또는 통계적 정확도 검증이 아닙니다.')
