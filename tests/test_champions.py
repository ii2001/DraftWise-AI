from app.champions import catalog, local_champions, lookup
from app.scoring import DraftRequest, ROLES, draft_analysis

# Missing from the original 138-champion roster; verified against Data Dragon 16.21.1.
ADDED_IDS = set('''Akshan Ambessa Anivia AurelionSol Aurora Briar Corki DrMundo Fizz
Gangplank Heimerdinger Hwei Illaoi Kalista Kled KogMaw KSante Leblanc Lissandra
Locke Lucian Malzahar Mel Naafiri Nasus Neeko Nilah Quinn Renata Samira Sett
Singed Xerath Yunara Zaahen'''.split())


def test_complete_roster_has_unique_ids_and_valid_scoring_metadata():
    champions = local_champions()
    ids = {c['id'] for c in champions}
    assert len(champions) == len(ids) == 173
    assert ADDED_IDS <= ids
    assert set(lookup()) == ids
    assert catalog()['champions'] == champions
    for c in champions:
        assert c['name']
        assert c['roles'] and set(c['roles']) <= ROLES
        assert c['damage'] in {'AD', 'AP', 'MIXED'}
        assert all(type(c[key]) is int and 0 <= c[key] <= 3
                   for key in ('tank', 'cc', 'engage', 'peel', 'mobility'))


def test_every_added_champion_can_be_picked_banned_and_recommended():
    champions = local_champions()
    by_id = lookup()
    for cid in ADDED_IDS:
        role = by_id[cid]['roles'][0]
        result = draft_analysis(DraftRequest(role=role, pool=[cid], pool_only=True), champions)
        assert [c['id'] for c in result['recommendations']] == [cid]
        result = draft_analysis(DraftRequest(role=role, allies=[cid]), champions)
        assert cid not in {c['id'] for c in result['recommendations']}
        result = draft_analysis(DraftRequest(role=role, pool=[cid], pool_only=True, bans=[cid]), champions)
        assert result['recommendations'] == []
