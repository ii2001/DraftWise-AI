# DraftWise AI 실제 화면 발표 최종본

- PPT: `DraftWise_AI_5min_FINAL.pptx`
- PDF: `DraftWise_AI_5min_FINAL.pdf`
- 전체 미리보기: `rendered/contact-sheet.png`
- 슬라이드별 렌더링: `rendered/slide-01.png` ~ `slide-08.png`
- 검사 기록: `review.json`

요청 경로 `presentation/DraftWise_AI_5min_presentation.pptx`는 없었으므로, 실제 원본 `docs/evidence/presentation/DraftWise_AI_5min_presentation.pptx`를 사용했다. 원본 파일은 덮어쓰지 않았다.

## 수정 페이지와 실제 이미지

| 페이지 | 변경 | 삽입한 원본 이미지 |
|---|---|---|
| 3 | 가상 UI 도식과 도식 안내·기존 링크 문구를 제거하고 실제 밴픽 영역과 주력 저장 영역을 확대 배치 | `01-draft-desktop.png`, `02-role-and-pool.png` |
| 5 | 가상 추천 막대·비교표를 실제 추천 카드·AI 근거와 선택 전후 지표로 교체. 자크 86.8, 에코 83.3, 자이라 78.5점을 캡처에서 확인 가능 | `04-real-ai-analysis.png`, `05-composition-comparison.png` |
| 6 | 기존 검사 수치를 유지하고 통합 실행 설명을 간결하게 정리. 실제 최근 분석 목록과 불러오기 버튼 추가 | `06-history.png` |

모든 이미지는 `docs/evidence/2026-10-22-grounding-fix/screenshots/`의 실제 Chrome 캡처다. 원본 이미지 파일 바이트를 그대로 PPT에 삽입하고, PowerPoint 자르기 설정으로 해당 영역만 확대했다. 이미지를 늘이거나 텍스트·수치를 합성하지 않았다. 비교 캡처의 하단 알림 대신 지표 영역을, 이력 캡처는 헤더와 첫 기록을 표시한다. 표시 영역 좌표와 원본 SHA-256은 `review.json`에 있다.

`03-picks-and-bans.png`는 3페이지와 중복되어 추가하지 않았다. 오류 주입 화면인 08·09나 이전 오류 보호 화면인 10을 정상 실행 이미지로 사용하지 않았다.

## 유지한 내용과 검토

- 전체 8장, 16:9, 다크 네이비·골드 테마와 원래 Noto Sans CJK KR 텍스트 스타일 유지.
- 1·2·4·7·8페이지 본문 XML은 원본과 같음. 같은 렌더러로 생성한 해당 페이지 PNG도 원본과 픽셀 단위로 일치.
- 4페이지 아키텍처와 7페이지 Before/After 그래프·수치 유지.
- Python-pptx로 편집. LibreOffice 26.8.1로 PDF를 내보내고 PyMuPDF로 전체 8장을 렌더링해 검토.
- 수정 페이지의 본문이 PDF에서 모두 추출되는지, 새 텍스트 상자와 이미지의 겹침·슬라이드 범위 이탈이 없는지 검사.
- 전체 미리보기와 수정 3·5·6페이지의 큰 렌더링을 눈으로 확인. 이미지 원본 바이트와 비율도 검사.
- 앱 코드 변경이나 새 API 호출 없이 기존 실행 증거 사용. 모델 재검증·테스트 재실행은 이번 PPT 편집에 포함하지 않음.

## 발표 시간과 표시 환경

8장 모두 발표자 노트를 추가했다. 배분은 20 / 35 / 45 / 45 / 50 / 30 / 45 / 15초, 총 **4분 45초 목표**다. 실제 낭독 리허설로 실측한 시간은 아니다. 실제 발표 전에 화면 전환을 포함해 확인해야 한다.

PowerPoint 자동 PDF 저장은 완료되지 않아 LibreOffice 렌더링을 사용했다. PDF에는 기존 글꼴을 부분 포함했다. PPT를 여는 컴퓨터에 Noto Sans CJK KR 글꼴이 없으면 대체 글꼴로 표시될 수 있으므로, 고정된 화면 공유가 필요하면 함께 제공한 PDF를 사용할 수 있다. 발표자 이름·교육생 번호와 일정 등 수정 요청 밖의 원본 내용은 유지했다.
