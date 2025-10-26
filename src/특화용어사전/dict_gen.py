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

def get_simple_QA_35(prompt, openai_api_key):
    llm = ChatOpenAI(openai_api_key=openai_api_key, model_name = 'gpt-3.5-turbo', temperature=0)
    # llm = ChatOpenAI(openai_api_key=openai_api_key, model_name = 'gpt-4-0125-preview', temperature=0)
    
    simple_QA = LLMChain(
            llm=llm, 
            prompt = prompt
        )
    
    return simple_QA

###################################################################################################

cnt = 1

for cate in list(mapping_pdf.keys()):
    
    os.makedirs(f'keywords/{cate}', exist_ok=True)
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
        device_info += ', 프로덕트 이름: ' + str(pdf_df['product_names'][1])
        
        sent = str(pdf_df['title'][2]) + str(pdf_df['subtitle'][2]) + str(pdf_df['lasttitle'][2]) + str(pdf_df['content'][2])

        korean_pattern = re.compile('[ㄱ-ㅎㅏ-ㅣ가-힣]+')
        korean_characters = ''.join(korean_pattern.findall(sent))
        korean_count = len(korean_characters)
        
        word_list = set()
        word_list.add(str(pdf_df['target_device(kr)'][1]))
        
        if korean_count > 4:
            korean_check = True
            
            template_text = """
                제품 정보: {info}

                한글 제품 설명서에서 소제목 기준으로 내용을 추출하여, 제품과 관련된 특화 용어사전을 만들거야.

                다음 문장에서 다음 조건을 만족하는 특화된 한글 용어만 리스트 형태로 추출해줘.
                - 제품과 기술적으로 관련된 특수 단어들만 추출
                - 음식 종류나 향신료 같이 제품과 기술적으로 관련 없는 단어는 절대 추출하지마!
                - 무조건 기술적으로 관련된 단어만 추출해야되.
                - 숫자·영어가 포함된 단어는 제외 (예: 'AC 220 V', 'R-134a' 등)
                - 너무 일반적인 단어는 제외 (예: '탄산음료', '젖은 손' 등)
                - 결과는 리스트 형태로, 용어가 없으면 빈 리스트로 표현
                - 한글로만 구성된 특화단어를를 추출해줘.

                예시 결과: ['용어1', '용어2', '용어3', ...]

                <문장>
                {sentence}
            """
            
            prompt = PromptTemplate(
                input_variables=["info", "sentence"],
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
                            "sentence": sent
                        }
                        
                        chain = prompt | llm4
                        
                        response = chain.invoke(inputs)
                        actual_list = ast.literal_eval(response.content)
                        
                        word_list.update(actual_list)
                        print(word_list)
                        lasttitle = str(pdf_df['lasttitle'][i])
                        sent = '대제목: ' + str(pdf_df['title'][i]) 
                        sent += ', 중제목: ' + str(pdf_df['subtitle'][i]) 
                        sent += ', 소제목: ' + str(pdf_df['lasttitle'][i])
                        sent += ', 내용: ' + str(pdf_df['content'][i])
            
            
            
            folder_path = os.path.join("keywords", cate)
            excel_file = os.path.join(folder_path, f"{name}.xlsx")
            df_key_pdf = pd.DataFrame(word_list, columns=["Keyword"])
            df_key_pdf.to_excel(excel_file, index=False)

###################################################################################################



###################################################################################################
###################################################################################################