from fastapi.testclient import TestClient
from app.main import app


def test_api_health_catalog_and_analysis(monkeypatch,tmp_path):
    monkeypatch.setattr('app.storage.DB',tmp_path/'api.sqlite3')
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
        roster=res.json()['champions']
        assert len(roster)==173
        assert {'Nasus','Leblanc','Hwei','Yunara','Zaahen','Locke'} <= {c['id'] for c in roster}
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


def test_history_restores_sparse_slots_settings_and_comparison(monkeypatch,tmp_path):
    monkeypatch.setenv('DRAFTWISE_MCP_DISABLED','1')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.setattr('app.storage.DB',tmp_path/'history.sqlite3')
    payload={'role':'JUNGLE','allies':['Yasuo','Jinx'],'enemies':['Ahri'],
             'bans':['LeeSin'],'pool':['Zac'],'pool_only':True,'style':'team',
             'question':'앞라인을 보완하고 싶어',
             'slots':{'allies':[None,'Yasuo','Jinx'], 'enemies':[None,None,'Ahri'],
                      'bans':[None]*9+['LeeSin']}}
    with TestClient(app) as client:
        response=client.post('/api/analyze',json=payload)
        assert response.status_code==200,response.text
        output=response.json()
        item=client.get('/api/history/'+output['session_id']).json()['items'][0]
        assert item['request']['slots']==payload['slots']
        assert item['request']['pool_only'] is True
        assert item['request']['question']==payload['question']
        assert item['result']['recommendations'][0]['composition_after']==output['recommendations'][0]['composition_after']
        assert client.get('/api/history/not-this-session').json()['items']==[]
        payload['slots']['allies']=['Ahri']
        assert client.post('/api/analyze',json=payload).status_code==422


def test_page_serves_local_vue_and_versioned_assets():
    from hashlib import sha256
    from html.parser import HTMLParser
    from app.main import ROOT

    class Assets(HTMLParser):
        urls=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='script': self.urls.append(attrs['src'])
            if tag=='link' and attrs.get('rel')=='stylesheet': self.urls.append(attrs['href'])

    with TestClient(app) as client:
        response=client.get('/')
        assert response.status_code==200
        assert response.headers['cache-control']=='no-store'
        assert 'id="boot-status"' in response.text
        assets=Assets()
        assets.feed(response.text)
        assert '/static/vendor/vue-3.5.44.global.prod.js' in assets.urls
        assert not any('jsdelivr' in url for url in assets.urls)
        for filename in ('app.js','style.css'):
            version=sha256((ROOT/'static'/filename).read_bytes()).hexdigest()[:12]
            url=f'/static/{filename}?v={version}'
            assert url in assets.urls
            assert client.get(url).status_code==200
        vue=client.get('/static/vendor/vue-3.5.44.global.prod.js')
        assert vue.status_code==200
        assert 'vue v3.5.44' in vue.text[:200]
