# DraftWise AI 발표 최종본

- `DraftWise_AI_5min_FINAL.pptx`: 발표용 8장, 16:9, 네이비·골드 테마
- `DraftWise_AI_5min_FINAL.pdf`: 글꼴을 포함한 고정 레이아웃 PDF
- `rendered/contact-sheet.png`: 전체 미리보기
- `rendered/slide-01.png` ~ `slide-08.png`: 슬라이드별 렌더링
- `review.json`: 이미지 출처·해시·검사 기록

## 발표 내용 정리

교육생 번호 기입란을 제거하고 발표자 이름만 남겼다. 마지막 장의 제출 자료 목록, 교육생 번호·ZIP 조건·제출 포털 안내와 제출·Zoom 일정을 제거하고 간결한 마무리 화면으로 바꿨다. 2~6페이지의 중복 안내 문구도 줄였다.

실제 화면, 아키텍처, 테스트·실측 결과, Before/After 그래프와 한계·트레이드오프 설명은 유지했다. 7페이지는 이전 최종본과 동일하다. 본문은 편집 가능한 PowerPoint 텍스트 도형이며, 실제 브라우저 캡처는 이미지다. 캡처 안의 글자는 텍스트 도형처럼 직접 수정할 수 없다.

## 실제 이미지

| 페이지 | 삽입한 원본 |
|---|---|
| 3 | `01-draft-desktop.png`, `02-role-and-pool.png` |
| 5 | `04-real-ai-analysis.png`, `05-composition-comparison.png` |
| 6 | `06-history.png` |

모두 `docs/evidence/2026-10-22-grounding-fix/screenshots/`의 실제 Chrome 캡처다. 원본 이미지 바이트를 그대로 삽입하고 비율을 유지하며 필요한 영역만 확대했다. 가상 UI·AI 생성 화면·오류 주입 화면은 사용하지 않았다.

## 검토 범위

Python-pptx로 편집하고 LibreOffice 26.8.1로 PDF를 내보냈다. 전체 8장을 PNG로 렌더링해 잘림·겹침을 검토했다. 삭제 대상 문구가 본문·발표자 노트·PDF에 없는지, 실제 이미지가 이전과 같은지, 본문이 PDF에 모두 출력되는지와 편집 잠금이 없는지 검사했다.

발표자 노트의 배분은 총 **4분 45초 목표**이며 실제 낭독 시간은 측정하지 않았다. PPT 표시 글꼴은 기존 Noto Sans CJK KR이며, 해당 글꼴이 없는 환경에서는 PDF를 사용하면 같은 레이아웃을 유지할 수 있다. 이번 편집에 새 모델 호출이나 앱 코드 변경은 포함하지 않았다.
