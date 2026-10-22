"""Transparent explainable heuristics. No win-rate or ranked-strength claims."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator

ROLES = {'TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'}
ROLE_FOCUS = {
    'TOP': '탑 · 앞라인과 군중 제어 보완',
    'JUNGLE': '정글 · 진입과 CC를 통한 교전 개시',
    'MID': '미드 · 피해 유형 균형과 CC 연계',
    'ADC': '원딜 · 상대 진입에 대한 기동성과 CC 대응',
    'SUPPORT': '서포터 · 아군 딜러 보호와 교전 개시',
}


class DraftSlots(BaseModel):
    allies: list[str | None] = Field(default_factory=list, max_length=4)
    enemies: list[str | None] = Field(default_factory=list, max_length=5)
    bans: list[str | None] = Field(default_factory=list, max_length=10)

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
    slots: DraftSlots | None = None

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
        if self.slots:
            for side in ('allies', 'enemies', 'bans'):
                if [cid for cid in getattr(self.slots, side) if cid is not None] != getattr(self, side):
                    raise ValueError('슬롯 정보와 픽·밴 목록이 일치하지 않습니다.')
        return self


def team_summary(champs: list[dict[str, Any]]) -> dict[str, Any]:
    ad = sum(c['damage'] == 'AD' for c in champs)
    ap = sum(c['damage'] == 'AP' for c in champs)
    frontline = sum(c['tank'] >= 2 for c in champs)
    hard_cc = sum(c['cc'] >= 2 for c in champs)
    flags = []
    if ad >= 2 and ap == 0: flags.append('아군 물리 피해 편중')
    if ap >= 2 and ad == 0: flags.append('아군 마법 피해 편중')
    if champs and frontline == 0: flags.append('아군 앞라인 부족')
    if len(champs) >= 2 and hard_cc == 0: flags.append('아군 CC 부족')
    if not flags: flags.append('뚜렷한 조합 결함 없음 또는 입력 부족')
    return {'ad': ad, 'ap': ap, 'frontline': frontline, 'hard_cc': hard_cc,
            'engage': sum(c['engage'] >= 2 for c in champs),
            'peel': sum(c['peel'] >= 2 for c in champs), 'flags': flags}


def position_fit(role: str, c: dict, team: dict, danger: int) -> tuple[int, list[str]]:
    score, reasons = 50, []
    if role == 'TOP':
        if team['frontline'] == 0 and c['tank'] >= 2:
            score += 25; reasons.append('탑: 부족한 앞라인 담당')
        if c['cc'] >= 2:
            score += 15; reasons.append('탑: 한타 CC 보강')
    elif role == 'JUNGLE':
        if c['engage'] >= 2:
            score += 20; reasons.append('정글: 먼저 진입해 교전 개시')
        if c['cc'] >= 2:
            score += 15; reasons.append('정글: CC를 활용한 갱킹 연계')
    elif role == 'MID':
        if team['ad'] >= 2 and team['ap'] == 0 and c['damage'] == 'AP':
            score += 25; reasons.append('미드: 팀에 부족한 마법 피해 제공')
        elif team['ap'] >= 2 and team['ad'] == 0 and c['damage'] == 'AD':
            score += 25; reasons.append('미드: 팀에 부족한 물리 피해 제공')
        if team['hard_cc'] == 0 and c['cc'] >= 2:
            score += 15; reasons.append('미드: CC로 아군 교전 연계')
    elif role == 'ADC':
        if danger:
            if c['mobility'] >= 2:
                score += 25; reasons.append('원딜: 기동성으로 상대 진입 대응')
            else:
                score -= 15; reasons.append('원딜: 이동기가 부족해 아군 보호 필요')
        if c['cc'] >= 2:
            score += 15; reasons.append('원딜: CC를 활용한 교전 대응')
    elif role == 'SUPPORT':
        if c['peel'] >= 2:
            score += 25; reasons.append('서포터: 아군 딜러 보호')
        if team['engage'] == 0 and c['engage'] >= 2:
            score += 20; reasons.append('서포터: 부족한 교전 개시 보완')
    return score, reasons


def draft_analysis(req: DraftRequest, champs: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {c['id']: c for c in champs}
    combined = req.allies + req.enemies + req.bans + req.pool
    missing = sorted(set(combined) - set(lookup))
    if missing:
        raise ValueError(f'지원하지 않는 챔피언: {", ".join(missing)}')
    allies = [lookup[c] for c in req.allies]
    enemies = [lookup[c] for c in req.enemies]
    summary = team_summary(allies)
    ad, ap = summary['ad'], summary['ap']
    frontline, hard_cc = summary['frontline'], summary['hard_cc']
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
        role_score, role_reasons = position_fit(req.role, c, summary, danger)
        team = .8 * max(0, min(100, team)) + .2 * role_score
        reasons = role_reasons + reasons
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
            'breakdown':{'comfort':round(comfort), 'team':round(team), 'enemy':round(vs), 'position':role_score},
            'reasons':reasons[:4], 'composition_after':team_summary(allies + [c])})
    candidates.sort(key=lambda x:(-x['score'],x['name']))
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
            'team':summary, 'role_focus':ROLE_FOCUS[req.role],
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
