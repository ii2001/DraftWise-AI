"""Offline regression check: confirmed bans and suggested bans must stay distinct."""
import asyncio
import copy
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from app.champions import local_champions
from app.llm import explain
from app.scoring import DraftRequest, draft_analysis


async def main():
    for bans in ([], ['Zyra','Ekko']):
        req=DraftRequest(role='JUNGLE',allies=['Yasuo','Jinx'],bans=bans,pool=['Zac'])
        analysis=draft_analysis(req,local_champions())
        original=copy.deepcopy(analysis)
        client=Mock()
        client.responses.create=AsyncMock(return_value=SimpleNamespace(output_text='검사용 설명'))
        with patch.dict(os.environ,{'OPENAI_API_KEY':'offline-test-placeholder'}), patch('openai.AsyncOpenAI',return_value=client):
            text,mode=await explain(req,analysis)
        payload=json.loads(client.responses.create.call_args.kwargs['input'])
        assert payload['confirmed_bans']==bans
        assert payload['declared_pool']==['Zac']
        assert 'bans' not in payload['analysis']
        assert payload['analysis']['suggested_bans']==analysis['bans']
        assert analysis==original
        assert mode=='openai' and text=='검사용 설명'
        print('PASS: confirmed/suggested bans separated, input unchanged; confirmed_bans=',bans)
    print('This is a mocked, offline regression check; it does not prove a real OpenAI call.')


if __name__=='__main__':
    asyncio.run(main())
