import json
import sqlite3
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
from .llm import EXPLANATION_POLICY
from .scoring import DraftRequest, deterministic_explanation
DB=Path(os.getenv('DRAFTWISE_DB','data/draftwise.sqlite3'))

def init_db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB) as cx:
        cx.execute('CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL, request TEXT NOT NULL, result TEXT NOT NULL)')
        cx.execute('CREATE INDEX IF NOT EXISTS by_session ON analyses (session_id, created_at DESC)')

def write(req:dict,result:dict,session_id:str|None) -> str:
    if not session_id:session_id=str(uuid4())
    with sqlite3.connect(DB) as cx:
        cx.execute('INSERT INTO analyses VALUES (?, ?, ?, ?, ?)',(str(uuid4()),session_id,datetime.now(timezone.utc).isoformat(),json.dumps(req,ensure_ascii=False),json.dumps(result,ensure_ascii=False)))
    return session_id

def history(session_id:str) -> list[dict]:
    with sqlite3.connect(DB) as cx:
        rows=cx.execute('SELECT created_at,request,result FROM analyses WHERE session_id = ? ORDER BY created_at DESC LIMIT 10',(session_id,)).fetchall()
    items=[]
    for date,req,res in rows:
        request,result=json.loads(req),json.loads(res)
        if result.get('explanation_policy')!=EXPLANATION_POLICY:
            result['explanation']=deterministic_explanation(result,DraftRequest.model_validate(request))
            result['llm_mode']='fallback_legacy_unverified'
            result['explanation_policy']=EXPLANATION_POLICY
        items.append({'created_at':date,'request':request,'result':result})
    return items
