# 📦 Repository 이름

**bixby-dqa-automation** — 제품 매뉴얼(PDF)로부터 **Bixby DQA용 QA 데이터**를 자동 생성·정리하는 파이프라인

> 기간: **2024.12 – 2025.04**
> 역할: **Vision·Document AI 설계/개발 전담** (레이아웃 탐지, 순서 정렬, QA 자동생성, 툴링)
> 핵심 기술: **PyTorch, YOLOv12x, TensorRT(선택), pdfplumber, EasyOCR, FAISS(선택), Python, YAML/JSON 파이프라인**

---

## 🚀 한 줄 요약

삼성전자 설명서 PDF에서 **레이아웃 → 읽기 순서 → QA 자동 생성**까지 이어지는 **완전 자동화** 파이프라인을 구축했습니다.

---

## ✅ 핵심 성과 (Resume-ready)

* PDF **레이아웃 라벨링 툴** 자체 개발 및 검수 프로세스 정착
* **YOLOv12x** 기반 12클래스 레이아웃 검출 모델 학습·배포
* **읽기 순서 정렬 알고리즘** 설계(블록 그래프+규칙 기반+좌표 정규화)
* **QA 자동 생성 알고리즘** 및 검수 워크플로우 구축(룰/프롬프트 하이브리드)
* Bixby **DQA DB 연동 포맷**으로 결과 자동 변환/적재 스크립트 제공

---

## 🧱 저장소 구조 (제안)

```text
bixby-dqa-automation/
├─ README.md
├─ LICENSE
├─ CITATION.cff
├─ CHANGELOG.md
├─ docs/
│  ├─ overview.md
│  ├─ figures/
│  │  ├─ pipeline-architecture.png   # 파이프라인 개요도
│  │  ├─ layout-classes.png          # 12개 클래스 예시 시각화
│  │  └─ demo.gif                    # 전체 데모 GIF
│  └─ reports/
│     └─ evaluation.md               # 정량 결과/에블레이션
├─ data/
│  ├─ samples/                        # 공개 가능한 샘플 PDF/주석
│  └─ schemas/
│     ├─ layout_classes.yaml          # 12개 클래스 정의
│     ├─ dqa_export_schema.json       # DQA DB 적재 스키마
│     └─ prompt_templates.yaml        # (선택) QA 프롬프트 템플릿
├─ configs/
│  ├─ train_yolo_v12x.yaml            # YOLO 학습 설정
│  ├─ pipeline.yaml                   # 전체 파이프라인 설정 (입출력 폴더 등)
│  └─ rules.yaml                      # 읽기 순서/QA 생성 규칙 모음
├─ tools/
│  ├─ labeling_tool/                  # PDF 라벨링 툴 (PyQt5/Qt)
│  │  ├─ app.py
│  │  ├─ widgets/
│  │  └─ README.md
│  └─ visualizer/
│     ├─ draw_layout.py
│     └─ README.md
├─ src/
│  ├─ __init__.py
│  ├─ pdf/
│  │  ├─ extract_pages.py             # pdfplumber로 페이지/블록 추출
│  │  └─ ocr_fallback.py              # EasyOCR 등 보조 OCR
│  ├─ layout/
│  │  ├─ train_yolo.py                # YOLOv12x 학습/추론 래퍼
│  │  └─ postprocess.py               # NMS, 클래스 맵핑, 정규화
│  ├─ order/
│  │  └─ ordering.py                  # 읽기 순서 정렬 알고리즘
│  ├─ qa/
│  │  ├─ qa_generate.py               # QA 자동 생성(룰/프롬프트 하이브리드)
│  │  └─ qa_validate.py               # 규칙·스키마 검증기
│  ├─ export/
│  │  └─ export_dqa.py                # Bixby DQA DB 포맷으로 변환
│  └─ utils/
│     ├─ io.py
│     ├─ geometry.py
│     └─ logging.py
├─ scripts/
│  ├─ 00_setup_env.bat
│  ├─ 10_prepare_data.py
│  ├─ 20_train_layout.py
│  ├─ 30_infer_layout.py
│  ├─ 40_order_blocks.py
│  ├─ 50_generate_qa.py
│  └─ 60_export_dqa.py
└─ tests/
   ├─ test_ordering.py
   ├─ test_export.py
   └─ test_schema.py
```

---

## 🧩 12개 레이아웃 클래스 정의 (예시 `data/schemas/layout_classes.yaml`)

```yaml
version: 1
classes:
  - 대제목
  - 섹션 박스
  - 중제목
  - 소제목
  - 내용
  - 이미지/표 박스
  - 이미지
  - 표
  - 아이콘_내용
  - 페이지 번호
  - 아이콘
  - 목차
```

---

## 🛠️ 빠른 시작 (Quickstart)

### 0) 환경

```bash
conda create -n dqa python=3.10 -y
conda activate dqa
pip install -r requirements.txt  # torch, pdfplumber, pyyaml, numpy, opencv-python 등
```

### 1) 샘플 데이터 준비

```bash
python scripts/10_prepare_data.py \
  --pdf_dir data/samples/pdfs \
  --ann_dir data/samples/annotations
```

### 2) 레이아웃 모델 학습/추론

```bash
# 학습
python scripts/20_train_layout.py --cfg configs/train_yolo_v12x.yaml

# 추론(박스 JSON 저장)
python scripts/30_infer_layout.py \
  --pdf_dir data/samples/pdfs \
  --out_dir outputs/layout_pred
```

### 3) 읽기 순서 정렬

```bash
python scripts/40_order_blocks.py \
  --pred_dir outputs/layout_pred \
  --cfg configs/pipeline.yaml \
  --out_dir outputs/ordered
```

### 4) QA 자동 생성 및 검증

```bash
python scripts/50_generate_qa.py \
  --ordered_dir outputs/ordered \
  --rules configs/rules.yaml \
  --out_dir outputs/qa_raw

python -m src.qa.qa_validate --input outputs/qa_raw --schema data/schemas/dqa_export_schema.json
```

### 5) DQA 포맷으로 내보내기

```bash
python scripts/60_export_dqa.py \
  --qa_dir outputs/qa_raw \
  --schema data/schemas/dqa_export_schema.json \
  --out outputs/dqa_db.jsonl
```

---

## 🔗 파이프라인 개요

1. **PDF 파싱**: pdfplumber로 블록 초기 추출, 필요 시 OCR 보완(EasyOCR)
2. **레이아웃 검출**: YOLOv12x로 12클래스 바운딩 박스 산출
3. **순서 정렬**: 좌표/열 정규화 → 블록 그래프 구성 → 규칙 기반 순회(좌→우, 상→하, 컬럼 고려)
4. **QA 생성**: 제목/문단/표/이미지 간 관계 규칙 + 프롬프트 템플릿(선택) 기반 질의·응답 생성
5. **검증·정리**: 스키마/룰 검증 → DQA DB 포맷으로 변환·적재

---

## 🧮 순서 정렬 알고리즘 (요지)

* **정규화**: 페이지별 width/height 기준 [0,1]로 좌표 정규화
* **컬럼 추정**: KMeans 또는 히스토그램으로 컬럼 경계 탐지(선택)
* **그래프**: 노드=블록, 에지=읽기 후보(상하/좌우 근접, Z-축 우선순위)
* **우선순위**: (페이지번호, 컬럼, y→x 정렬) + 클래스 기반 가중치(제목류 우선)
* **후처리**: 페이지 넘김/섹션 전환 처리, 페이지 번호·아이콘 제거 규칙

---

## 🧪 평가 지표 (예시)

* **레이아웃 mAP@0.5**
* **순서 정렬 정확도**: GT 시퀀스 대비 Kendall-τ / Spearman / edit distance
* **QA 품질**: 규칙 기반 정합률(키 필드 누락률, 형식 오류율), 휴먼 스폿체크 합격률

> `docs/reports/evaluation.md`에 수치/설정/시드 명시

---

## 📊 결과 예시 (README에 표로 요약)

| Task             | Metric      | Score |
| ---------------- | ----------- | ----- |
| Layout Detection | mAP@0.5     | 0.86  |
| Reading Order    | Kendall-τ ↑ | 0.78  |
| QA Schema Valid  | Pass Rate   | 98.2% |

*(실제 수치로 교체)*

---

## 🧰 라벨링 툴 (tools/labeling_tool)

* PDF 페이지 로딩, 박스 드로잉/수정/클래스 지정
* COCO/YOLO/커스텀(JSON) 내보내기
* **검수 모드**: 다중 어노테이터 합의/리뷰 기능

> `tools/labeling_tool/README.md`에 GIF/스크린샷 포함 권장

---

## ⚙️ 설정 파일 예시

### `configs/pipeline.yaml`

```yaml
paths:
  pdf_dir: data/samples/pdfs
  layout_pred_dir: outputs/layout_pred
  ordered_dir: outputs/ordered
  qa_dir: outputs/qa_raw
  export_path: outputs/dqa_db.jsonl

order:
  column_detection: histogram   # or kmeans/none
  title_priority: true
  ignore_classes: [페이지 번호, 아이콘]

qa:
  mode: rules-first
  prompt_template: data/schemas/prompt_templates.yaml
```

### `configs/rules.yaml`

```yaml
reading_order:
  line_threshold: 0.015
  column_gap: 0.05
  title_boost: 0.2

qa_generation:
  q_types: [기능, 사용법, 경고, 주의, 설치, 유지보수]
  join_paragraphs: true
  table_as_kv: true
  image_caption_as_hint: true
  blacklist: [마케팅문구]
```

---

## 🧑‍💻 사용 예시 코드 스니펫

```python
# src/order/ordering.py (요약)
def order_blocks(blocks, cfg):
    b = normalize(blocks)
    cols = detect_columns(b, method=cfg['order']['column_detection'])
    G = build_graph(b, cols)
    seq = traverse(G, priority=cfg['order'].get('title_priority', True))
    return seq
```

```python
# src/qa/qa_generate.py (요약)
for section in ordered_sections:
    if has_title(section) and has_content(section):
        questions = make_questions(section, rules)
        answers = extract_answers(section)
        yield to_record(questions, answers)
```

---

## 🔒 라이선스/비공개 데이터 주의

* 기업 문서/데이터는 **저작권/보안** 문제로 미공개. README에는 **샘플/더미**로 대체
* 모델 가중치 또한 공개 범위를 명확히 표기 (예: 비공개/요청 시 제공 불가)

---

## 📣 README 배지/메타

```md
![status](https://img.shields.io/badge/status-production-green)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-lightgrey)
```

---

## 🧩 GitHub 운영 파일(복붙용)

### `.github/ISSUE_TEMPLATE/bug_report.md`

```md
---
name: Bug report
about: Create a report to help us improve
---
**Describe the bug**
**To Reproduce**
**Expected behavior**
**Screenshots**
**Env (OS, Python, CUDA)**
```

### `.github/pull_request_template.md`

```md
## Summary
-

## Changes
-

## Checklist
- [ ] 코드 스타일 & 린트 통과
- [ ] 단위 테스트 통과
- [ ] 문서/예시 업데이트
```

### `CITATION.cff`

```yaml
cff-version: 1.2.0
title: bixby-dqa-automation
authors:
  - family-names: Lee
    given-names: Hyunhee
identifiers:
  - type: url
    value: https://github.com/fly4hyun/bixby-dqa-automation
date-released: 2025-04-30
version: 1.0.0
```

---

## 📅 프로젝트 타임라인(명시)

* **2024.12**: 문제정의, 라벨링 스키마/툴 초안
* **2025.01**: 레이아웃 모델 학습, 베이스라인 구축
* **2025.02**: 읽기 순서 정렬 알고리즘, QA 생성 1차
* **2025.03**: 품질 개선, 검수 워크플로우, 스키마 정합성 98%+
* **2025.04**: DQA DB 연동/최종 결과물 납품

---

## 🧭 커뮤니케이션용 요약(상단 배치용)

* 레이아웃 탐지 → 읽기 순서 → QA 자동화 **엔드투엔드** 구축
* **툴·알고리즘·스키마**까지 **운영 관점**에서 완결
* 실제 DQA DB 연동/적재 **운영 수준** 품질 달성

---

## 📄 README 템플릿 (복붙 후 값만 교체)

```md
# bixby-dqa-automation

제품 매뉴얼(PDF)에서 **Bixby DQA용 QA 데이터**를 자동 생성하는 파이프라인입니다.  
기간: 2024.12–2025.04 / 역할: Vision·Document AI 개발

## Highlights
- 라벨링 툴 개발 → YOLOv12x 레이아웃 검출 → 읽기 순서 정렬 → QA 자동 생성
- DQA DB 포맷으로 자동 내보내기(jsonl) 및 스키마 검증 98%+

## Tech Stack
PyTorch, YOLOv12x, pdfplumber, EasyOCR, Python, YAML/JSON

## Repo Map
(트리 삽입)

## Quickstart
(명령어 블록 5단계)

## Results
(mAP, Kendall-τ, Pass Rate 표)

## Limitations
- 기업 데이터 비공개 / 샘플로 대체

## License
MIT (또는 사내 정책에 맞게)

## Citation
(CITATION.cff 참조)

## Contact
이현희 / fly4hyun@naver.com
```

---

## 🔖 체크리스트 (배포 전)

* [ ] 샘플 PDF/주석/출력 더미 업로드
* [ ] 파이프라인 스크립트 5단계 동작 확인
* [ ] 결과 표/데모 GIF 첨부
* [ ] 라이선스/보안 고지 명확화
* [ ] 타임라인·역할·지표 수치 기입

---

## 🔁 확장 아이디어(선택)

* TensorRT 엔진 변환(서버/엣지 가속), 표 구조 복원 모듈, 이미지-텍스트 연결 강화, GPT 없는 완전 룰 베이스 모드 등
