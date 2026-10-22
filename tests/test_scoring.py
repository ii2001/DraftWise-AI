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
