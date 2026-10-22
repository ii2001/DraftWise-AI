# 2026-10-22 제출 검증 증거

수치는 실행 시 수집했다. API 응답·화면의 문장을 수정해 정확한 것처럼 꾸미지 않았다. 최종 구조적 실행 검사와 자연어 사실 검토는 별도다.

| 파일 | 의미 |
|---|---|
| `tests.json`, `python-tests.txt`, `node-tests.txt` | 최종 Python 20개·Node 8개 검사, 시각·환경·종료 코드·파일 해시 |
| `integration.json`, `integration.txt` | 동일 네 입력의 실제 OpenAI·LangGraph·MCP 실행. 모드·trace·정량 추천 일치·HTTP 시간 검증 |
| `browser.json`, `browser.txt` | 실제 Chrome 12개 확인과 UI 버튼의 추가 실제 분석 1회. 분석 API를 가짜 응답으로 바꾸지 않음 |
| `screenshots/01`–`09` PNG | 실제 페이지 캡처. 08은 브라우저 외부 자산 차단, 09는 앱 스크립트 차단 오류 주입 조건 |
| `benchmark.json`, `benchmark.txt` | 동일 네 입력·각 방식 200회 시간 표본과 사전 성공 기준. HTTP·MCP·LangGraph·LLM 제외 |
| `prompt-context-selfcheck.txt` | 모의 OpenAI 클라이언트로 실제 밴/추천 밴 입력 분리 확인. 실제 호출 증거가 아님 |
| `explanation-review.json` | 최종 출력 5개의 확정 밴 서술 수동 검토. 밴하지 않은 자크를 밴됐다고 말한 오류 1건 미해결 |
| `summary.json` | 원본에서 계산한 집계. 입력별 중앙값의 평균과 HTTP 평균을 구분 |
| `attempts/browser-01.*` | 첫 자동화 시도의 필터 해제 누락으로 인한 실패. 모델 호출 전에 종료됨 |
| `attempts/pre-fix-*` | 밴 입력 구분 수정 전의 실제 API 4회·UI 1회, 테스트와 오류 설명 캡처·검토 |
| `checksums.sha256` | 증거 파일의 SHA-256 목록 |

최종 실제 요청은 4회 + UI 1회다. 수정 전 5회를 포함한 제출 준비 전체 실제 OpenAI 호출은 10회다. 이 횟수는 API 사용료나 토큰 수를 측정한 값이 아니다. 일반 테스트의 모의 클라이언트 호출과 HTTP 422 검증 요청은 실제 OpenAI 호출 수에 포함하지 않았다.

검증 당시 소스는 기존 앱 커밋 `78f4cdd`와 `app/llm.py`의 입력 구분 수정이다. 실제 테스트한 파일의 SHA-256을 JSON에 기록했다. 문서·측정 도구를 추가한 최종 커밋과 원래 앱 기준 커밋이 같다고 주장하지 않는다.

## 재현

작업 폴더 루트에서 의존성을 설치하고 서버를 띄운다. `.env` 또는 환경에 유효한 `OPENAI_API_KEY`가 필요하다. 키 자체를 출력하거나 파일에 기록하지 않는다. 제출 증거를 덮어쓰지 않도록 재실행 출력은 `/tmp`로 지정한다.

```bash
# 터미널 1: 실제 MCP를 켜고 분리 DB와 포트를 사용
DRAFTWISE_DB=/tmp/draftwise-recheck.sqlite3 .venv/bin/python -c "import app.main,os,uvicorn; os.environ.pop('DRAFTWISE_MCP_DISABLED',None); uvicorn.run(app.main.app,host='127.0.0.1',port=8602)"
```

```bash
# 터미널 2: 로컬 테스트·계산 비교
.venv/bin/python -m pytest -q
node --test tests/test_draft_ui.cjs
.venv/bin/python -m scripts.verify_prompt_context
.venv/bin/python evaluate.py --repeats 200 --output /tmp/draftwise-recheck/benchmark.json

# 실제 API 4회 호출; 비용 발생
.venv/bin/python -m scripts.verify_integration --base-url http://127.0.0.1:8602 --output /tmp/draftwise-recheck/integration.json

# Google Chrome 필요. Playwright는 검증 도구로만 /tmp에 설치
npm install --prefix /tmp/draftwise-browser-tools playwright --no-package-lock --no-audit --no-fund
# 실제 UI 분석 추가 1회 호출; 비용 발생
PLAYWRIGHT_MODULE=/tmp/draftwise-browser-tools/node_modules/playwright node scripts/browser_submission.cjs http://127.0.0.1:8602 /tmp/draftwise-recheck
```

기본 pytest 20개는 실제 API를 호출하지 않는다. `verify_prompt_context`의 `mode='openai'`는 모의 클라이언트 응답으로 확인한 코드 분기이며 실제 API 성공 증거로 사용하지 않는다. 통합 실행의 `passed`는 HTTP·실행 모드·정량 추천 일치·이력 검사를 뜻한다. 모델 설명 전체의 사실 정확도까지 포함하지 않으며 `explanation-review.json`의 실패 기록을 함께 봐야 한다.

브라우저 08의 외부 요청 차단은 브라우저 자산만 차단한다. 서버에서 OpenAI에 연결할 수 없다는 조건은 시험하지 않았다. 실제 휴대폰·Safari·Firefox·동시 사용자 부하는 이번 검증 범위에 없다.

`/tmp`의 검증 DB는 저장소에 포함하지 않았다. JSON의 세션 ID와 내용은 검증용 합성 입력에 대한 기록이며 실제 사용자 개인정보를 수집한 것이 아니다.
