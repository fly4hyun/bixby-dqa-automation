# Bixby DQA Automation (Document → QA Auto Pipeline)
> 삼성전자 제품 설명서 PDF로부터 Bixby DQA용 QA 데이터를 자동 생성하는 엔드투엔드 파이프라인  
> 기간: 2024.12 – 2025.04 | 역할: Vision·Document AI 설계·구현 전담

---

## Summary
- 제품 매뉴얼 PDF에서 **레이아웃 검출 → 읽기 순서 정렬 → QA 데이터 자동생성**까지 자동화
- **DQA DB 스키마 형식으로 직접 적재 가능한 산출물**까지 일관된 파이프라인 구축

---

## My Contribution
- PDF 라벨링 툴 개발 및 검수 체계화
- **YOLOv12x 기반 12-클래스 문서 레이아웃 검출 모델 학습**
- 사람이 읽는 흐름을 반영한 **순서 정렬 알고리즘** 설계
- 섹션/문단 관계 기반 **QA 생성 규칙 및 변환 스크립트 개발**
- Bixby DQA DB로 **자동 변환/정합성 검증 파이프라인 설계**

---

## Performance (공개 가능한 지표만 예시 기입)
| Task | Metric | Result |
|------|--------|--------|
| Layout Detection | mAP@0.5 | 0.xx |
| Reading Order | Kendall-τ | 0.xx |
| QA Schema Validity | Pass Rate | xx.x% |

> 실제 숫자는 기업 정책 범위 내에서 기입

---

## Visual Examples
*(샘플로 교체 가능한 공간 — 결과 이미지/레이아웃 박스 시각화/QA 결과 캡쳐 등 첨부)*  
`docs/figures/layout-demo.png`  
`docs/figures/qa-output.png`

---

## Notes on Disclosure
본 프로젝트는 **기업연계 프로젝트로 코드 및 원본 데이터는 비공개**합니다.  
문서화/샘플/구조 설명만 공개 가능 범위 내에서 제공됩니다.

---
