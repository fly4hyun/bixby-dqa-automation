###################################################################################################
###################################################################################################

import os
import pdfplumber
from pdf2image import convert_from_path
import yaml
import regex
from PIL import Image

###################################################################################################
###################################################################################################
### 박스 iou 계산산
def boxes_overlap(box1, box2, iou_threshold=0.00001):
    def calc_iou(a, b):
        x1, y1, x2, y2 = a
        ox1, oy1, ox2, oy2 = b
        inter_x1 = max(x1, ox1)
        inter_y1 = max(y1, oy1)
        inter_x2 = min(x2, ox2)
        inter_y2 = min(y2, oy2)
        iw = max(0, inter_x2 - inter_x1)
        ih = max(0, inter_y2 - inter_y1)
        inter_area = iw * ih
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (ox2 - ox1) * (oy2 - oy1)
        union_area = area1 + area2 - inter_area
        if union_area == 0:
            return 0.0
        return inter_area / union_area
    return calc_iou(box1, box2) > iou_threshold

###################################################################################################
### 박스 iom 계산
def boxes_overlap_iom(box1, box2, iou_threshold=0.5):
    def calc_iou(a, b):
        x1, y1, x2, y2 = a
        ox1, oy1, ox2, oy2 = b
        inter_x1 = max(x1, ox1)
        inter_y1 = max(y1, oy1)
        inter_x2 = min(x2, ox2)
        inter_y2 = min(y2, oy2)
        iw = max(0, inter_x2 - inter_x1)
        ih = max(0, inter_y2 - inter_y1)
        inter_area = iw * ih
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (ox2 - ox1) * (oy2 - oy1)
        union_area = min(area1, area2)
        if union_area == 0:
            return 0.0
        return inter_area / union_area
    return calc_iou(box1, box2) > iou_threshold

###################################################################################################
###################################################################################################
### pdf 파일 로드 및 이미지 저장
class LoadPDF:
    
    def __init__(self, pdf_path, pdf_to_image_path):
        self.pdf_path = pdf_path
        self.pdf_to_image_path = pdf_to_image_path
        
        self.pdf_name = pdf_path.split('/')[-1].split('.')[0]
        self.pdf_name = self.pdf_name.split('\\')[-1]
        
        self.destination_folder = os.path.join(pdf_to_image_path, self.pdf_name)
        
        if not os.path.exists(self.destination_folder):
            os.makedirs(self.destination_folder)
            try:
                self.convert_pdf_to_images()
            except Exception as e:
                print("에러", f"PDF 변환 실패: {e}")
                return
    
    ###############################################################################################
    ### pdf 파일을 이미지로 변환
    def convert_pdf_to_images(self):
        pdf_images = convert_from_path(self.pdf_path)
        for i, image in enumerate(pdf_images):
            image_path = os.path.join(self.destination_folder, f"{i}.jpg")
            image.save(image_path)
    
    ###############################################################################################
    ### 이미지 리스트 로드
    def load_image_list(self):
        image_list = []
        for image in os.listdir(self.destination_folder):
            image_list.append(os.path.join(self.destination_folder, image))
        return image_list
    
    ###############################################################################################
    ### pdf 파일을 텍스트로 변환하여 저장
    def pdf_load_text_save(self, pdf_to_text_path):
        with pdfplumber.open(self.pdf_path) as pdf:
            num_pages = len(pdf.pages)
            for i in range(num_pages):
                page = pdf.pages[i]
                ### text가 없으면 빈 문자열 할당
                text = page.extract_text() or ""  

                ### 저장할 폴더 생성
                text_folder = os.path.join(pdf_to_text_path, self.pdf_name)
                os.makedirs(text_folder, exist_ok=True)

                ### txt 파일 저장
                text_file_path = os.path.join(text_folder, f"{i}.txt")
                with open(text_file_path, 'w', encoding='utf-8') as text_file:
                    ### text가 없으면 빈 파일 생성
                    text_file.write(text)  

###################################################################################################
###################################################################################################
### pdf 객체 탐지 및 라벨 로드
class YamlProcessor:
    def __init__(self, pdf_path, pdf_to_text_path, pdf_refined_text_path, labeling_path):
        self.pdf_path = pdf_path
        self.pdf_to_text_path = pdf_to_text_path
        self.pdf_refined_text_path = pdf_refined_text_path
        self.labeling_path = labeling_path
        self.pdf_name = pdf_path.split('/')[-1].split('.')[0]
        self.pdf_name = self.pdf_name.split('\\')[-1]
        self.class_names = [
            "대제목", "섹션 박스", "중제목", "소제목", "내용", "이미지/표 박스",
            "이미지", "표", "아이콘_내용", "페이지 번호", "아이콘", "목차"
        ]
    
    ###############################################################################################
    ### 텍스트 숫자 근처 텍스트 처리 (OCR 기준)
    def add_space_around_numbers(self, text):
        text = regex.sub(r'(\d)([^\d\s.,!?])', r'\1 \2', text)
        text = regex.sub(r'([^\d\s.,!?])(\d)', r'\1 \2', text)
        text = regex.sub(r'([a-zA-Z])([가-힣])', r'\1 \2', text)
        text = regex.sub(r'([가-힣])([a-zA-Z])', r'\1 \2', text)
        text = regex.sub(r'([.,!?])([^\s\d])', r'\1 \2', text)
        return text
    
    ###############################################################################################
    ### 텍스트 파일 로드
    def load_txt_content(self, page_num):
        txt_file_path = os.path.join(self.pdf_to_text_path, self.pdf_name, f"{page_num}.txt")
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        content = self.add_space_around_numbers(content)
        return content

    ###############################################################################################
    ###############################################################################################
    ### 부모 OCR 텍스트(문자열)를 한 줄로 취급하여,
    ### 부모 bbox와 아이콘_내용 박스의 수평 위치를 기준으로 적절한 위치에 "<아이콘/>"을 삽입하는 함수
    def merge_text_with_multiple_icons(self, page, parent_bbox, icon_bboxes):
        """
        부모 영역(parent_bbox) 내의 OCR 단어를 줄 단위로 그룹화하고,
        각 줄에 대해 아이콘_내용(icon_bboxes)이 세로로 충분히 겹치면(≥50% overlap)
        해당 줄에서 아이콘 위치에 따라 좌측, 아이콘, 우측 영역으로 분할하여
        각 영역의 OCR 텍스트를 추출합니다.
        
        조건)
        - 한 줄의 OCR 단어들은 vertical 위치(예: 'top')가 비슷한 것끼리 묶습니다.
        - 아이콘이 해당 줄의 높이와 50% 이상 겹치면 그 줄에 속하는 것으로 봅니다.
        - 한 줄 내에서 아이콘이 여러 개라면, 각 아이콘의 x좌표 순서대로 영역을 나누고,
            아이콘 부분은 강제 "<아이콘/>" 표시로 대체합니다.
        
        반환)
        줄별 결과를 개행 문자로 연결한 최종 텍스트.
        """
        p_x0, p_y0, p_x1, p_y1 = parent_bbox

        ###########################################################################################
        ### 부모 영역 내 전체 OCR 단어 추출 (부모 bbox 내부에 중심이 포함된 단어)
        all_words = page.extract_words()
        parent_words = []
        for w in all_words:
            cx = (w['x0'] + w['x1']) / 2.0
            cy = (w['top'] + w['bottom']) / 2.0
            if p_x0 <= cx <= p_x1 and p_y0 <= cy <= p_y1:
                parent_words.append(w)

        if not parent_words:
            return ""
        
        ###########################################################################################
        ### 1. 단어들을 vertical 위치(예: top) 기준으로 그룹화하여 줄(line) 단위로 묶기
        parent_words.sort(key=lambda w: w['top'])
        ### 각 줄은 단어 리스트
        lines = []
        ### pt 단위, 같은 줄로 간주할 vertical 차이 임계치
        line_threshold = 5  
        for w in parent_words:
            if not lines:
                lines.append([w])
            else:
                current_line = lines[-1]
                avg_top = sum(word['top'] for word in current_line) / len(current_line)
                if abs(w['top'] - avg_top) <= line_threshold:
                    current_line.append(w)
                else:
                    lines.append([w])
        
        ###########################################################################################
        ### 각 줄의 bbox 계산
        line_boxes = []
        for line in lines:
            min_x = min(w['x0'] for w in line)
            max_x = max(w['x1'] for w in line)
            min_y = min(w['top'] for w in line)
            max_y = max(w['bottom'] for w in line)
            line_boxes.append((min_x, min_y, max_x, max_y))

        ###########################################################################################
        ### 2. 각 줄별로 처리: 해당 줄에 포함되는 아이콘을 판단
        line_results = []
        for idx, line_box in enumerate(line_boxes):
            l_x0, l_y0, l_x1, l_y1 = line_box
            ### 해당 줄의 OCR 단어 (이미 정렬된 parent_words 중 해당 줄 bbox에 포함)
            line_words = [w for w in lines[idx] if w['x0'] >= l_x0 and w['x1'] <= l_x1]
            ### 기본 줄 텍스트(아이콘이 없을 경우)
            line_text = " ".join(w['text'] for w in sorted(line_words, key=lambda w: w['x0'])).strip()

            ### 해당 줄에 속하는 아이콘: vertical overlap 비율 계산
            icons_in_line = []
            line_height = l_y1 - l_y0
            for ibox in icon_bboxes:
                i_x0, i_y0, i_x1, i_y1 = ibox
                ### 아이콘과 줄의 vertical overlap 계산
                overlap = max(0, min(l_y1, i_y1) - max(l_y0, i_y0))
                if line_height > 0 and (overlap / line_height) >= 0.5:
                    icons_in_line.append(ibox)
            ### x좌표 순으로 정렬
            icons_in_line.sort(key=lambda box: box[0])

            if not icons_in_line:
                ### 아이콘이 없는 줄은 그대로 사용
                line_results.append(line_text)
            else:
                ### 한 줄 내에서 아이콘이 있으면, 좌측/아이콘/우측 영역으로 분할
                segments = []
                current_x = l_x0
                ### 줄의 OCR 단어를 x좌표 기준으로 정렬
                line_words_sorted = sorted(line_words, key=lambda w: w['x0'])
                for icon in icons_in_line:
                    i_x0, i_y0, i_x1, i_y1 = icon
                    ### 좌측 영역: current_x ~ 아이콘의 x0
                    if i_x0 > current_x:
                        seg_words = [w for w in line_words_sorted if current_x <= w['x0'] < i_x0]
                        seg_text = " ".join(w['text'] for w in seg_words)
                        if seg_text:
                            segments.append(seg_text)
                    ### 아이콘 영역: 강제 "<아이콘/>"
                    segments.append("<아이콘/>")
                    current_x = i_x1
                ### 우측 영역: 마지막 아이콘 이후 영역
                if current_x < l_x1:
                    seg_words = [w for w in line_words_sorted if current_x <= w['x0'] <= l_x1]
                    seg_text = " ".join(w['text'] for w in seg_words)
                    if seg_text:
                        segments.append(seg_text)
                ### 한 줄 결과: 세그먼트를 공백으로 연결
                line_result = " ".join(segments).strip()
                line_results.append(line_result)

        ###########################################################################################
        ### 3. 최종 결과: 각 줄을 개행 문자로 연결
        final_text = "\n".join(line_results)
        return final_text
    
    ###############################################################################################
    ### 전체 노드들 중, 클래스 2(소제목) 또는 3(내용) 노드와 겹치는 아이콘_내용(클래스 7) 노드가 있으면,
    ### 해당 노드의 bbox를 PDF 좌표로 변환한 후, 겹치는 경우에 한해서 부모의 OCR 텍스트를
    ### merge_text_with_icon 함수를 통해 업데이트하고, (필요하다면) 새로운 노드로 분할
    def split_boxes_by_icon(self, nodes, page, scale_x, scale_y):
        """
        노드 리스트 중 클래스 2(소제목) 또는 3(내용) 노드에 대해,
        아이콘_내용(클래스 7) 노드와 겹치는 경우,
        이미지 좌표의 bbox를 PDF 좌표로 변환한 후 부모 영역 내의 OCR 텍스트를
        위의 merge_text_with_multiple_icons()를 사용해 재구성
        
        매개변수:
        nodes   : 전체 노드 리스트 (각 노드 bbox는 이미지 좌표)
        page    : pdfplumber PDF 페이지 객체
        scale_x : 이미지 좌표 → PDF 좌표 변환 계수 (가로)
        scale_y : 이미지 좌표 → PDF 좌표 변환 계수 (세로)
        """
        new_nodes = []
        for nd in nodes:
            if nd.get("children"):
                nd["children"] = self.split_boxes_by_icon(nd["children"], page, scale_x, scale_y)
            if nd["cls"] in [2, 3, 4]:
                orig_bbox = nd["bbox"]
                conv_bbox = [orig_bbox[0] * scale_x,
                            orig_bbox[1] * scale_y,
                            orig_bbox[2] * scale_x,
                            orig_bbox[3] * scale_y]
                overlapping_icons = []
                for other in nodes:
                    if other["cls"] == 8:
                        obb = other["bbox"]
                        conv_obb = [obb[0] * scale_x,
                                    obb[1] * scale_y,
                                    obb[2] * scale_x,
                                    obb[3] * scale_y]
                        if boxes_overlap_iom(conv_bbox, conv_obb):
                            overlapping_icons.append(conv_obb)
                if overlapping_icons:
                    new_text = self.merge_text_with_multiple_icons(page, conv_bbox, overlapping_icons)
                    nd["ocr_text"] = [new_text]
            new_nodes.append(nd)
        return new_nodes

    ###############################################################################################
    ### 노드를 yaml 형식으로 변환
    def node_to_yaml(self, nd, txt_content):
        c_ = nd["cls"]
        cname = self.class_names[c_] if 0 <= c_ < len(self.class_names) else f"cls_{c_}"
        ### 아이콘_내용(클래스 7)은 "<아이콘/>"을 단일 항목의 리스트로 설정
        if c_ == 8:
            ocr_text = ["<아이콘/>"]
        else:
            ### 만약 자식 중에 아이콘_내용(클래스 7)이 있다면(분할되어 있다면), 해당 노드의 ocr_text는 이미 분할된 리스트
            ### 관련 없는 텍스트는 join하지 않고 원본 리스트 그대로 유지
            ocr_text = nd["ocr_text"]
        return {
            "bbox": nd["bbox"],
            "cls": c_,
            "class_name": cname,
            "order": nd["order"],
            "ocr_text": ocr_text,
            "text_start_line": nd["text_start_line"], 
            "element_path": nd.get("element_path", None),
            "children": [self.node_to_yaml(ch, txt_content) for ch in nd.get("children", [])]
        }
    
    ###############################################################################################
    ### yaml 파일 처리
    def process_yaml(self):
        for page_num in range(len(os.listdir(os.path.join(self.pdf_to_text_path, self.pdf_name)))):
            input_yaml_path = os.path.join('pdf_results/pdf_yaml', self.pdf_name, f"{page_num}.yaml")
            output_yaml_path = os.path.join(self.pdf_refined_text_path, self.pdf_name, f"{page_num}.yaml")
            if not os.path.exists(os.path.dirname(output_yaml_path)):
                os.makedirs(os.path.dirname(output_yaml_path))
            txt_content = self.load_txt_content(page_num)
            
            with open(input_yaml_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            ### PDF 페이지 객체와 이미지 크기에서 scale factor 계산
            image_path = os.path.join("pdf_results", "pdf_results_image", self.pdf_name, f"{page_num}.jpg")
            im = Image.open(image_path)
            image_width, image_height = im.size
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_num]
                pdf_bbox = page.bbox  # (pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                pdf_width = pdf_bbox[2] - pdf_bbox[0]
                pdf_height = pdf_bbox[3] - pdf_bbox[1]
                scale_x = pdf_width / image_width
                scale_y = pdf_height / image_height
                nodes = data['boxes']
                ### split_boxes_by_icon: 부모 노드에서 아이콘_내용 겹치는 경우 OCR 텍스트 업데이트
                nodes = self.split_boxes_by_icon(nodes, page, scale_x, scale_y)
            
            data_for_yaml = [self.node_to_yaml(n, txt_content) for n in nodes]
            with open(output_yaml_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump({"boxes": data_for_yaml}, f, allow_unicode=True, sort_keys=False)

###################################################################################################
###################################################################################################