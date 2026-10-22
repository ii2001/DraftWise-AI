import os
import time
from hashlib import sha256
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from .agent import run_agent
from .scoring import DraftRequest
from .champions import catalog,riot_latest_version
from .storage import init_db,write,history

ROOT=Path(__file__).resolve().parent.parent
load_dotenv(ROOT/'.env')

@asynccontextmanager
async def lifespan(app:FastAPI):
    init_db()
    yield

app=FastAPI(title='DraftWise AI',version='0.1.0',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

@app.get('/')
async def index():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    for asset in ('style.css','app.js'):
        version=sha256((ROOT/'static'/asset).read_bytes()).hexdigest()[:12]
        html=html.replace(f'/static/{asset}',f'/static/{asset}?v={version}')
    return HTMLResponse(html,headers={'Cache-Control':'no-store'})

@app.get('/api/health')
def health():
    return {'status':'ok','openai_configured':bool(os.getenv('OPENAI_API_KEY')),
            'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini') if os.getenv('OPENAI_API_KEY') else None}

@app.get('/api/champions')
def champions():
    result=catalog()
    # Do not depend on external availability during tests or app startup.
    result['version']=riot_latest_version()
    return result

@app.post('/api/analyze')
async def analyze(req:DraftRequest):
    try:
        started=time.perf_counter()
        result=await run_agent(req)
        result['latency_ms']=round((time.perf_counter()-started)*1000)
        sid=write(req.model_dump(),result,req.session_id)
        result['session_id']=sid
        return result
    except ValueError as e:
        raise HTTPException(status_code=422,detail=str(e)) from e
    except Exception as e:
        # Do not leak internal model/API credentials.
        raise HTTPException(status_code=503,detail='분석 처리 중 오류가 발생했습니다. 백엔드 로그를 확인하세요.') from e

@app.get('/api/history/{session_id}')
def get_history(session_id:str):
    if len(session_id)>80:
        raise HTTPException(status_code=400,detail='Invalid session ID')
    return {'items':history(session_id)}
