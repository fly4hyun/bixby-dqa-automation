# PDF Parsing Data 생성 프로세스

이 프로젝트는 삼성전자 설명서 pdf로부터 PDF Parsing Data 를 생성
문서별로 각 내용을 엑셀 형식으로 정렬하여 저장
생성된 결과물을 가지고 문서별 같은 내용을 매핑하고 QA 생성은 포함되어 있지 않음

---

## 폴더 구조

### 기본 코드 및 폴더
```
parser_samsung/                 # 최상위 폴더
├── Readme.md                   # 사용 방법
├── labeling_guide.pptx         # 라벨링 가이드
├── pdf_parsing_guide.pptx      # PDF Parsing Data 생성 가이드
├── setup_parsing_samsung.txt   # 파이썬 및 라이브러리 버전
├── main.py                     # 메인 코드 (pdf parser 생성시 실행)
├── utils/                      # 유틸 파일 폴더
    ├── utils_pdf.py            # pdf 로드 및 pdf 데이터 추출 코드
    ├── utils_yolo.py           # pdf 레이아웃 탐지용 코드 (라벨링이 되어 있으면 생략)
    └── utils_parsing.py        # 객체별 순서 및 parsing data 생성시 필요한 각종 후처리 알고리즘 코드
├── weights/                    # yolo 모델 웨이트 폴더
    └── best.pt                 # (현재 yolov11x 모델 사용)
├── move_data.py                # pdf 레이아웃 데이터 라벨링 코드
├── pdf_to_image.py             # 새로운 pdf를 이미지로 변화하는 코드
├── datasets_labels.py          # 새로운 pdf를 이미지로 변환 한 다음(수동으로 진행 필요), 자동으로 라벨링하는 코드
└── line_merge.py               # parsing data 검수 전, 줄바꿈 부분을 띄어쓰기로 처리하는 코드
```
### 데이터 파일 및 폴더
```
parser_samsung/                 # 최상위 폴더
├── pdf/                        # 분석하고자 하는 pdf를 모아놓은 폴더
    ├── pdf1.pdf                # pdf 파일
    ├── pdf2.pdf                #
    ├── ...
    └── pdfn.pdf                # 
├── temp_data/                  # pdf 라벨링 데이터
    ├── pdf1/                   # 라벨링된 pdf 폴더
        ├── images/             # yolo 결과 폴더
            ├── 0.jpg           # 객체 탐지가 표시된 이미지
            ├── 1.jpg           # 
            ├── ...
            └── n.jpg           # 
        ├── labels/             # 박스 영역 라벨 데이터
            ├── 0.txt           # 레벨 데이터 (class x y w h)
            ├── 1.txt           # 
            ├── ...
            └── n.txt           # 
        └── ori_images/         # pdf 페이지별 이미지 폴더
            ├── 0.jpg           # pdf 페이지별 이미지
            ├── 1.jpg           # 
            ├── ...
            └── n.jpg           # 
    ├── pdf2/                   # 
    ├── ...
    └── pdfn/                   # 
```
### 결과물 파일 및 폴더
```
parser_samsung/                 # 최상위 폴더
├── pdf_parser_results/         # parsing data 생성 폴더
    ├── pdf1.xlsx               # pdf1에 대한 최종 parsing data 파일
    ├── pdf2.xlsx               # 
    ├── ...
    └── pdfn.xlsx               # 
├── pdf_results/                # pdf 추출 데이터
    ├── debug_regions/          # 영역 확인용 디버그 폴더
        ├── pdf1/               # 
            ├── 0.jpg           # 
            ├── 1.jpg           # 
            ├── ...
            └── n.jpg           # 
        ├── pdf2/               # 
        ├── ...
        └── pdfn/               # 
    ├── pdf_elements/           # 페이지별 이미지, 표, 아이콘 이미지 모음 폴더
        ├── pdf1/               # 
            ├── 0/              # 
                ├── 0.jpg       # 
                ├── 1.jpg       # 
                ├── ...
                └── n.jpg       # 
            ├── 1/              # 
            ├── ...
            └── n/              # 
        ├── pdf2/               # 
        ├── ...
        └── pdfn/               # 
    ├── pdf_refined_text/       # 페이지별 최종 수정된 텍스트 및 영역 순서
        ├── pdf1/               # 
            ├── 0.yaml          # 
            ├── 1.yaml          # 
            ├── ...
            └── n.yaml          # 
        ├── pdf2/               # 
        ├── ...
        └── pdfn/               # 
    ├── pdf_results_image/      # 페이지별 영역 탐지 결과
        ├── pdf1/               # 
            ├── 0.jpg           # 
            ├── 1.jpg           # 
            ├── ...
            └── n.jpg           # 
        ├── pdf2/               # 
        ├── ...
        └── pdfn/               # 
    ├── pdf_text/               # 페이지별 pdf 로더를 통한 텍스트 추출
        ├── pdf1/               # 
            ├── 0.txt           # 
            ├── 1.txt           # 
            ├── ...
            └── n.txt           # 
        ├── pdf2/               # 
        ├── ...
        └── pdfn/               # 
    └── pdf_yaml/               # 페이지별 최종 수정 전 텍스트 및 영역 순서
        ├── pdf1/               # 
            ├── 0.yaml          # 
            ├── 1.yaml          # 
            ├── ...
            └── n.yaml          # 
        ├── pdf2/               # 
        ├── ...
        └── pdfn/               # 
└── pdf_to_image/               # pdf 페이지를 이미지로 변환
    ├── pdf1/                   # 
        ├── 0.jpg               # 
        ├── 1.jpg               # 
        ├── ...
        └── n.jpg               # 
    ├── pdf2/                   # 
    ├── ...
    └── pdfn/                   # 
```

---

## 기능 (실행 순서)

---

### 1. PDF 레이아웃 라벨링

pdf를 기존 레이아웃 탐지 모델로 라벨링을 진행
1. (pdf를 이미지로 변환하여 'temp_data/pdf이름/ori_images/'에 0번부터 시작하여 페이지를 순차적으로 저장) 경로 지정 후 pdf_to_image.py 코드 실행
2. datasets_labels.py 코드를 실행 (기존에 라벨링을 진행한 폴더랑 다른 폴더를 사용해야함)
- (기존 폴더 사용시 폴더 내 모든 데이터를 덮어쓰게됨)
- label_path로 temp_data을 지정 ('temp_data/pdf이름/ori_images/'에 저장됨)
- pdf_path로 pdf가 존재하는 폴더 경로를 지정
3. 결과값 저장
- 'temp_data/pdf이름/labels/'에 라벨값 저장
- 'temp_data/pdf이름/images/'에 라벨링 결과 이미지 저장

---

### 2. 라벨링 툴을 이용하여 라벨링 결과 검수

객체탐지 모델 사용시, 신규 설명서는 체감상 90프로 정도의 정확도를 가지므로 질 좋은 Parsing Data를 생성하기 위해 검수가 꼭 필요함
- (학습 결과 모든 클래스에 대해 P: 0.967, R: 0.954, mAP50: 0.973, mAP50-95: 0.939)
1. move_data.py 실행
- label_path에 (검수하고자 하는 라벨값이 저장된 폴더) temp_data을 지정
- 라벨링 가이드를 참고하여 라벨링을 진행

---

### 3. PDF Parsing Data 생성

pdf와 라벨링 정보를 이용하여 Parsing Data를 생성
1. main.py 실행
- pdf_path에 폴더 경로 또는 파일 경로 지정
- labeling_data에 해당 pdf의 라벨링된 폴더를 지정 (지정하지 않거나 없을 시 자동으로 진행 -> 성능 하락)
2. 결과값 저장
- 'pdf_parsing_results/'에 해당 pdf명 + .xlsx로 저장

---

### 4. Parsing Data 검수 전 전처리

검수의 편의성을 위해 pdf의 줄바꿈을 검수 이전에 전처리로 진행
1. line_merge.py 실행
- 검수 된 dqa 폴더 지정
- 엑셀 시트 번호 중요 (기본 0 (두번째 시트)로 정의되어 있음)

---

### 5. Pasring Data 검수

자동으로 불가능한 부분을 해결하기 위해 직접 검수를 진행
- 대제목, 중제목, 소제목으로 구분하지 못하는 더 세부적인 타이틀을 내용으로 이동
- 소제목이 연속으로 등장할 시 누락되는 소제목 처리
- 경고, 주의, 참고가 어디까지인지를 명확하게 구분하지 못함
- 일반적인 내용 흐름이 아닌 특수한 흐름인 경우, 내용 순서를 수정
- 라벨링 시 잘못된 라벨링으로 인한 오류

---

## 설치

setup_parsing_samsung.txt 파일 내 파이썬 버전 및 라이브러리 버전 정보 기록
