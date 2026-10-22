"""OpenAI is called ONLY from the Python backend. No API secret reaches the browser."""
import json
import os
from .scoring import DraftRequest, deterministic_explanation

PROMPT = '''너는 리그 오브 레전드 밴픽 의사결정을 돕는 한국어 코치다.
아래 자료는 실시간 승률·카운터 정보가 아니라 직접 정의한 교육용 특성 데이터이며,
점수는 결정론적 조합 휴리스틱이다. 근거 없는 티어, 승률, 패치 수치, 일대일 카운터를 절대 만들어내지 마라.
JSON에 제공된 추천 순위나 점수를 변경하지 말고, 각 후보가 왜 도움이 되는지 비교해서
3~5문장으로 명료하게 설명하라. 사용자 질문이 있으면 그 맥락도 반영하되 데이터가 없으면 명시하라.
직접 입력한 픽/밴은 확정 정보로 취급하고 픽이 금지된 챔피언은 절대 권유하지 마라.
confirmed_bans만 실제로 밴된 챔피언이다. suggested_bans는 아직 밴하지 않은 추천 밴 후보이며,
이를 실제 밴으로 설명하거나 confirmed_bans에 없는 챔피언이 밴됐다고 말하지 마라.
declared_pool은 사용자가 등록한 주력 목록이며 실제 전적이나 숙련도 측정값이 아니다.
위험도 및 부정확성 주의: 실제 라이브 밴픽 데이터를 확인한 것은 아니다.'''

async def explain(req:DraftRequest,analysis:dict) -> tuple[str,str]:
    key=os.getenv('OPENAI_API_KEY','').strip()
    if not key:
        return deterministic_explanation(analysis,req), 'demo_no_api_key'
    try:
        from openai import AsyncOpenAI
        client=AsyncOpenAI(api_key=key, timeout=18.0, max_retries=0)
        model_analysis={**analysis, 'suggested_bans':analysis['bans']}
        del model_analysis['bans']
        payload={'position':req.role,'allies':req.allies,'enemies':req.enemies,
                 'confirmed_bans':req.bans,'declared_pool':req.pool,
                 'question':req.question,'style':req.style,'analysis':model_analysis}
        response=await client.responses.create(
            model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
            instructions=PROMPT,
            input=json.dumps(payload,ensure_ascii=False),
            max_output_tokens=450)
        text=response.output_text.strip()
        if not text:
            raise ValueError('Empty model output')
        return text,'openai'
    except Exception:
        # Fail safe; detailed errors are logged server side, never leak credentials to user.
        return deterministic_explanation(analysis,req), 'fallback_openai_error'
