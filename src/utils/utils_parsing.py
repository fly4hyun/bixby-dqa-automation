###################################################################################################
###################################################################################################

import os
import yaml
import pandas as pd
import re

###################################################################################################
###################################################################################################
### 키워드 매핑 변수
KEYWORD_MAP = {
    '참고': ['참고', 'note', 'Note', 'NOTE', 
           'HUOM',  # 핀란드
           'MERK',  # 노르웨이
           'BEMÆRK', # 덴마크
           'OBS',   # 스웨덴
           'HINWEIS', # 독일
           'OPMERKING', # 네덜란드
           'REMARQUE', # 프랑스
           'NOTA', 'OBSERVAÇÃO',  # 스페인, IT, PT
           'ΣΗΜΕΙΩΣΗ',    #EL
           'नो ोट',     #HI
           'MEGJEGYZÉS',  #HU
           'ЗАБЕЛЕЖКА',   #BG
           'MÄRKUS',  #ET
           'PASTABA',    #LT
           'PIEZĪME',     #LV
           'UWAGA',  #PL
           'NOTĂ'   #RO
           ],
    '주의': ['주의', 'caution', 'Caution', 'CAUTION', 
           'HUOMIO',    # 핀란드
           'FORSIKTIG', # 노르웨이
           'FORSIGTIG', 'ACHTUNG', # 덴마크
           'VAR FÖRSIKTIG', 'VARFÖRSIKTIG', # 스웨덴
           'VORSICHT',  # 독일
           'OPGELET', 'LET OP', 'LETOP',   # 네덜란드
           'ATTENTION', # 프랑스
           'PRECAUCIÓN',  # 스페인
           'ΠΡΟΣΟΧΗ',     #EL
           'ATTENZIONE', 'PRECAUZIONE',  #IT
           'ATENÇÃO', 'CUIDADO',     #PT
           'सा ावधाान',   #HI
           'VIGYÁZAT',    #HU
           'ВНИМАНИЕ',    #BG
           'ETTEVAATUST',     #ET
           'DĖMESIO',     #LT
           'UZMANĪBU',    #LV
           'PRZESTROGA',  #PL
           'ATENŢIE'    #RO
           ],
    '경고': ['경고', 'warning', 'Warning', 'WARNING', 
           'VAROITUS',   # 핀란드
           'ADVARSEL',  # 노르웨이
           'ADVARSEL',  # 덴마크
           'VARNING',   # 스웨덴
           'WARNUNG',   # 독일
           'WAARSCHUWING', # 네덜란드
           'AVERTISSEMENT', 'MISE EN GARDE', 'MISEENGARDE',   # 프랑스
           'ADVERTENCIA',  # 스페인
           'ΠΡΟΕΙΔΟΠΟΙΗΣΗ',   #EL
           'AVVERTENZA',  #IT
           'AVISO', 'ADVERTÊNCIA',  #PT
           'चेेताावनीी',    #HI
           'FIGYELMEZTETÉS',  #HU
           'ПРЕДУПРЕЖДЕНИЕ',  #BG
           'HOIATUS',     #ET
           'ĮSPĖJIMAS',   #LT
           'BRĪDINĀJUMS',     #LV
           'OSTRZEŻENIE',     #PL
           'AVERTISMENT'    #RO
           ]
}

###################################################################################################
###################################################################################################
### flush 및 관련 함수
def flush_branch(branch_state, content_accumulator, data):
    if branch_state and branch_state.get('lines'):
        branch_text = "\n".join(branch_state['lines'])
        content_accumulator['content'] += branch_text
        branch_state['lines'] = []
    return branch_state

###################################################################################################
### flush 및 관련 함수
def flush_current_record(content_accumulator, data):
    if content_accumulator['content'].strip():
        data.append(content_accumulator.copy())
        content_accumulator['content'] = ''
        content_accumulator['record_mode'] = None
        if 'start_x_info' in content_accumulator:
            del content_accumulator['start_x_info']

###################################################################################################
### insert_text 함수 (start_x 포함)
def insert_text(text, start_x, content_accumulator, data):
    if not text.strip():
        return

    tolerance_x = 8.0
    terminal_punctuations = {'.', '!', '?', ')'}
    bullet_chars = ['•', 'ꞏ', '−', '(', '※', '-']

    if not content_accumulator.get('content', '').strip():
        content_accumulator['record_mode'] = "text"
        content_accumulator['content'] = text
        content_accumulator['start_x_info'] = start_x
        content_accumulator['group_has_increased'] = False
        return

    if start_x < content_accumulator['start_x_info'] - tolerance_x:
        flush_current_record(content_accumulator, data)
        content_accumulator['record_mode'] = "text"
        content_accumulator['content'] = text
        content_accumulator['start_x_info'] = start_x
        content_accumulator['group_has_increased'] = False
        return

    if any(text.strip().startswith(b) for b in bullet_chars):
        content_accumulator['content'] += "\n" + text
        if start_x > content_accumulator['start_x_info'] + tolerance_x:
            content_accumulator['start_x_info'] = start_x
            content_accumulator['group_has_increased'] = True
        return

    if start_x > content_accumulator['start_x_info'] + tolerance_x:
        content_accumulator['group_has_increased'] = True
        content_accumulator['start_x_info'] = start_x
        content_accumulator['content'] += "\n" + text
    else:
        if content_accumulator.get('group_has_increased', False):
            content_accumulator['content'] += "\n" + text
        else:
            if content_accumulator['content'].strip() and content_accumulator['content'].strip()[-1] in terminal_punctuations:
                flush_current_record(content_accumulator, data)
                content_accumulator['record_mode'] = "text"
                content_accumulator['content'] = text
                content_accumulator['start_x_info'] = start_x
                content_accumulator['group_has_increased'] = False
            else:
                content_accumulator['content'] += "\n" + text

###################################################################################################
###################################################################################################
### process_box 함수
### 대제목, 중제목, 소제목, 내용을 구분하여 저장
def process_box(box, content_accumulator, current_title, data, 
                super_class=None, last_class=None, branch_state=None, 
                icon_subtitles_check=[False, None]):
    
    ### text 내용, 시작 위치
    ocr_text = ' '.join(box.get('ocr_text', []))
    text_start_line = ''.join(box.get('text_start_line', []))
    ### 클래스 이름, 수정
    class_name = box.get('class_name', '')
    child_class_name = box.get('class_name', '')
    current_order = box.get("order", None)
    
    if class_name in ['대제목', '중제목', '소제목']:
        branch_state = flush_branch(branch_state, content_accumulator, data)
        flush_current_record(content_accumulator, data)
        content_accumulator['record_mode'] = None
        content_accumulator['content_type'] = ''
    
    if class_name == '대제목':
        if current_title != ocr_text:
            flush_current_record(content_accumulator, data)
            current_title = ocr_text
            content_accumulator['title'] = ocr_text
            content_accumulator['subtitle'] = ''
            content_accumulator['lasttitle'] = ''
            content_accumulator['content'] = ''
        if current_order is not None:
            content_accumulator['last_order'] = current_order
    elif class_name == '중제목':
        flush_current_record(content_accumulator, data)
        content_accumulator['subtitle'] = ocr_text
        content_accumulator['lasttitle'] = ''
        content_accumulator['content'] = ''
        icon_subtitles_check = [False, None]
        if current_order is not None:
            content_accumulator['last_order'] = current_order
    elif class_name == '소제목':
        if last_class == '아이콘':
            cleaned_text = re.sub(r'\s+', '', ocr_text).lower()
            assigned_keyword = None
            for keyword in ['경고', '주의', '참고']:
                for variant in KEYWORD_MAP.get(keyword, []):
                    if variant.lower() in cleaned_text:
                        assigned_keyword = keyword
                        break
                if assigned_keyword is not None:
                    break
            if assigned_keyword is None:
                try:
                    start_x = float(text_start_line.strip().splitlines()[0])
                except Exception:
                    start_x = content_accumulator.get('start_x_info', 0)
                insert_text(ocr_text, start_x, content_accumulator, data)
                if current_order is not None:
                    content_accumulator['last_order'] = current_order
            else:
                flush_current_record(content_accumulator, data)
                ### 경고/주의/참고 키워드가 포함된 경우는 그대로 저장하고, 후처리에서 추가 merge 진행
                content_accumulator['lasttitle'] = ocr_text
                content_accumulator['content_type'] = assigned_keyword
                content_accumulator['content'] = ''
                if current_order is not None:
                    content_accumulator['last_order'] = current_order
        else:
            flush_current_record(content_accumulator, data)
            new_record = content_accumulator.copy()
            new_record['lasttitle'] = ocr_text
            new_record['content'] = ""
            if current_order is not None:
                new_record['last_order'] = current_order
            data.append(new_record)
            content_accumulator['lasttitle'] = ""
    elif class_name == '내용':
        tolerance = 4.0
        terminal_punctuations = {'.', '!', '?', ')'}
        if branch_state is None:
            branch_state = {'lines': [], 'base_x': None}
        ocr_lines = ocr_text.strip().splitlines()
        start_x_lines = text_start_line.strip().splitlines()
        total_lines = min(len(ocr_lines), len(start_x_lines))
        for i in range(total_lines):
            line = ocr_lines[i].strip()
            if not line:
                continue
            try:
                current_x = float(start_x_lines[i].strip())
            except Exception:
                continue
            if branch_state['base_x'] is None:
                branch_state['base_x'] = current_x
            first_char = line[0]
            if first_char in ['•', 'ꞏ', '−', '(', '※', '-']:
                branch_state['lines'].append(line)
                continue
            if not branch_state['lines']:
                branch_state['lines'].append(line)
                branch_state['base_x'] = current_x
                continue
            if current_x > branch_state['base_x'] + tolerance:
                branch_state['lines'].append(line)
            elif abs(current_x - branch_state['base_x']) <= tolerance:
                if branch_state['lines'] and branch_state['lines'][-1][-1] in terminal_punctuations:
                    text_from_box = "\n".join(branch_state['lines'])
                    insert_text(text_from_box, branch_state['base_x'], content_accumulator, data)
                    branch_state = {'lines': [line], 'base_x': current_x}
                else:
                    branch_state['lines'].append(line)
            else:
                text_from_box = "\n".join(branch_state['lines'])
                insert_text(text_from_box, branch_state['base_x'], content_accumulator, data)
                branch_state = {'lines': [line], 'base_x': current_x}
        if branch_state and branch_state.get('lines'):
            text_from_box = "\n".join(branch_state['lines'])
            insert_text(text_from_box, branch_state['base_x'], content_accumulator, data)
        branch_state = None
        if current_order is not None:
            content_accumulator['last_order'] = current_order
    elif class_name in ['이미지', '표']:
        flush_current_record(content_accumulator, data)
        branch_state = None
    else:
        branch_state = flush_branch(branch_state, content_accumulator, data)
        branch_state = None

    for child in box.get('children', []):
        _, child_last_class, class_name, branch_state, icon_subtitles_check = process_box(
            child, content_accumulator, current_title, data,
            super_class=child_class_name,
            last_class=class_name,
            branch_state=branch_state,
            icon_subtitles_check=icon_subtitles_check
        )
    return current_title, child_class_name, class_name, branch_state, icon_subtitles_check

###################################################################################################
###################################################################################################
### load_yaml_data 함수
### 생성된 데이터를 후처리하여 저장
def load_yaml_data(pdf_name):
    base_path = f'pdf_results/pdf_refined_text/{pdf_name}'
    data = []
    ignore_first_page = True
    content_accumulator = {
        'pdf_name': pdf_name,
        'serial_number': '',
        'product_name': '',
        'title': '',
        'subtitle': '',
        'lasttitle': '',
        'content': '',
        'page': None,
        'category': '',
        'products': '',
        'target_device(kr)': '',
        'target_device(en)': '',
        'model_names': '',
        'product_names': '',
        'content_type': '',
        'record_mode': None
    }
    current_title = None
    super_class = None
    last_class = None
    current_branch_state = None
    icon_subtitles_check = [False, None]
    page_counter = 1
    files = sorted(os.listdir(base_path), key=lambda x: int(x.split('.')[0]))
    total_files = len(files)
    for idx, yaml_file in enumerate(files):
        ### 마지막 페이지 건너뛰기
        if idx == total_files - 1:
            continue

        with open(os.path.join(base_path, yaml_file), 'r', encoding='utf-8') as file:
            page_data = yaml.safe_load(file)

        ### 페이지 제목 추출 (대제목 box에서 제목 확인)
        page_title = ""
        for box in page_data.get('boxes', []):
            if box.get('class_name') == '대제목' and box.get('ocr_text'):
                page_title = " ".join(box.get('ocr_text')).strip()
                break

        ### 제목이 '제품보증서' 또는 'Open Source Announcement'이면 건너뛰기
        if page_title in ['제품보증서', 'Open Source Announcement']:
            continue

        content_accumulator['page'] = page_counter
        page_counter += 1

        if ignore_first_page:
            ignore_first_page = False
            continue

        if any(box.get('class_name') == '목차' for box in page_data.get('boxes', [])):
            continue

        page_boxes = page_data.get('boxes', [])
        for box in page_boxes:
            current_title, super_class, last_class, current_branch_state, icon_subtitles_check = process_box(
                box, content_accumulator, current_title, data,
                super_class, last_class, branch_state=current_branch_state,
                icon_subtitles_check=icon_subtitles_check
            )
        current_branch_state = flush_branch(current_branch_state, content_accumulator, data)
        current_branch_state = None
        flush_current_record(content_accumulator, data)

    current_branch_state = flush_branch(current_branch_state, content_accumulator, data)
    current_branch_state = None
    flush_current_record(content_accumulator, data)
    
    ###############################################################################################
    ### 후처리 2
    ### 동일 타이틀 내에서는 중제목이 바뀌지 않으면 이전 non-keyword 소제목(last_non_keyword_lasttitle)을 유지하고,
    ### 중제목이 새로 나오면 소제목은 빈 칸("")으로 처리
    ### 또한, record의 lasttitle에 경고/주의/참고 키워드가 포함되어 있으면,
    ### 해당 텍스트에서 키워드를 제거한 후 남은 추가 텍스트(있다면)를 content에 합치고, 
    ### content_type은 해당 키워드를 유지한 채 lasttitle은 빈 칸으로 처리
    last_title = ""
    last_subtitle = ""
    last_non_keyword_lasttitle = ""
    
    for record in data:
        current_title = record.get('title', '').strip()
        current_subtitle = record.get('subtitle', '').strip()
        current_lasttitle = record.get('lasttitle', '').strip()
        
        if current_title != last_title:
            last_title = current_title
            last_subtitle = current_subtitle
            last_non_keyword_lasttitle = current_lasttitle
            record['subtitle'] = current_subtitle
            record['lasttitle'] = current_lasttitle
        else:
            if current_subtitle != last_subtitle:
                last_subtitle = current_subtitle
                last_non_keyword_lasttitle = current_lasttitle
                record['subtitle'] = current_subtitle
                record['lasttitle'] = current_lasttitle
            else:
                if last_non_keyword_lasttitle != current_lasttitle:
                    last_non_keyword_lasttitle = current_lasttitle
                    record['lasttitle'] = current_lasttitle
                
        ### 후처리: 만약 record의 lasttitle에 경고/주의/참고 키워드가 포함되어 있으면,
        ### 키워드 제거 후 남은 추가 텍스트가 있으면 이를 content에 합치고, 
        ### content_type은 해당 키워드를 유지한 채 lasttitle은 빈 칸으로 처리
        if record.get('lasttitle', '').strip():
            ### lasttitle에서 공백, :, -, / 등 특수문자 제거 후 소문자로 변환
            cleaned_lasttitle = re.sub(r'[\s\:\-/]+', "", record['lasttitle']).lower()
            keywords_priority = ["경고", "주의", "참고"]
            chosen = None
            for kw in keywords_priority:
                for variant in KEYWORD_MAP.get(kw, []):
                    cleaned_variant = re.sub(r'[\s\:\-/]+', "", variant).lower()
                    if cleaned_variant in cleaned_lasttitle:
                        chosen = kw
                        break
                if chosen is not None:
                    break
            if chosen is not None:
                record['content_type'] = chosen
                ### 체크: cleaned_lasttitle가 정확히 키워드만 있는지 확인
                keyword_exact = False
                for kw in keywords_priority:
                    for variant in KEYWORD_MAP.get(kw, []):
                        cleaned_variant = re.sub(r'[\s\:\-/]+', "", variant).lower()
                        if cleaned_lasttitle == cleaned_variant:
                            keyword_exact = True
                            break
                    if keyword_exact:
                        break
                if not keyword_exact:
                    ### 추가 텍스트가 있는 경우, 원본 lasttitle을 content에 추가
                    if record.get('content', "").strip():
                        record['content'] = record['lasttitle'] + "\n" + record['content']
                    else:
                        record['content'] = record['lasttitle']
                ### 최종적으로 lasttitle을 빈 칸으로 처리
                record['lasttitle'] = ""
            else:
                record['lasttitle'] = current_lasttitle
                record['content_type'] = ""
                last_non_keyword_lasttitle = current_lasttitle
        else:
            if not record.get('content_type', '').strip():
                record['content_type'] = ""
    
    ###############################################################################################
    ### 추가 상속 처리:
    ### 같은 타이틀/소제목 그룹 내에서, 만약 content_type이 빈 경우,
    ### 그리고 record의 lasttitle과 content가 모두 빈 경우, 이전 경고/주의/참고 값을 상속
    last_warning_type = ""
    last_title2 = ""
    last_subtitle2 = ""
    for record in data:
        current_title = record.get('title','').strip()
        current_subtitle = record.get('subtitle','').strip()
        if current_title != last_title2 or current_subtitle != last_subtitle2:
            last_warning_type = ""
        if record.get('content_type','').strip():
            last_warning_type = record['content_type']
        else:
            if not record.get('lasttitle','').strip() and not record.get('content','').strip():
                record['content_type'] = last_warning_type
        last_title2 = current_title
        last_subtitle2 = current_subtitle
    
    ###############################################################################################
    ### 추가 후처리: 동일 세부제목 그룹에 빈 내용 레코드가 없으면 삽입
    final_data = []
    i = 0
    while i < len(data):
        record = data[i]
        cur_lasttitle = record.get('lasttitle', '').strip()
        if cur_lasttitle != "":
            group = []
            while i < len(data) and data[i].get('lasttitle', '').strip() == cur_lasttitle:
                group.append(data[i])
                i += 1
            has_blank = any(r.get('content', '').strip() == "" for r in group)
            if not has_blank:
                blank_record = group[0].copy()
                blank_record['content'] = ""
                final_data.append(blank_record)
            final_data.extend(group)
        else:
            final_data.append(record)
            i += 1
    data = final_data
    
    ###############################################################################################
    ### 추가 병합:
    ### 같은 타이틀/소제목 그룹에서, 만약 첫 record의 content_type이 경고/주의/참고이고, lasttitle이 빈 칸이며,
    ### 바로 다음 record의 lasttitle이 채워져 있고 그 record의 content_type이 빈 칸이며,
    ### 그 record의 content가 비어있지 않을 경우에만 merge하여 하나의 block으로 처리
    i = 0
    while i < len(data) - 1:
        rec = data[i]
        next_rec = data[i+1]
        if rec.get('title','') == next_rec.get('title','') and rec.get('subtitle','') == next_rec.get('subtitle',''):
            if (rec.get('content_type','').strip() in KEYWORD_MAP and 
                rec.get('lasttitle','').strip() == "" and 
                next_rec.get('lasttitle','').strip() != "" and 
                next_rec.get('content_type','').strip() == "" and
                next_rec.get('content','').strip() != ""):
                merge_text = next_rec['lasttitle']
                if next_rec.get('content','').strip():
                    merge_text += "\n" + next_rec['content']
                if rec.get('content','').strip():
                    rec['content'] = rec['content'] + "\n" + merge_text
                else:
                    rec['content'] = merge_text
                del data[i+1]
                continue
        i += 1

    ###############################################################################################
    ### 추가 상속: 같은 타이틀/소제목 그룹 내에서,
    ### 만약 경고/주의/참고 타입이 설정된 레코드가 있고, 그 레코드 이후에 lasttitle이 비어있는 레코드가 있으면 상속
    def inherit_warning(data):
        current_warning = None
        current_title = None
        current_subtitle = None
        for record in data:
            title = record.get('title','').strip()
            subtitle = record.get('subtitle','').strip()
            if title != current_title or subtitle != current_subtitle:
                current_title = title
                current_subtitle = subtitle
                current_warning = None
            if record.get('content_type','').strip() in KEYWORD_MAP:
                current_warning = record['content_type']
            else:
                if not record.get('lasttitle','').strip() and not record.get('content','').strip():
                    if current_warning:
                        record['content_type'] = current_warning
        return data

    data = inherit_warning(data)
    
    ###############################################################################################
    ### 1. lasttitle 상속 처리: 같은 title/ subtitle 그룹 내에서, 마지막 소제목이 나타난 후 빈 칸이면 해당 소제목(lasttitle)으로 채우기
    prev_title = None
    prev_subtitle = None
    current_subheading = None
    for record in data:
        title = record.get('title', '').strip()
        subtitle = record.get('subtitle', '').strip()
        lasttitle = record.get('lasttitle', '').strip()
        ### 그룹 변경 시 current_subheading 초기화
        if title != prev_title or subtitle != prev_subtitle:
            current_subheading = lasttitle if lasttitle else None
            prev_title = title
            prev_subtitle = subtitle
        else:
            if not lasttitle and current_subheading:
                record['lasttitle'] = current_subheading
            elif lasttitle:
                current_subheading = lasttitle
    
    ### 검수 작업시 헷갈릴수 있으므로 주석 처리
    # ###############################################################################################
    # ### 2. content 줄바꿈 처리, 빈 줄 삭제 및 KEYWORD_MAP 단어 확인 추가
    # def process_content(text):
    #     import re
    #     terminal_punctuations = {'.', '!', '?', ')'}
    #     bullet_chars = ['•', 'ꞏ', '−', '(', '※']
    #     ### 빈 줄 제거 및 strip 처리
    #     lines = [line.strip() for line in text.splitlines() if line.strip()]
    #     if not lines:
    #         return ""
    #     result = lines[0]
    #     for i in range(1, len(lines)):
    #         prev_line = lines[i-1]
    #         curr_line = lines[i]
    #         ### prev_line을 공백 및 특수문자 제거 후 소문자로 변환
    #         cleaned_prev_line = re.sub(r'[\s\:\-/]+', '', prev_line).lower()
    #         has_keyword = False
    #         for key in ['참고', '주의', '경고']:
    #             for variant in KEYWORD_MAP.get(key, []):
    #                 # variant도 같은 방식으로 클린 처리
    #                 cleaned_variant = re.sub(r'[\s\:\-/]+', '', variant).lower()
    #                 if cleaned_variant in cleaned_prev_line:
    #                     has_keyword = True
    #                     break
    #             if has_keyword:
    #                 break
    #         ### 이전 줄의 마지막 문자가 터미널 기호이거나, 현재 줄이 bullet 문자로 시작하거나,
    #         ### 이전 줄에 KEYWORD_MAP에 해당하는 단어가 있으면 줄바꿈 유지
    #         if prev_line[-1] in terminal_punctuations or curr_line[0] in bullet_chars or has_keyword:
    #             result += "\n" + curr_line
    #         else:
    #             result += " " + curr_line
    #     return result
    
    # for record in data:
    #     content = record.get('content', '')
    #     if content:
    #         record['content'] = process_content(content)
    
    ###############################################################################################
    ### 3. 만약 content가 완전히 빈 문자열이면 해당 내용(줄)은 제거
    ###    (위 process_content 함수에서 이미 빈 줄은 삭제하므로, 최종 결과가 빈 경우에만 체크)
    data = [record for record in data if record.get('content', '').strip() != ""]

    ###############################################################################################
    ### 4. 만약 content_type이 빈 문자열이면 "일반"으로 설정
    for record in data:
        if not record.get('content_type', '').strip():
            record['content_type'] = "일반"
    
    return data

###################################################################################################
###################################################################################################
### csv로 저장
def save_to_csv(pdf_name, data):
    csv_path = f'pdf_parser_results/{pdf_name}.csv'
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    for i, record in enumerate(data, start=1):
        record['No'] = i
    df = pd.DataFrame(data)
    columns = ['No', 'category', 'products', 'target_device(kr)', 'target_device(en)',
               'model_names', 'product_names', 'title', 'subtitle',
               'lasttitle', 'content', 'content_type', 'page']
    df.to_csv(csv_path, index=False, columns=columns, encoding='utf-8-sig')

###################################################################################################
### xlsx로  저장
def save_to_xlsx(pdf_name, data):
    if not data:
        print("저장할 데이터가 없습니다.")
        return
    xlsx_path = f'pdf_parser_results/{pdf_name}.xlsx'
    os.makedirs(os.path.dirname(xlsx_path), exist_ok=True)
    for i, record in enumerate(data, start=1):
        record['No'] = i
    df = pd.DataFrame(data)
    columns = ['No', 'category', 'products', 'target_device(kr)', 'target_device(en)',
               'model_names', 'product_names', 'title', 'subtitle',
               'lasttitle', 'content', 'content_type', 'page']
    df.to_excel(xlsx_path, index=False, columns=columns, sheet_name='Parser Results')
    print(f"파일 저장 완료: {xlsx_path}")

###################################################################################################
###################################################################################################