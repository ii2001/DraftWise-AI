"""Transparent explainable heuristics. No win-rate or ranked-strength claims."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator

ROLES = {'TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'}

class DraftRequest(BaseModel):
    role: str = 'JUNGLE'
    allies: list[str] = Field(default_factory=list, max_length=5)
    enemies: list[str] = Field(default_factory=list, max_length=5)
    bans: list[str] = Field(default_factory=list, max_length=10)
    pool: list[str] = Field(default_factory=list, max_length=40)
    pool_only: bool = False
    style: str = 'balanced'
    question: str = Field(default='', max_length=300)
    session_id: str | None = Field(default=None, max_length=80)

    @field_validator('role')
    @classmethod
    def role_allowed(cls,v):
        v = v.upper().strip()
        if v not in ROLES:
            raise ValueError('지원하지 않는 포지션입니다.')
        return v

    @field_validator('allies', 'enemies', 'bans', 'pool')
    @classmethod
    def unique(cls,v):
        if len(v) != len(set(v)):
            raise ValueError('동일 목록에 중복 챔피언이 있습니다.')
        return v

    @field_validator('style')
    @classmethod
    def style_allowed(cls,v):
        if v not in {'balanced', 'comfort', 'team'}:
            raise ValueError('지원하지 않는 추천 방식입니다.')
        return v

    @model_validator(mode='after')
    def disallow_overlaps(self):
        active = self.allies + self.enemies
        if len(active) != len(set(active)):
            raise ValueError('아군과 적군에 동일 챔피언을 동시에 선택할 수 없습니다.')
        if set(active).intersection(self.bans):
            raise ValueError('픽된 챔피언을 밴 목록에 넣을 수 없습니다.')
        return self


def draft_analysis(req: DraftRequest, champs: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {c['id']: c for c in champs}
    combined = req.allies + req.enemies + req.bans + req.pool
    missing = sorted(set(combined) - set(lookup))
    if missing:
        raise ValueError(f'지원하지 않는 챔피언: {", ".join(missing)}')
    allies = [lookup[c] for c in req.allies]
    enemies = [lookup[c] for c in req.enemies]
    ad = sum(c['damage']=='AD' for c in allies)
    ap = sum(c['damage']=='AP' for c in allies)
    frontline = sum(c['tank']>=2 for c in allies)
    hard_cc = sum(c['cc']>=2 for c in allies)
    danger = sum(c['mobility']>=2 and c['engage']>=1 for c in enemies)
    pressure = sum(c['tank']>=2 for c in enemies)
    needs_ap = ad>=2 and ap==0
    needs_ad = ap>=2 and ad==0
    needs_frontline = len(allies)>0 and frontline==0
    needs_cc = len(allies)>=2 and hard_cc==0
    pool_set=set(req.pool)
    banned_or_picked=set(req.allies+req.enemies+req.bans)

    if req.style=='comfort':
        pw,tw,ew = .65,.23,.12
    elif req.style=='team':
        pw,tw,ew=.2,.58,.22
    else:
        pw,tw,ew=.4,.4,.2

    candidates=[]
    for c in champs:
        if req.role not in c['roles'] or c['id'] in banned_or_picked:
            continue
        if req.pool_only and c['id'] not in pool_set:
            continue
        # A user-declared champion pool is a proxy for familiarity, not Riot mastery data.
        comfort = 95 if c['id'] in pool_set else (50 if pool_set else 70)
        team = 47.0
        reasons=[]
        if needs_ap:
            if c['damage']=='AP':
                team+=28;reasons.append('AD 편중을 보완하는 AP 피해')
            elif c['damage']=='AD':team-=15
        elif needs_ad:
            if c['damage']=='AD':team+=28;reasons.append('AP 편중을 보완하는 AD 피해')
            elif c['damage']=='AP':team-=15
        else:
            team += 5 if c['damage']=='MIXED' else 0
        if needs_frontline:
            if c['tank']>=2:
                team+=20;reasons.append('부족한 앞라인 보완')
            elif c['tank']==0:team-=10
        if needs_cc:
            if c['cc']>=2:
                team+=14;reasons.append('군중 제어기 보강')
            elif c['cc']==0: team-=7
        if 'Yasuo' in req.allies and c['engage']>=2 and c['cc']>=2:
            team+=10;reasons.append('야스오와 연계 가능한 진입/CC')
        team=max(0,min(100,team))
        vs=50.0
        if danger>0 and (c['tank']>=2 or c['peel']>=2):
            vs+=min(22, danger*9);reasons.append('상대 진입에 대비한 생존/보호')
        if pressure>=2 and c['damage']=='AP':
            vs+=8;reasons.append('상대 앞라인에 대비한 피해 유형 다변화')
        if len(enemies)>0 and c['cc']>=2:
            vs+=5
        vs=max(0,min(100,vs))
        total=round(comfort*pw+team*tw+vs*ew,1)
        if c['id'] in pool_set: reasons.insert(0,'직접 등록한 숙련 챔피언')
        if not reasons: reasons.append('현재 선택 정보에서 큰 조합 결함이 없음')
        candidates.append({'id':c['id'], 'name':c['name'], 'role':req.role,
            'damage':c['damage'],'score':total,
            'breakdown':{'comfort':round(comfort), 'team':round(team), 'enemy':round(vs)},
            'reasons':reasons[:4]})
    candidates.sort(key=lambda x:(-x['score'],x['name']))
    flags=[]
    if needs_ap:flags.append('아군 물리 피해 편중')
    if needs_ad:flags.append('아군 마법 피해 편중')
    if needs_frontline:flags.append('아군 앞라인 부족')
    if needs_cc:flags.append('아군 CC 부족')
    if not flags: flags.append('뚜렷한 조합 결함 없음 또는 입력 부족')
    bans=[]
    # Explainable ban candidate criteria: opponents' high engage/CC, not real ban rate.
    for c in champs:
        if c['id'] in banned_or_picked or c['id'] in pool_set:
            continue
        threat = c['engage']*3+c['cc']*2+c['mobility']*2
        if needs_frontline and c['engage']>=2: threat+=4
        if c['tank']>=2 and ad>=2:threat+=4
        if threat>=16:bans.append((threat,c))
    bans.sort(key=lambda p:(-p[0],p[1]['id']))
    return {'recommendations':candidates[:5],
            'bans':[{'id':c['id'],'name':c['name'],'reason':'진입·군중 제어 또는 조합 압박 위험(교육용 규칙 평가)'} for _,c in bans[:3]],
            'team':{'ad':ad,'ap':ap,'frontline':frontline,'hard_cc':hard_cc,'flags':flags},
            'weights':{'comfort':pw,'team':tw,'enemy':ew},
            'considered':len(candidates),'data_quality':'curated_demo'}


def deterministic_explanation(result:dict,req:DraftRequest) -> str:
    recs=result['recommendations']
    if not recs:
        return '추천 가능한 챔피언이 없습니다. 밴, 포지션 또는 챔피언 풀 제한을 조정해 주세요.'
    first=recs[0]
    flags=' / '.join(result['team']['flags'])
    reasons='; '.join(first['reasons'])
    text=f"현재 분석: {flags}. 1순위는 {first['name']}({first['score']}점)입니다. 추천 근거: {reasons}."
    if req.question: text+=f" 추가 질문({req.question})을 고려할 때, 수치화되지 않은 개별 라인 상성과 숙련도는 직접 판단해야 합니다."
    text+=' 점수는 학습용 휴리스틱으로 계산했으며 실제 승률 예측이 아닙니다.'
    return text
