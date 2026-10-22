"""OpenAI selects supplied evidence; only server-owned facts become visible prose."""
import json
import os
from .scoring import DraftRequest, deterministic_explanation

EXPLANATION_POLICY = 'validated_evidence_v1'
PROMPT = '''너는 한국어 밴픽 코치다. 추천 순위와 점수는 이미 확정되어 있다.
사용자의 질문, 아군·상대 조합을 고려해 상위 3명 각각의 reasons 중 가장 관련 있는 근거를
1~2개 선택하라. 후보 순서는 그대로 유지하고 각 reasons 배열의 0부터 시작하는 인덱스만 반환하라.
새 근거, 챔피언 이름, 밴 상태나 자유 서술을 생성하지 마라.
confirmed_bans만 확정 밴이며 suggested_bans는 아직 밴하지 않은 추천 후보다.
declared_pool은 주력 등록 목록이며 실제 전적·숙련도 측정값이 아니다.'''
OUTPUT_FORMAT = {
    'type': 'json_schema', 'name': 'draft_evidence', 'strict': True,
    'schema': {
        'type': 'object', 'additionalProperties': False,
        'properties': {'reason_indices': {'type': 'array', 'items': {
            'type': 'array', 'items': {'type': 'integer'}}}},
        'required': ['reason_indices'],
    },
}


def render_explanation(req: DraftRequest, analysis: dict, output: str) -> str:
    data = json.loads(output)
    recs = analysis['recommendations'][:3]
    if not isinstance(data, dict) or set(data) != {'reason_indices'}:
        raise ValueError('Unexpected explanation fields')
    selections = data['reason_indices']
    if not isinstance(selections, list) or len(selections) != len(recs):
        raise ValueError('Evidence count does not match recommendations')
    sentences = []
    for rank, (candidate, indices) in enumerate(zip(recs, selections, strict=True), 1):
        reasons = candidate['reasons']
        if (not isinstance(indices, list) or not 1 <= len(indices) <= 2
                or any(type(i) is not int or not 0 <= i < len(reasons) for i in indices)
                or len(indices) != len(set(indices))):
            raise ValueError('Invalid evidence index')
        selected = ' / '.join(reasons[i] for i in indices)
        sentences.append(f"{rank}순위 {candidate['name']}({candidate['score']}점). 근거: {selected}.")
    if req.question:
        sentences.append('추가 질문에 대해 전적·실시간 상성 등 제공되지 않은 정보는 답변하지 않습니다.')
    sentences.append('점수는 교육용 규칙 평가이며 실제 승률 예측이 아닙니다.')
    return '\n'.join(sentences)


async def explain(req: DraftRequest, analysis: dict) -> tuple[str, str]:
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        return deterministic_explanation(analysis, req), 'demo_no_api_key'
    if not analysis['recommendations']:
        return deterministic_explanation(analysis, req), 'rules_no_candidates'
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key, timeout=18.0, max_retries=0)
        model_analysis = {**analysis, 'suggested_bans': analysis['bans']}
        del model_analysis['bans']
        model_analysis['recommendations'] = analysis['recommendations'][:3]
        payload = {'position': req.role, 'allies': req.allies, 'enemies': req.enemies,
                   'confirmed_bans': req.bans, 'declared_pool': req.pool,
                   'question': req.question, 'style': req.style, 'analysis': model_analysis}
        response = await client.responses.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), instructions=PROMPT,
            input=json.dumps(payload, ensure_ascii=False), text={'format': OUTPUT_FORMAT},
            max_output_tokens=450)
    except Exception:
        return deterministic_explanation(analysis, req), 'fallback_openai_error'
    try:
        return render_explanation(req, analysis, response.output_text), 'openai'
    except (ValueError, TypeError):
        return deterministic_explanation(analysis, req), 'fallback_invalid_explanation'
