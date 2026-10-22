from collections import Counter
import pytest
from app.champions import local_champions
from evaluate import ROLE_ORDER, benchmark, composition, random_scenarios


def test_random_drafts_are_repeatable_balanced_and_have_no_pick_ban_conflicts():
    roster=local_champions();by_id={c['id']:c for c in roster}
    first=random_scenarios(10,20261022,roster)
    assert [(title,req.model_dump()) for title,req in first]==[
        (title,req.model_dump()) for title,req in random_scenarios(10,20261022,roster)]
    assert first!=random_scenarios(10,20261023,roster)
    assert Counter(req.role for _,req in first)=={r:2 for r in ROLE_ORDER}
    for _,req in first:
        assert len(req.allies)==4 and len(req.enemies)==5 and len(req.bans)==10
        assert len(set(req.allies+req.enemies+req.bans))==19
        assert len(req.pool)==3 and req.pool_only
        assert not set(req.pool)&set(req.allies+req.enemies+req.bans)
        assert all(req.role in by_id[cid]['roles'] for cid in req.pool)
        for cid,role in zip(req.allies,[r for r in ROLE_ORDER if r!=req.role],strict=True):
            assert role in by_id[cid]['roles']
        for cid,role in zip(req.enemies,ROLE_ORDER,strict=True):
            assert role in by_id[cid]['roles']


def test_composition_rubric_counts_traits_without_treating_mixed_as_both_damage_types():
    by_id={c['id']:c for c in local_champions()}
    assert composition([])['score']==0
    assert composition([by_id['Kaisa']])['score']==0
    assert composition([by_id['Zed']])['score']==25
    assert composition([by_id['Zed'],by_id['Ahri']])['score']==75
    assert composition([by_id['Zed'],by_id['Ahri'],by_id['Ornn']])['score']==100


def test_timing_repetitions_do_not_change_random_inputs_or_outcome_draws():
    one=benchmark(1);three=benchmark(3)
    assert one['case_count']==three['case_count']==10
    for left,right in zip(one['cases'],three['cases'],strict=True):
        assert left['request']==right['request']
        for method in ('baseline','improved'):
            for field in ('champion_id','recommendation_score','composition_after','complete','repair_success'):
                assert left[method][field]==right[method][field]
            assert len(left[method]['samples_ms'])==1
            assert len(right[method]['samples_ms'])==3
            assert right[method]['valid']
        assert left['improved']['recommendation_score']>=left['baseline']['recommendation_score']
    with pytest.raises(ValueError):benchmark(0)
