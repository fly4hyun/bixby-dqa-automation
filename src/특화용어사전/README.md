# 특화 용어사전 생성 파이프라인

`dict_gen.py`, `ko_word_mapping.py`, `check_mapping_word.py`, `postprocess.py` —  
네 개 스크립트로 **제품 설명서 PDF → 다국어 특화 용어사전**을 자동 생성·검증·통합합니다.

---

## 1. 사전 준비

| 항목 | 경로 / 내용 |
|------|-------------|
| 제품 매핑 정보 엑셀 | `data/제품맵핑정보.xlsx` |
| 각 제품 DQA 엑셀   | `data/DQA/<파일이름>.xlsx` |
| OpenAI 키 (2개)    | 스크립트 상단 `openai_api_key`, `openai_api_key_2` 직접 입력 또는 `OPENAI_API_KEY` 환경변수 사용 |

### 1‑1. 환경 설정 (conda 권장)
```bash
# 파이썬 3.12 가상환경 생성
conda create --name dict_samsung python=3.12 -y
conda activate dict_samsung

# 필수 패키지 설치
pip install langchain openai sentence-transformers langchain-openai \
            pandas openpyxl tqdm
```

---

## 2. 스크립트별 역할

| 스크립트 | 핵심 기능 | 주요 입·출력 |
|-----------|-----------|--------------|
| **dict_gen.py** | 다국어 설명서 → 언어 감지<br>한글 키워드 ↔ 다국어 키워드 **1차 후보** 생성 | `keywords/<카테고리>/<파일>.xlsx`<br>(Keyword, Mapping, Language) |
| **ko_word_mapping.py** | 한글 설명서 그룹화 → **특화 키워드** 확보<br>다국어 설명서에서 의미 일치 단어 추출 | 위 동일 파일에 매핑 확장 |
| **check_mapping_word.py** | 2차 검증: 언어 재확인·매핑 오류 수정 | 매핑 파일 덮어쓰기 |
| **postprocess.py** | 모든 매핑 파일 취합 → 카테고리·제품 정보와 함께 **최종 사전** 완성 | `Specialized_Terminology_Dictionary.xlsx` |

---

## 3. 실행 순서

```bash
# 1) 다국어 매핑 후보 생성
python dict_gen.py

# 2) 한글 ↔ 다국어 매핑 확정
python ko_word_mapping.py

# 3) 매핑 파일 최종 검증
python check_mapping_word.py

# 4) 결과 통합 및 엑셀 사전 생성
python postprocess.py
```

실행 로그는 `tqdm` 진행률과 함께 터미널에 출력됩니다.

---

## 4. 출력 구조

```
keywords/
└─ <category>&<products>&<device>/
   ├─ <파일이름1>.xlsx   # Keyword, Mapping, Language
   ├─ <파일이름2>.xlsx
   └─ …

Specialized_Terminology_Dictionary.xlsx   # 최종 통합 사전
```

| 컬럼 | 설명 |
|------|------|
| `no` | 일련번호 |
| `category / products` | 제품 카테고리 및 라인업 |
| `target_device(kr/en)` | 한글·영문 모델명 |
| `model_names / product_names` | 관련 모델·제품명 목록 |
| `korean / english / … french` | 각 언어별 특화 용어 |

---

## 5. 비고

- PDF → 엑셀(DQA) 변환은 별도 파이프라인에서 선행되어야 합니다.  
- OpenAI API 호출량이 많으므로 **요금·속도**를 고려해 배치 실행하세요.
