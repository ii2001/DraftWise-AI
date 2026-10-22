import pytest
from pydantic import ValidationError
from app.champions import local_champions
from app.scoring import DraftRequest, draft_analysis, deterministic_explanation

CAT=local_champions()

def run(**kwargs):
    return draft_analysis(DraftRequest(**kwargs),CAT)

def test_ad_heavy_allies_get_ap_jungle_recommendation():
    result=run(role='JUNGLE',allies=['Yasuo','Jinx'],pool=['Zyra','Ekko','Zac'])
    assert result['team']['flags'][0]=='아군 물리 피해 편중'
    assert result['recommendations'][0]['damage']=='AP'
    assert result['recommendations'][0]['id'] not in {'Yasuo','Jinx'}

def test_no_frontline_rewards_tank():
    result=run(role='JUNGLE',allies=['Jayce','Zed','Jinx'],pool=['Zac','Ekko'],style='team')
    assert '아군 앞라인 부족' in result['team']['flags']
    assert result['recommendations'][0]['id']=='Zac'

def test_bans_never_recommended():
    result=run(role='JUNGLE',allies=['Yasuo','Jinx'],enemies=['LeeSin'],bans=['Zyra','Zac'],pool=['Zyra','Zac','Ekko'])
    assert not {'Zyra','Zac','LeeSin'}.intersection(x['id'] for x in result['recommendations'])

def test_pool_only_filters():
    result=run(role='JUNGLE',pool=['Ekko'],pool_only=True)
    assert [r['id'] for r in result['recommendations']]==['Ekko']

def test_conflicting_selection_invalid():
    with pytest.raises(ValidationError):
        DraftRequest(allies=['Yasuo'],enemies=['Yasuo'])
    with pytest.raises(ValidationError):
        DraftRequest(allies=['Yasuo'],bans=['Yasuo'])

def test_unknown_champion_rejected():
    with pytest.raises(ValueError,match='지원하지 않는 챔피언'):
        run(allies=['NOT_REAL'])

def test_explanation_does_not_claim_winrate():
    req=DraftRequest(role='JUNGLE',allies=['Yasuo','Jinx'])
    text=deterministic_explanation(draft_analysis(req,CAT),req)
    assert '실제 승률 예측이 아닙니다' in text

def test_empty_pool_only_is_safe():
    result=run(role='MID',pool_only=True)
    assert result['recommendations']==[]


def test_recommendation_comparison_adds_only_the_selected_champion():
    result=run(role='JUNGLE',allies=['Yasuo','Jinx'],pool=['Zac'],pool_only=True)
    before=result['team']
    after=result['recommendations'][0]['composition_after']
    assert before['ad']==after['ad']==2
    assert before['ap']==0 and after['ap']==1
    assert before['frontline']==0 and after['frontline']==1
    assert before['hard_cc']==0 and after['hard_cc']==1
    assert '아군 물리 피해 편중' in before['flags']
    assert '아군 물리 피해 편중' not in after['flags']
    assert '아군 앞라인 부족' not in after['flags']


@pytest.mark.parametrize('role,pool,favored,other',[
    ('TOP',['Ornn','Fiora'],'Ornn','Fiora'),
    ('JUNGLE',['Zac','MasterYi'],'Zac','MasterYi'),
    ('MID',['Ahri','Zed'],'Ahri','Zed'),
    ('ADC',['Ezreal','Ashe'],'Ezreal','Ashe'),
    ('SUPPORT',['Lulu','Brand'],'Lulu','Brand'),
])
def test_position_fit_rewards_the_roles_needed_traits(role,pool,favored,other):
    result=run(role=role,allies=['Jinx','Yasuo'] if role!='ADC' else ['Yasuo'],
               enemies=['Akali'],pool=pool,pool_only=True)
    recs={c['id']:c for c in result['recommendations']}
    assert recs[favored]['breakdown']['position']>recs[other]['breakdown']['position']
    assert result['role_focus']
    assert all(0<=c['score']<=100 for c in recs.values())


def test_slots_must_match_compact_lists_and_obey_team_limits():
    req=DraftRequest(allies=['Jinx'],bans=['Ahri'],slots={
        'allies':[None,None,'Jinx'], 'enemies':[], 'bans':[None,'Ahri']})
    assert req.slots.allies[2]=='Jinx'
    with pytest.raises(ValidationError,match='일치'):
        DraftRequest(allies=['Jinx'],slots={'allies':['Yasuo']})
    with pytest.raises(ValidationError):
        DraftRequest(slots={'allies':[None]*5})
