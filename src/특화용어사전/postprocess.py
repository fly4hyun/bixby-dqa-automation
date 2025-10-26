###################################################################################################
###################################################################################################

import os
import re
from tqdm import tqdm
import ast

import pandas as pd
from collections import defaultdict

###################################################################################################
###################################################################################################

mapping_excel = 'data/제품맵핑정보.xlsx'

df = pd.read_excel(mapping_excel, engine='openpyxl')

mapping_pdf = defaultdict(lambda: [])
device_info_mapping = {}

for i in range(len(df)):
    
    categories = '&'.join([str(df['category'][i]), str(df['products'][i]), str(df['target_device(kr)'][i])])
    
    mapping_pdf[categories].append(df['파일이름'][i])

for i in range(len(df)):
    
    categories_dict = {}
    categories_dict['category'] = df['category'][i]
    categories_dict['products'] = df['products'][i]
    categories_dict['target_device(kr)'] = df['target_device(kr)'][i]
    categories_dict['target_device(en)'] = df['target_device(en)'][i]
    
    model_temp = df['model_names'][i]
    if '[' in model_temp:
        model_temp = model_temp.replace('[', '')
        model_temp = model_temp.replace(']', '')
        model_temp = model_temp.replace(',', '')
        model_temp = model_temp.replace('"', '')
        model_temp_list = model_temp.split(' ')
    else:
        model_temp_list = [model_temp]
    
    categories_dict['model_names'] = model_temp_list
    categories_dict['product_names'] = [df['product_names'][i]]
    
    device_info_mapping[df['파일이름'][i]] = categories_dict
    
###################################################################################################



korean_pdf = defaultdict(lambda: [])
non_korean_pdf = defaultdict(lambda: [])
for cate in list(mapping_pdf.keys()):
    # if cate != 'Refrigerator&general_fridge&냉장고':
    #     continue
    for name in mapping_pdf[cate]:
        korean_check = False
        dqa_excel = f'data/DQA/{name}.xlsx'
        pdf_df = pd.read_excel(dqa_excel, engine='openpyxl')
        
        sent = str(pdf_df['title'][2]) + str(pdf_df['subtitle'][2]) + str(pdf_df['lasttitle'][2]) + str(pdf_df['content'][2])

        korean_pattern = re.compile('[ㄱ-ㅎㅏ-ㅣ가-힣]+')
        korean_characters = ''.join(korean_pattern.findall(sent))
        korean_count = len(korean_characters)

        if korean_count > 4:
            korean_check = True
            korean_pdf[cate].append(name)
            
        if korean_check == False:
            non_korean_pdf[cate].append(name)
            
###################################################################################################

word_info = {}
word_mapping = {}
lang_mapping = {'KO': 'korean', 
                'EN': 'english', 
                'ES': 'spanish', 
                'PT': 'portuguese', 
                'DE': 'german', 
                'IT': 'italian', 
                'FR': 'french', }

for cate in list(mapping_pdf.keys()):
    # if cate != 'Refrigerator&general_fridge&냉장고':
    #     continue
    word_info[cate] = {}
    
    for kor_pdf in korean_pdf[cate]:
        kor_pdf_path = f'keywords/{cate}/{kor_pdf}.xlsx'
        kor_pdf_df = pd.read_excel(kor_pdf_path, engine='openpyxl')
        
        for i in range(len(kor_pdf_df)):
            wod = kor_pdf_df['Keyword'][i]
            word_mapping[wod] = {'korean': set(), 
                                 'english': set(), 
                                 'spanish': set(), 
                                 'portuguese': set(), 
                                 'german': set(), 
                                 'italian': set(), 
                                 'french': set()}
            if wod in list(word_info[cate].keys()):
                info_temp = dict(device_info_mapping[kor_pdf])
                if word_info[cate][wod]['target_device(en)'] == 'us-US 없음':
                    word_info[cate][wod]['target_device(en)'] = info_temp['target_device(en)']
                temp_model_name_set = set(info_temp['model_names'])
                temp_model_name_set.update(set(word_info[cate][wod]['model_names']))
                word_info[cate][wod]['model_names'] = list(temp_model_name_set)
                
                temp_product_names_set = set(info_temp['product_names'])
                temp_product_names_set.update(set(word_info[cate][wod]['product_names']))
                word_info[cate][wod]['product_names'] = list(temp_product_names_set)
                
            else:
                word_info[cate][wod] = dict(device_info_mapping[kor_pdf])
                
    ###############################################################################################
    
    for non_kor_pdf in non_korean_pdf[cate]:
        non_kor_pdf_path = f'keywords/{cate}/{non_kor_pdf}.xlsx'
        non_kor_pdf_df = pd.read_excel(non_kor_pdf_path, engine='openpyxl')
        
        for i in range(len(non_kor_pdf_df)):
            lang_non_ko = lang_mapping[non_kor_pdf_df['Language'][i]]
            ko_word = non_kor_pdf_df['Keyword'][i]
            lang_non_ko_word = ast.literal_eval(non_kor_pdf_df['Mapping'][i])
            
            word_mapping[ko_word][lang_non_ko].update(set(lang_non_ko_word))
            
            info_temp = dict(device_info_mapping[non_kor_pdf])
            
            if word_info[cate][ko_word]['target_device(en)'] == 'us-US 없음':
                if info_temp['target_device(en)'] != 'us-US 없음':
                    word_info[cate][ko_word]['target_device(en)'] = info_temp['target_device(en)']
                    
            temp_model_name_set = set(info_temp['model_names'])
            temp_model_name_set.update(set(word_info[cate][wod]['model_names']))
            word_info[cate][wod]['model_names'] = list(temp_model_name_set)
            
            temp_product_names_set = set(info_temp['product_names'])
            temp_product_names_set.update(set(word_info[cate][wod]['product_names']))
            word_info[cate][wod]['product_names'] = list(temp_product_names_set)
            
###################################################################################################

data = []
cnt = 1
for cate in list(mapping_pdf.keys()):
    # if cate != 'Refrigerator&general_fridge&냉장고':
    #     continue
    for ko_word in list(word_info[cate].keys()):
        
        en_word = list(word_mapping[ko_word]['english'])
        es_word = list(word_mapping[ko_word]['spanish'])
        pt_word = list(word_mapping[ko_word]['portuguese'])
        de_word = list(word_mapping[ko_word]['german'])
        it_word = list(word_mapping[ko_word]['italian'])
        fr_word = list(word_mapping[ko_word]['french'])
        
        if en_word == []:
            continue
        if en_word == [] and es_word == [] and pt_word == [] and de_word == [] and it_word == [] and fr_word == []:
            continue
        if en_word == []:
            en_word = ''
        if es_word == []:
            es_word = ''
        if pt_word == []:
            pt_word = ''
        if de_word == []:
            de_word = ''
        if it_word == []:
            it_word = ''
        if fr_word == []:
            fr_word = ''
        
        korean_pattern = re.compile('[ㄱ-ㅎㅏ-ㅣ가-힣]+')
        korean_characters = ''.join(korean_pattern.findall(ko_word))
        korean_count = len(korean_characters)
        if korean_count == 0:
            continue
        
        data.append({
            'no': cnt, 
            'category': word_info[cate][ko_word]['category'], 
            'products': word_info[cate][ko_word]['products'], 
            'target_device(kr)': word_info[cate][ko_word]['target_device(kr)'], 
            'target_device(en)': word_info[cate][ko_word]['target_device(en)'], 
            'model_names': word_info[cate][ko_word]['model_names'], 
            'product_names': word_info[cate][ko_word]['product_names'], 
            'korean': ko_word, 
            'english': en_word, 
            'spanish': es_word, 
            'portuguese': pt_word, 
            'german': de_word, 
            'italian': it_word, 
            'french': fr_word, 
        })
        
        cnt += 1

df_results = pd.DataFrame(data, columns=["no", "category", "products", "target_device(kr)", "target_device(en)", "model_names", "product_names", "korean", "english", "spanish", "portuguese", "german", "italian", "french"])
df_results.to_excel(f'Specialized_Terminology_Dictionary.xlsx', index=False)
        
###################################################################################################
###################################################################################################