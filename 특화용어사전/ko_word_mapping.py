###################################################################################################
###################################################################################################


import os
import re
from tqdm import tqdm
import ast
import pandas as pd
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain, LLMChain, ConversationChain


from langchain.prompts.prompt import PromptTemplate


###################################################################################################
###################################################################################################

mapping_excel = 'data/제품맵핑정보.xlsx'

df = pd.read_excel(mapping_excel, engine='openpyxl')

mapping_pdf = defaultdict(lambda: [])

for i in range(len(df)):
    
    categories = '&'.join([str(df['category'][i]), str(df['products'][i]), str(df['target_device(kr)'][i])])
    
    mapping_pdf[categories].append(df['파일이름'][i])

###################################################################################################

openai_api_key = ""

###################################################################################################

llm4 = ChatOpenAI(
    openai_api_key=openai_api_key, 
    model_name='gpt-4-0125-preview', 
    temperature=0
)

###################################################################################################

kor_word_mapping = defaultdict(lambda: [])

for cate in list(mapping_pdf.keys()):
    
    kor_word_temp = set()

    for name in mapping_pdf[cate]:
        korean_check = False
        
        dqa_excel = f'data/DQA/{name}.xlsx'
        pdf_df = pd.read_excel(dqa_excel, engine='openpyxl')
        
        sent = str(pdf_df['title'][2]) + str(pdf_df['subtitle'][2]) + str(pdf_df['lasttitle'][2]) + str(pdf_df['content'][2])

        korean_pattern = re.compile('[ㄱ-ㅎㅏ-ㅣ가-힣]+')
        korean_characters = ''.join(korean_pattern.findall(sent))
        korean_count = len(korean_characters)
        
        word_list = set()
        word_list.add(str(pdf_df['target_device(kr)'][1]))
        
        if korean_count > 4:
            korean_check = True
            
            kor_excel_path = f'keywords/{cate}/{name}.xlsx'
            ko_pdf_df = pd.read_excel(kor_excel_path, engine='openpyxl')
            kor_word_temp.update(ko_pdf_df['Keyword'].tolist())
            
    kor_word_mapping[cate] = kor_word_temp

###################################################################################################

cnt = 1

for cate in list(mapping_pdf.keys()):
    
    os.makedirs(f'keywords/{cate}', exist_ok=True)
    kor_word = list(kor_word_mapping[cate])
    mapping_dict = {}
    
    for word in kor_word:
        mapping_dict[word] = set()
    
    print(cate)
    for name in mapping_pdf[cate]:
        
        print(f'{cnt}/178 : {name}')
        cnt += 1
        korean_check = False
        
        dqa_excel = f'data/DQA/{name}.xlsx'
        pdf_df = pd.read_excel(dqa_excel, engine='openpyxl')
        
        device_info = '카테고리: ' + str(pdf_df['category'][1]) 
        device_info += ', 프로덕트: ' + str(pdf_df['products'][1]) 
        device_info += ', 한글명: ' + str(pdf_df['target_device(kr)'][1])
        device_info += ', 영문명: ' + str(pdf_df['target_device(en)'][1])
        device_info += ', 프로덕트 이름: ' + str(pdf_df['product_names'][1])
        
        sent = str(pdf_df['title'][2]) + str(pdf_df['subtitle'][2]) + str(pdf_df['lasttitle'][2]) + str(pdf_df['content'][2])

        korean_pattern = re.compile('[ㄱ-ㅎㅏ-ㅣ가-힣]+')
        korean_characters = ''.join(korean_pattern.findall(sent))
        korean_count = len(korean_characters)
        
        if korean_count > 4:
            korean_check = True
            
        if korean_check == False:
            
            template_text = """
                제품 정보: {info}
                
                한글 단어 리스트트: {ko_word}
                
                다국어 설명서에서 소제목 기준으로 내용을 추출하여, 제품과 관련된 특화 용어사전을 만들거야.
                
                다음 문장에서 한글 단어 리스트에 있는 단어와 의미가 일치하는 단어를 찾아서 리스트 형태로 추출해줘.
                - [["한국어단어1", "다국어용어1"], ["한국어단어2", "다국어용어2"], ...] 형태로 추출해줘.
                - 단어가 없으면 빈 리스트로 표현
                - 한글 단어와 일치하는 것만 추출해야되.
                - 의미적으로 같은 것도 추출해도 되.
                - 한글 단어는 제품과 관련된 일반적이지 않은 특화 용어들로만 뽑았어.

                예시 결과: [["한국어단어1", "다국어용어1"], ["한국어단어2", "다국어용어2"], ...]

                <문장>
                {sentence}
            """
        
            prompt = PromptTemplate(
                input_variables=["info", "ko_word", "sentence"],
                template=template_text
            )
            
            lasttitle = ''
            sent = '대제목: ' + str(pdf_df['title'][0]) 
            sent += ', 중제목: ' + str(pdf_df['subtitle'][0]) 
            sent += ', 소제목: ' + str(pdf_df['lasttitle'][0])
            sent += ', 내용: ' + str(pdf_df['content'][0])
            
            for i in tqdm(range(len(pdf_df))):
                if i == 0:
                    lasttitle = str(pdf_df['lasttitle'][0])
                else:
                    if lasttitle == str(pdf_df['lasttitle'][i]):
                        sent += '\n' + str(pdf_df['content'][i])
                    else:
                        inputs = {
                            "info": device_info,
                            "ko_word": list(mapping_dict.keys()),
                            "sentence": sent
                        }
                        
                        chain = prompt | llm4
                        response = chain.invoke(inputs)
                        try:
                            extracted_mappings = ast.literal_eval(response.content)
                        except Exception as e:
                            print("응답 파싱 실패:", e)
                            print(response.content)
                            extracted_mappings = []
                            
                        for mapping in extracted_mappings:
                            if len(mapping) == 2:
                                k = mapping[0]
                                v = mapping[1]
                                if k in mapping_dict:
                                    mapping_dict[k].add(v)                                    

                        lasttitle = str(pdf_df['lasttitle'][i])
                        sent = '대제목: ' + str(pdf_df['title'][i]) 
                        sent += ', 중제목: ' + str(pdf_df['subtitle'][i]) 
                        sent += ', 소제목: ' + str(pdf_df['lasttitle'][i])
                        sent += ', 내용: ' + str(pdf_df['content'][i])
            
            
            folder_path = os.path.join("keywords", cate)
            excel_file = os.path.join(folder_path, f"{name}.xlsx")
            
            data = []
            for key, values in mapping_dict.items():
                # 값이 없으면 빈 리스트, 있으면 리스트로 변환
                value_list = list(values) if values else []
                data.append({'Keyword': key, 'Mapping': value_list})
            df_key_pdf = pd.DataFrame(data, columns=["Keyword", "Mapping"])
            df_key_pdf.to_excel(excel_file, index=False)
            

###################################################################################################





###################################################################################################
###################################################################################################