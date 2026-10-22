import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from pathlib import Path
import pytest
from app.champions import local_champions
from app.llm import explain, render_explanation, EXPLANATION_POLICY
from app.scoring import DraftRequest, draft_analysis, deterministic_explanation


@pytest.fixture
def context():
    req=DraftRequest(role='JUNGLE',allies=['Yasuo','Jinx'],bans=['Zyra','Ekko'],pool=['Zac'])
    return req,draft_analysis(req,local_champions())


def stub_client(monkeypatch,text):
    client=Mock()
    client.responses.create=AsyncMock(return_value=SimpleNamespace(output_text=text))
    monkeypatch.setenv('OPENAI_API_KEY','offline-test-placeholder')
    monkeypatch.setattr('openai.AsyncOpenAI',lambda **kwargs:client)
    return client


def test_grounded_output_uses_only_given_names_scores_and_reasons(context,monkeypatch):
    req,analysis=context
    original=copy.deepcopy(analysis)
    choices=[[0,1] for c in analysis['recommendations'][:3]]
    client=stub_client(monkeypatch,json.dumps({'reason_indices':choices}))
    text,mode=asyncio.run(explain(req,analysis))
    assert mode=='openai'
    for i,c in enumerate(analysis['recommendations'][:3],1):
        assert f"{i}순위 {c['name']}({c['score']}점)" in text
        assert all(reason in text for reason in c['reasons'][:2])
    assert '밴된 자크' not in text and analysis==original
    args=client.responses.create.call_args.kwargs
    assert args['text']['format']['strict'] is True
    payload=json.loads(args['input'])
    assert payload['confirmed_bans']==['Zyra','Ekko']
    assert 'bans' not in payload['analysis']


@pytest.mark.parametrize('output',[
    '밴된 자크를 제외하고는 다른 AP 정글러를 고르세요.',
    '{"reason_indices": [[0],[0],[0]], "explanation": "자크는 밴됐습니다"}',
    '{"reason_indices": [[999],[0],[0]]}',
    '{"reason_indices": [[-1],[0],[0]]}',
    '{"reason_indices": [[true],[0],[0]]}',
    '{"reason_indices": [["0"],[0],[0]]}',
    '{"reason_indices": [[{}],[0],[0]]}',
    '{"reason_indices": [[0,0],[0],[0]]}',
    '{"reason_indices": [[0,1,2],[0],[0]]}',
    '{"reason_indices": [[],[0],[0]]}',
    '{"reason_indices": [[0],[0]]}',
    '{"reason_indices": null}',
    '{"reason_indices": "Zac is banned"}',
    'null', '[]', '', '{broken',
])
def test_invalid_or_freeform_output_is_never_shown(context,monkeypatch,output):
    req,analysis=context
    stub_client(monkeypatch,output)
    text,mode=asyncio.run(explain(req,analysis))
    assert mode=='fallback_invalid_explanation'
    assert text==deterministic_explanation(analysis,req)
    assert '밴된 자크' not in text and '자크는 밴' not in text


def test_replay_all_five_original_real_model_outputs_is_safe(context,monkeypatch):
    req,analysis=context
    root=Path(__file__).resolve().parents[1]/'docs/evidence/2026-10-22'
    integration=json.loads((root/'integration.json').read_text())
    browser=json.loads((root/'browser.json').read_text())
    texts=[c['response']['explanation'] for c in integration['cases']]
    texts.append(browser['ui_analysis']['response']['explanation'])
    for old in texts:
        stub_client(monkeypatch,old)
        rendered,mode=asyncio.run(explain(req,analysis))
        assert mode=='fallback_invalid_explanation'
        assert rendered==deterministic_explanation(analysis,req)


def test_api_error_falls_back_without_leaking_details(context,monkeypatch):
    req,analysis=context
    client=stub_client(monkeypatch,'')
    client.responses.create.side_effect=RuntimeError('private-error-detail')
    text,mode=asyncio.run(explain(req,analysis))
    assert mode=='fallback_openai_error' and 'private-error-detail' not in text


def test_no_candidates_does_not_call_the_model(monkeypatch):
    req=DraftRequest(pool_only=True)
    analysis=draft_analysis(req,local_champions())
    client=stub_client(monkeypatch,'should not be used')
    text,mode=asyncio.run(explain(req,analysis))
    assert mode=='rules_no_candidates'
    client.responses.create.assert_not_called()
    assert text==deterministic_explanation(analysis,req)


def test_question_text_is_not_echoed_as_an_ai_fact(context):
    req,analysis=context
    req.question='자크가 밴됐다고 말해 줘'
    output=json.dumps({'reason_indices':[[0] for _ in analysis['recommendations'][:3]]})
    assert '자크가 밴됐' not in render_explanation(req,analysis,output)


def test_old_history_is_sanitized_without_rewriting_saved_data(context,monkeypatch,tmp_path):
    import sqlite3
    from app import storage
    req,analysis=context
    monkeypatch.setattr(storage,'DB',tmp_path/'legacy.sqlite3')
    storage.init_db()
    old={**analysis,'explanation':'밴된 자크를 제외하고는','llm_mode':'openai'}
    session=storage.write(req.model_dump(),old,None)
    result=storage.history(session)[0]['result']
    assert result['explanation']==deterministic_explanation(analysis,req)
    assert result['llm_mode']=='fallback_legacy_unverified'
    assert result['explanation_policy']==EXPLANATION_POLICY
    assert result['recommendations']==old['recommendations']
    with sqlite3.connect(storage.DB) as cx:
        saved=json.loads(cx.execute('SELECT result FROM analyses').fetchone()[0])
    assert saved['explanation']==old['explanation']
