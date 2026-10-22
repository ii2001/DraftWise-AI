from fastapi.testclient import TestClient
from app.main import app


def test_api_health_catalog_and_analysis(monkeypatch):
    monkeypatch.setenv('DRAFTWISE_MCP_DISABLED','1')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with TestClient(app) as client:
        res=client.get('/api/health')
        assert res.status_code==200
        assert res.json()['openai_configured'] is False
        with monkeypatch.context() as m:
            m.setattr('app.main.riot_latest_version', lambda:'16.18.1')
            res=client.get('/api/champions')
        assert res.status_code==200
        assert len(res.json()['champions'])>=100
        resp=client.post('/api/analyze',json={
            'role':'JUNGLE','allies':['Yasuo','Jinx'],'enemies':['LeeSin','Ahri'],
            'pool':['Zyra','Ekko','Zac']})
        assert resp.status_code==200,resp.text
        output=resp.json()
        assert output['trace']==['validate_input','mcp_retrieve','rule_scoring','llm_explanation']
        assert output['llm_mode']=='demo_no_api_key'
        assert output['mcp_mode']=='local_disabled'
        assert len(output['recommendations'])>0
        assert client.get('/api/history/'+output['session_id']).json()['items']
        assert client.post('/api/analyze',json={'allies':['Yasuo'],'bans':['Yasuo']}).status_code==422
