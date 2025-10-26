###################################################################################################
###################################################################################################

import os
import re
import yaml
from PIL import Image, ImageDraw, ImageFont
import pdfplumber

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
### 두 내용이 같은 줄에 있는지 확인
def is_same_line(box1, box2, overlap_threshold=0.5):
    x1, y1, x2, y2 = box1
    ox1, oy1, ox2, oy2 = box2
    h1 = y2 - y1
    h2 = oy2 - oy1
    inter_top = max(y1, oy1)
    inter_bottom = min(y2, oy2)
    overlap_h = inter_bottom - inter_top
    if overlap_h <= 0:
        return False
    min_h = min(h1, h2)
    ratio = overlap_h / float(min_h)
    return ratio >= overlap_threshold

###################################################################################################
### 박스 내부에 다른 박스가 있는지 확인
def box_in(parent_box, child_box):
    px1, py1, px2, py2 = parent_box
    cx1, cy1, cx2, cy2 = child_box
    return (cx1 >= px1) and (cy1 >= py1) and (cx2 <= px2) and (cy2 <= py2)

###################################################################################################
###################################################################################################
### 겹치는 박스를 병합하는 함수
def merge_overlapping_boxes_ext(boxes_ext):
    merged = []
    for (x1, y1, x2, y2, cls_, ocrs, _) in boxes_ext:
        found = False
        ### 7개 요소를 모두 언패킹 (마지막 요소는 사용하지 않음)
        for i, (mx1, my1, mx2, my2, mcls, mocrs, _) in enumerate(merged):
            if cls_ == mcls and boxes_overlap((x1, y1, x2, y2), (mx1, my1, mx2, my2)):
                nx1, ny1 = min(x1, mx1), min(y1, my1)
                nx2, ny2 = max(x2, mx2), max(y2, my2)
                merged[i] = (nx1, ny1, nx2, ny2, cls_, mocrs + ocrs, '')
                found = True
                break
        if not found:
            merged.append((x1, y1, x2, y2, cls_, ocrs, ''))
    return merged

###################################################################################################
### 섹션 박스 영역 확장
def expand_section_box(boxes_ext):
    target = 1
    inc = [2, 3, 4, 5, 6, 7, 8, 10]
    out = []
    for i, (x1, y1, x2, y2, cls_, ocrs, _) in enumerate(boxes_ext):
        if cls_ != target:
            out.append((x1, y1, x2, y2, cls_, ocrs, ''))
            continue
        for j, (ox1, oy1, ox2, oy2, ocls, _, _) in enumerate(boxes_ext):
            if i == j: continue
            if ocls in inc and boxes_overlap((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                x1, y1 = min(x1, ox1), min(y1, oy1)
                x2, y2 = max(x2, ox2), max(y2, oy2)
        out.append((x1, y1, x2, y2, cls_, ocrs, ''))
    return out

###################################################################################################
### 이미지/표 박스 영역 확장
def expand_image_table_box(boxes_ext):
    target = 5
    inc = [2, 3, 4, 6, 7, 8, 10]
    res = []
    for i, (x1, y1, x2, y2, cls_, ocrs, _) in enumerate(boxes_ext):
        if cls_ != target:
            res.append((x1, y1, x2, y2, cls_, ocrs, ''))
            continue
        for j, (ox1, oy1, ox2, oy2, ocls, _, _) in enumerate(boxes_ext):
            if i == j: continue
            if ocls in inc and boxes_overlap((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                x1, y1 = min(x1, ox1), min(y1, oy1)
                x2, y2 = max(x2, ox2), max(y2, oy2)
        res.append((x1, y1, x2, y2, cls_, ocrs, ''))
    return res

###################################################################################################
### 박스 영역 후처리리
def postprocess_boxes(boxes_ext):
    for _ in range(2):
        boxes_ext = merge_overlapping_boxes_ext(boxes_ext)
    boxes_ext = expand_section_box(boxes_ext)
    boxes_ext = expand_image_table_box(boxes_ext)
    return boxes_ext

###################################################################################################
###################################################################################################
### pdfplumber로 추출한 단어 정보를 사용하여 OCR 확장
def expand_boxes_with_ocr(raw_boxes, ocr_data):
    exclude_cls = [6, 7, 8, 10]
    line_sens = [2, 3, 4]
    out = []
    for (rx1, ry1, rx2, ry2, rcls) in raw_boxes:
        x1, y1, x2, y2 = float(rx1), float(ry1), float(rx2), float(ry2)
        c = int(rcls)
        out.append([x1, y1, x2, y2, c, [], ''])
    for idx, (x1, y1, x2, y2, cls_, ocrs, _) in enumerate(out):
        if cls_ in exclude_cls:
            continue

        ### 제목(클래스 0)은 박스 확장을 하지 않고, 원본 영역 내 단어만 추가
        if cls_ == 0:
            for (ox1, oy1, ox2, oy2, txt, conf) in ocr_data:
                if box_in((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                    ocrs.append(str(txt))
            continue

        ### 라인 감지
        if cls_ in line_sens:
            new_x1, new_y1, new_x2, new_y2 = x1, y1, x2, y2
            for (ox1, oy1, ox2, oy2, txt, conf) in ocr_data:
                if boxes_overlap((new_x1, new_y1, new_x2, new_y2), (ox1, oy1, ox2, oy2)):
                    if is_same_line((new_x1, new_y1, new_x2, new_y2), (ox1, oy1, ox2, oy2)):
                        new_x1 = min(new_x1, ox1)
                        new_x2 = max(new_x2, ox2)
                        ocrs.append(str(txt))
            out[idx][0] = new_x1
            out[idx][1] = new_y1
            out[idx][2] = new_x2
            out[idx][3] = new_y2
        else:
            ### 나머지 클래스는 박스 확장을 수행
            new_x1, new_y1, new_x2, new_y2 = x1, y1, x2, y2
            for (ox1, oy1, ox2, oy2, txt, conf) in ocr_data:
                if boxes_overlap((new_x1, new_y1, new_x2, new_y2), (ox1, oy1, ox2, oy2)):
                    new_x1 = min(new_x1, ox1)
                    new_y1 = min(new_y1, oy1)
                    new_x2 = max(new_x2, ox2)
                    new_y2 = max(new_y2, oy2)
                    ocrs.append(str(txt))
            out[idx][0] = new_x1
            out[idx][1] = new_y1
            out[idx][2] = new_x2
            out[idx][3] = new_y2
    return out

###################################################################################################
###################################################################################################
### 박스 순서 정렬렬
def sort_and_enumerate_boxes(final_boxes):
    if not final_boxes:
        return []

    page_boxes = [list(b) for b in final_boxes if b[4] == 9]
    other_boxes = [list(b) for b in final_boxes if b[4] != 9]

    xs = [x for b in other_boxes for x in (b[0], b[2])]
    midx = (min(xs) + max(xs)) / 2.0 if xs else 0
    
    ###############################################################################################
    ### 박스의 위치에 따른 순서 지정
    def refine_sorting(boxes):
        n = len(boxes)
        i = 0
        while i < n - 1:
            if boxes[i][0] > boxes[i + 1][2] and boxes[i][3] > boxes[i + 1][1]:
                boxes[i], boxes[i + 1] = boxes[i + 1], boxes[i]
                i = max(i - 1, 0)
            else:
                i += 1
        return boxes

    ###############################################################################################
    ### 박스가 투컬럼인지 원컬럼인지를 고려한 정렬 함수
    def sort_boxes(boxes):
        sorted_boxes = []
        current_group = []
        current_type = None
        for box in sorted(boxes, key=lambda b: b[1]):
            x1, x2 = box[0], box[2]
            if x2 < midx:
                column_type = 'two_column'
            elif x1 > midx:
                column_type = 'two_column'
            else:
                column_type = 'single'
            if column_type != current_type and current_group:
                if current_type == 'single':
                    sorted_boxes.extend(sorted(current_group, key=lambda b: b[1]))
                    sorted_boxes = refine_sorting(sorted_boxes)
                else:
                    left_part = [b for b in current_group if b[2] < midx]
                    right_part = [b for b in current_group if b[0] > midx]
                    left_part.sort(key=lambda b: b[1])
                    right_part.sort(key=lambda b: b[1])
                    left_part = refine_sorting(left_part)
                    right_part = refine_sorting(right_part)
                    sorted_boxes.extend(left_part + right_part)
                current_group = []
            current_group.append(box)
            current_type = column_type
        if current_group:
            if current_type == 'single':
                sorted_boxes.extend(sorted(current_group, key=lambda b: b[1]))
                sorted_boxes = refine_sorting(sorted_boxes)
            else:
                left_part = [b for b in current_group if b[2] < midx]
                right_part = [b for b in current_group if b[0] > midx]
                left_part.sort(key=lambda b: b[1])
                right_part.sort(key=lambda b: b[1])
                left_part = refine_sorting(left_part)
                right_part = refine_sorting(right_part)
                sorted_boxes.extend(left_part + right_part)
        return sorted_boxes

    sorted_other_boxes = sort_boxes(other_boxes)
    page_list = sorted(page_boxes, key=lambda b: b[1])
    sorted_boxes = sorted_other_boxes + page_list

    processed_boxes = []
    for i, box in enumerate(sorted_boxes, start=1):
        if len(box) == 7:
            box.append(i)
        processed_boxes.append(box)
    return [tuple(box) for box in processed_boxes]

###################################################################################################
###################################################################################################
### 트리 구성 (중복제거 및 부모-자식 할당)
def build_tree_no_duplicate(final_sorted):
    def box_in(parent_box, child_box):
        px1, py1, px2, py2 = parent_box
        cx1, cy1, cx2, cy2 = child_box
        return (cx1 >= px1) and (cy1 >= py1) and (cx2 <= px2) and (cy2 <= py2)

    newt = []
    for (x1, y1, x2, y2, cls_, ocrs, sl, od_) in final_sorted:
        ocr_tuple = tuple(ocrs)
        newt.append((x1, y1, x2, y2, cls_, ocr_tuple, sl, od_))

    top_nodes_map = {}
    for b_t in newt:
        x1, y1, x2, y2, c_, oc, sl, or_ = b_t
        node = {
            "cls": c_,
            "bbox": [x1, y1, x2, y2],
            "ocr_text": list(oc), 
            "text_start_line": sl,
            "order": or_,
            "children": []
        }
        top_nodes_map[b_t] = node

    assigned = set()
    for pkey, pnode in list(top_nodes_map.items()):
        if pnode["cls"] == 5:
            px1, py1, px2, py2 = pnode["bbox"]
            valid_child_found = False
            for ckey, cnode in list(top_nodes_map.items()):
                bx1, by1, bx2, by2, bcls, _, _, _ = ckey
                if bcls in [6, 7] and box_in((px1, py1, px2, py2), (bx1, by1, bx2, by2)):
                    valid_child_found = True
                    break
            if not valid_child_found:
                top_nodes_map.pop(pkey)
    for pkey, pnode in list(top_nodes_map.items()):
        if pnode["cls"] == 5:
            px1, py1, px2, py2 = pnode["bbox"]
            child_list = []
            for ckey in list(top_nodes_map.keys()):
                if ckey in assigned or ckey == pkey:
                    continue
                bx1, by1, bx2, by2, bcls, boc, bsl, bord = ckey
                if bcls in [2, 3, 4, 6, 7, 8, 10]:
                    if box_in((px1, py1, px2, py2), (bx1, by1, bx2, by2)):
                        child_node = top_nodes_map[ckey]
                        child_list.append(child_node)
                        assigned.add(ckey)
                        top_nodes_map.pop(ckey, None)
            pnode["children"].extend(child_list)
    for pkey, pnode in list(top_nodes_map.items()):
        if pnode["cls"] == 1:
            px1, py1, px2, py2 = pnode["bbox"]
            child_list = []
            for ckey in list(top_nodes_map.keys()):
                if ckey in assigned or ckey == pkey:
                    continue
                bx1, by1, bx2, by2, bcls, boc, bsl, bord = ckey
                if bcls in [2, 3, 4, 5, 6, 7, 8, 10]:
                    if box_in((px1, py1, px2, py2), (bx1, by1, bx2, by2)):
                        child_node = top_nodes_map[ckey]
                        child_list.append(child_node)
                        assigned.add(ckey)
                        top_nodes_map.pop(ckey, None)
            pnode["children"].extend(child_list)
    top_nodes = list(top_nodes_map.values())
    return top_nodes

###################################################################################################
###################################################################################################
### 부모-자식 DFS 전위순회 => 최종 order 할당
def assign_order_dfs(top_nodes):
    c = [1]
    def dfs(n):
        n["order"] = c[0]
        c[0] += 1
        for ch in n["children"]:
            dfs(ch)
    for nd in top_nodes:
        dfs(nd)

###################################################################################################
###################################################################################################
### pdfplumber로 추출한 단어 정보를 사용하여 OCR
class DetectionYOLO:
    
    def __init__(self, yolo_model, ocr_model, labeling_path, pdf_path, save_image=True):
        self.model = yolo_model
        self.ocr = ocr_model
        self.labeling_path = labeling_path
        self.pdf_path = pdf_path
        self.save_image = save_image
        self.class_names = [
            "대제목", "섹션 박스", "중제목", "소제목", "내용", "이미지/표 박스",
            "이미지", "표", "아이콘_내용", "페이지 번호", "아이콘", "목차"
        ]
        self.class_colors = [
            "#FF4500", "#1E90FF", "#FF1493", "#32CD32", "#FFD700", "#8B008B",
            "#00CED1", "#FF8C00", "#9400D3", "#FF1493", "#696969", "#8B4513"
        ]
        self.element_names = [
            "title", "section", "subtitle", "lasttitle", "content", "image_table",
            "image", "table", "icon_content", "page", "icon", "toc"
        ]

    ###############################################################################################
    ### pdfplumber로 PDF에서 단어 단위 OCR 데이터 추출 및 이미지 좌표로 변환
    def detect_and_postprocess(self, image_list, pdf_name):

        img_outdir = os.path.join("pdf_results", "pdf_results_image", pdf_name)
        elements_outdir = os.path.join("pdf_results", "pdf_elements", pdf_name)
        yaml_outdir = os.path.join("pdf_results", "pdf_yaml", pdf_name)
        os.makedirs(img_outdir, exist_ok=True)
        os.makedirs(elements_outdir, exist_ok=True)
        os.makedirs(yaml_outdir, exist_ok=True)
        ### debug_regions 폴더에 모든 박스 영역(이미지 크롭 결과)을 저장
        debug_folder = os.path.join("pdf_results", "debug_regions", pdf_name)
        os.makedirs(debug_folder, exist_ok=True)

        ###########################################################################################
        ### (cid:숫자) 패턴을 모두 제거
        def remove_cid(text):
            return re.sub(r'\(cid:\d+\)', '', text)

        ###########################################################################################
        ### 입력 박스(image 좌표)를 PDF 좌표로 변환한 후,  
        ### 해당 영역 내 단어를 pdfplumber 페이지에서 추출하여 원래 줄 구조 그대로 반환
        def group_box_text_by_lines(page, box, scale_x, scale_y):
            """
            pdfplumber 페이지(page)에서, 이미지 좌표상의 box를 PDF 좌표로 변환한 영역 내 단어들을 추출한 후,
            각 단어를 수직 overlap 비율(새 단어와 현재 줄의 overlap/최소 높이)이 50% 이상이면 같은 줄로 그룹화
            이후, 인접한 줄들끼리도 vertical overlap 비율이 50% 이상이면 병합하여 원래 줄 구조(여러 줄)를 반환
            
            매개변수:
            page    : pdfplumber PDF 페이지 객체 (PDF 좌표 기준 단어 추출)
            box     : (x0, y0, x1, y1) 이미지 좌표상의 영역
            scale_x : 이미지→PDF 좌표 변환 계수 (가로)
            scale_y : 이미지→PDF 좌표 변환 계수 (세로)
            
            반환:
            각 줄 텍스트를 개행 문자로 이어 붙인 문자열과 각 줄의 시작 x좌표 리스트를 튜플로 리턴
            예) ("첫 번째 줄 텍스트\n두 번째 줄 텍스트", [start_x1, start_x2])
            """
            ### 이미지 좌표(box)를 PDF 좌표로 변환
            pdf_box = (box[0] / scale_x, box[1] / scale_y, box[2] / scale_x, box[3] / scale_y)
            x0, y0, x1, y1 = pdf_box

            words = page.extract_words()
            ### 필터: 중심이 해당 영역 내에 있는 단어들
            box_words = [w for w in words if ( (w['x0']+w['x1'])/2.0 >= x0 and (w['x0']+w['x1'])/2.0 <= x1 and 
                                            (w['top']+w['bottom'])/2.0 >= y0 and (w['top']+w['bottom'])/2.0 <= y1 )]
            if not box_words:
                return "", ''
            ### 세로(top), 가로(x0) 기준 정렬
            box_words.sort(key=lambda w: (w['top'], w['x0']))

            #######################################################################################
            ### 함수: 두 사각형의 vertical overlap 비율 (작은 높이에 대한 비율)을 계산
            def vertical_overlap_ratio(top1, bottom1, top2, bottom2):
                overlap = max(0, min(bottom1, bottom2) - max(top1, top2))
                h1 = bottom1 - top1
                h2 = bottom2 - top2
                if min(h1, h2) <= 0:
                    return 0
                return overlap / min(h1, h2)

            ### 단어들을 순차적으로 그룹화: 현재 줄의 bounding box와 새 단어의 overlap 비율이 0.5 이상이면 같은 줄로 취급
            lines = []
            current_line = [box_words[0]]
            ### 현재 줄의 bounding box (top, bottom)를 업데이트
            cur_top = box_words[0]['top']
            cur_bottom = box_words[0]['bottom']
            for w in box_words[1:]:
                w_top = w['top']
                w_bottom = w['bottom']
                ratio = vertical_overlap_ratio(cur_top, cur_bottom, w_top, w_bottom)
                if ratio >= 0.5:
                    current_line.append(w)
                    ### 업데이트: 현재 줄의 bounding box 확장
                    cur_top = min(cur_top, w_top)
                    cur_bottom = max(cur_bottom, w_bottom)
                else:
                    lines.append((current_line, cur_top, cur_bottom))
                    current_line = [w]
                    cur_top = w_top
                    cur_bottom = w_bottom
            if current_line:
                lines.append((current_line, cur_top, cur_bottom))

            ### 병합: 인접한 줄들끼리 vertical overlap 비율이 50% 이상이면 병합
            merged_lines = []
            cur_words, cur_top, cur_bottom = lines[0]
            for (words_line, top_line, bottom_line) in lines[1:]:
                ratio = vertical_overlap_ratio(cur_top, cur_bottom, top_line, bottom_line)
                if ratio >= 0.5:
                    ### 병합: 단어 리스트 합치고 bounding box 업데이트
                    cur_words.extend(words_line)
                    cur_top = min(cur_top, top_line)
                    cur_bottom = max(cur_bottom, bottom_line)
                else:
                    merged_lines.append(cur_words)
                    cur_words = words_line
                    cur_top = top_line
                    cur_bottom = bottom_line
            merged_lines.append(cur_words)

            ### 각 줄 내 단어들을 x좌표 기준 정렬하고 텍스트로 변환
            line_texts = []
            start_x_list = []
            for line in merged_lines:
                line.sort(key=lambda w: w['x0'])
                ### 각 줄의 시작 위치는 가장 왼쪽 단어의 x0 값
                start_x = line[0]['x0']
                start_x_list.append(str(start_x))
                text = " ".join(word['text'] for word in line)
                line_texts.append(text)
            return "\n".join(line_texts), "\n".join(start_x_list)

        for img_path in image_list:
            base_name = os.path.basename(img_path)
            file_root, _ = os.path.splitext(base_name)  ### 페이지 번호 (0부터 시작)
            page_folder = os.path.join(elements_outdir, file_root)
            os.makedirs(page_folder, exist_ok=True)

            #######################################################################################
            ### (A) pdfplumber로 PDF에서 단어 단위 OCR 데이터 추출 및 이미지 좌표로 변환
            with pdfplumber.open(self.pdf_path) as pdf:
                page_index = int(file_root)
                if page_index >= len(pdf.pages):
                    print(f"[WARNING] PDF 페이지 수보다 {page_index}가 큽니다.")
                    ocr_data = []
                    page = None
                else:
                    page = pdf.pages[page_index]
                    words = page.extract_words()
                    im = Image.open(img_path)
                    img_width, img_height = im.size
                    page_width = page.width
                    page_height = page.height
                    scale_x = img_width / page_width
                    scale_y = img_height / page_height
                    ocr_data = []
                    for w in words:
                        pdf_x0 = float(w['x0'])
                        pdf_y0 = float(w['top'])
                        pdf_x1 = float(w['x1'])
                        pdf_y1 = float(w['bottom'])
                        ### 단순 스케일 적용 (Y축 반전 없음)
                        img_x0 = pdf_x0 * scale_x
                        img_y0 = pdf_y0 * scale_y
                        img_x1 = pdf_x1 * scale_x
                        img_y1 = pdf_y1 * scale_y
                        
                        cleaned_text = remove_cid(w['text'])
                        ocr_data.append((img_x0, img_y0, img_x1, img_y1, cleaned_text, 1.0))

            #######################################################################################
            ### (B) 라벨 파일이 있으면 YOLO 검출 건너뛰고 라벨 박스 사용 (YOLO 형식: class cx cy w h, 정규화 좌표)
            label_file = os.path.join(self.labeling_path, pdf_name, "labels", f"{file_root}.txt")
            if os.path.exists(label_file):
                print(f"[INFO] {file_root}.txt 라벨 파일이 존재합니다. 라벨 박스와 클래스 정보만 사용합니다.")
                raw_boxes = []
                im = Image.open(img_path)
                width, height = im.size
                with open(label_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                cls_label = int(parts[0])
                                cx_norm, cy_norm, w_norm, h_norm = map(float, parts[1:5])
                                cx_abs = cx_norm * width
                                cy_abs = cy_norm * height
                                w_abs = w_norm * width
                                h_abs = h_norm * height
                                x1 = cx_abs - w_abs / 2
                                y1 = cy_abs - h_abs / 2
                                x2 = cx_abs + w_abs / 2
                                y2 = cy_abs + h_abs / 2
                                raw_boxes.append((x1, y1, x2, y2, cls_label))
                            except Exception as e:
                                print(f"[ERROR] 라벨 파일 파싱 에러: {e}")
                
                final_b = []
                for box in raw_boxes:
                    x1, y1, x2, y2, cls_label = box
                    ocrs = []
                    for (ox1, oy1, ox2, oy2, text, conf) in ocr_data:
                        if boxes_overlap_iom((x1, y1, x2, y2), (ox1, oy1, ox2, oy2)):
                            ocrs.append(text)
                    final_b.append((x1, y1, x2, y2, cls_label, ocrs, ''))
                
                final_b = expand_section_box(final_b)
                final_b = expand_image_table_box(final_b)
                
            else:
                ###################################################################################
                ### (C) 라벨 파일이 없으면 YOLO 검출 후, OCR 데이터와 결합하여 박스 확장
                results = self.model.predict(source=img_path, save=False, imgsz=640, verbose=False)
                raw_boxes = []
                for r_ in results:
                    box_ = r_.boxes.xyxy.cpu().numpy()
                    cls_ = r_.boxes.cls.cpu().numpy()
                    for (xx1, yy1, xx2, yy2), c_ in zip(box_, cls_):
                        x1, y1, x2, y2 = map(float, [xx1, yy1, xx2, yy2])
                        raw_boxes.append((x1, y1, x2, y2, int(c_)))
                b_ocr = expand_boxes_with_ocr(raw_boxes, ocr_data)
                final_b = postprocess_boxes(b_ocr)
            
            #######################################################################################
            ### (D) 영역 내 텍스트를 원래 영역(노드 박스) 그대로 읽어, 줄 단위(원래 줄 구조)로 구분
            if page is not None:
                for idx, node in enumerate(final_b):
                    x1, y1, x2, y2, cls_label, ocrs, _ = node
                    if cls_label in [0, 2, 3, 4, 11]:
                        new_text, start_line = group_box_text_by_lines(page, (x1, y1, x2, y2), scale_x, scale_y)
                        final_b[idx] = (x1, y1, x2, y2, cls_label, [new_text], start_line)

            #######################################################################################
            ### (D) 영역 정렬 및 임시 order 부여
            sorted_b = sort_and_enumerate_boxes(final_b)
            #######################################################################################
            ### (E) 트리 구성 (중복 제거 및 부모-자식 할당)
            top_nodes = build_tree_no_duplicate(sorted_b)
            #######################################################################################
            ### (F) DFS로 부모-자식 순서 할당
            assign_order_dfs(top_nodes)
            
            #######################################################################################
            ### 이미지 소제목 순서 변경경
            def swap_image_and_subtitle_in_box(node):
                ### node가 이미지/표 박스인 경우 처리
                if node["cls"] == 5:
                    children = node.get("children", [])
                    ### 소제목 노드가 유일한 경우만 처리
                    subtitles = [child for child in children if child["cls"] == 2]
                    if len(subtitles) == 1:
                        ### 만약 이미 정해진 순서에서, 첫 번째 자식이 이미지이고 두 번째 자식이 소제목이라면
                        if len(children) >= 2 and children[0]["cls"] == 6 and children[1]["cls"] == 2:
                            ### swap 자식의 순서를
                            children[0], children[1] = children[1], children[0]
                            ### 그리고 각 자식의 "order" 값을 서로 교체
                            children[0]["order"], children[1]["order"] = children[1]["order"], children[0]["order"]
                ### 재귀적으로 자식 노드 처리
                for child in node.get("children", []):
                    swap_image_and_subtitle_in_box(child)
            
            #######################################################################################
            ### 표 소제목 순서 변경
            def swap_image_and_lasttitle_in_box(node):
                ### node가 이미지/표 박스인 경우 처리
                if node["cls"] == 5:
                    children = node.get("children", [])
                    ### 소제목 노드가 유일한 경우만 처리
                    lasttitles = [child for child in children if child["cls"] == 3]
                    if len(lasttitles) == 1:
                        ### 만약 이미 정해진 순서에서, 첫 번째 자식이 표이고 두 번째 자식이 소제목이라면
                        if len(children) >= 2 and children[0]["cls"] == 6 and children[1]["cls"] == 3:
                            ### swap 자식의 순서를
                            children[0], children[1] = children[1], children[0]
                            ### 그리고 각 자식의 "order" 값을 서로 교체
                            children[0]["order"], children[1]["order"] = children[1]["order"], children[0]["order"]
                ### 재귀적으로 자식 노드 처리
                for child in node.get("children", []):
                    swap_image_and_lasttitle_in_box(child)
            
            for node in top_nodes:
                swap_image_and_subtitle_in_box(node)
            for node in top_nodes:
                swap_image_and_lasttitle_in_box(node)
            
            #######################################################################################
            ### (G) 원래 저장하던 요소 이미지 저장 (이미지/표/아이콘 등)
            def save_elements(node):
                if node["cls"] in [6, 7, 8, 10]:
                    x1, y1, x2, y2 = node["bbox"]
                    img = Image.open(img_path)
                    img_crop = img.crop((x1, y1, x2, y2))
                    element_path = os.path.join(page_folder, f"{self.element_names[node['cls']]}_{node['order']}.jpg")
                    img_crop.save(element_path)
                    node["element_path"] = element_path.replace("\\", "/")
                for child in node["children"]:
                    save_elements(child)
            for top_node in top_nodes:
                save_elements(top_node)

            #######################################################################################
            ### (H) 디버그용: 모든 박스 영역 이미지 저장
            def save_box_image(node, img, prefix=""):
                x1, y1, x2, y2 = node["bbox"]
                cropped = img.crop((x1, y1, x2, y2))
                filename = f"{prefix}_{node['order']}_{node['cls']}.jpg"
                save_path = os.path.join(debug_folder, filename)
                cropped.save(save_path)
                for child in node["children"]:
                    save_box_image(child, img, prefix=f"{prefix}_{node['order']}")
            im = Image.open(img_path)
            for top_node in top_nodes:
                save_box_image(top_node, im, prefix=file_root)

            #######################################################################################
            ### (I) YAML 파일 생성
            out_yaml = os.path.join(yaml_outdir, f"{file_root}.yaml")
            def node_to_yaml(nd):
                c_= nd["cls"]
                if 0 <= c_ < len(self.class_names):
                    cname = self.class_names[c_]
                else:
                    cname = f"cls_{c_}"
                d = {
                    "bbox": nd["bbox"],
                    "cls": c_,
                    "class_name": cname,
                    "order": nd["order"],
                    "ocr_text": nd["ocr_text"], 
                    "text_start_line": nd["text_start_line"], 
                    "element_path": nd.get("element_path", None)
                }
                if nd["children"]:
                    d["children"] = [node_to_yaml(ch) for ch in nd["children"]]
                else:
                    d["children"] = []
                return d
            
            data_for_yaml = [node_to_yaml(n) for n in top_nodes]
            with open(out_yaml, "w", encoding="utf-8") as f:
                yaml.safe_dump({"boxes": data_for_yaml}, f, allow_unicode=True, sort_keys=False)

            #######################################################################################
            ### (J) 결과 이미지 저장 (박스 및 라벨 표시)
            out_img = os.path.join(img_outdir, f"{file_root}.jpg")
            self.draw_result_image(img_path, top_nodes, out_img)

    ###############################################################################################
    ### 결과 이미지 저장 (박스 및 라벨 표시)
    def draw_result_image(self, image_path, top_nodes, output_path):
        im = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
        dr = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("malgun.ttf", size=20)
        except:
            font = ImageFont.load_default()
        all_nodes = []
        def dfs_collect(nd):
            all_nodes.append(nd)
            for c_ in nd["children"]:
                dfs_collect(c_)
        for top_ in top_nodes:
            dfs_collect(top_)
        for nd in all_nodes:
            x1, y1, x2, y2 = nd["bbox"]
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            cc = nd["cls"]
            oo = nd["order"]
            cname = self.class_names[cc] if 0 <= cc < len(self.class_names) else f"cls_{cc}"
            label = f"{oo} {cc} {cname}"
            col = self.class_colors[cc % len(self.class_colors)]
            tb = dr.textbbox((0, 0), label, font=font)
            tw = tb[2] - tb[0]
            th = tb[3] - tb[1]
            pad = 10
            bg = [x1, y1 - (th + 5), x1 + (tw + pad * 2), y1]
            dr.rectangle(bg, fill=col + "AA")
            dr.text((x1 + pad, y1 - th - 5), label, fill="white", font=font)
            dr.rectangle([x1, y1, x2, y2], outline=col, width=3)
        merged = Image.alpha_composite(im, overlay).convert("RGB")
        merged.save(output_path)
        print(f"[INFO] Result image saved => {output_path}")

###################################################################################################
###################################################################################################