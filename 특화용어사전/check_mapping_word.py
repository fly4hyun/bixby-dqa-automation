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
openai_api_key_2 = ""

llm4 = ChatOpenAI(
    openai_api_key=openai_api_key, 
    model_name='gpt-3.5-turbo', 
    temperature=0
)

llm3 = ChatOpenAI(
    openai_api_key=openai_api_key_2, 
    model_name='gpt-4-0125-preview', 
    temperature=0
)

###################################################################################################


cnt = 1

for cate in list(mapping_pdf.keys()):
    
    os.makedirs(f'keywords/{cate}', exist_ok=True)
    print(cate)
    for name in mapping_pdf[cate]:
        
        koo_list = []
        non_koo_list = []
        
        template_text_lang_check = """
            다음 문장이 어느나라 말인지를 알려줘.
            언어는 [한국어, 영어, 스페인어, 포르투갈어, 독일어, 이탈리아어, 프랑스어]
            이렇게 7가지야
            
            한국어면 KO, 영어면 EN, 스페인어면 ES, 포르투갈어면 PT, 독일어면 DE, 이탈리아어면 IT, 프랑스어면 FR를 출력하면 되
            언어는 한가지 언어로만 되어 있어서 리스트에 해당 언어만 영문으로 다음과 같이 표시하면 되.
            
            예시 결과: ['EN']

            <문장>
            {sentence}
        """
        
        prompt_lang_check = PromptTemplate(
            input_variables=["sentence"],
            template=template_text_lang_check
        )
        
        chain_lang_check = prompt_lang_check | llm3

        
        
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
        
        sent += str(pdf_df['title'][3]) + str(pdf_df['subtitle'][3]) + str(pdf_df['lasttitle'][3]) + str(pdf_df['content'][3])

        inputs_lang_check = {
            "sentence": sent
        }

        response_lang_check = chain_lang_check.invoke(inputs_lang_check)
        try:
            lang_check = ast.literal_eval(response_lang_check.content)
        except Exception as e:
            print("응답 파싱 실패:", e)
            print(name, response_lang_check.content)
            continue
            
        if korean_count > 4:
            korean_check = True
            
        if korean_check == False:
            
            template_text = """
                다음 한글 단어가 다음 리스트에 있는 단어들과 같은 의미인지를 판단할거야.
                다음 단어들 중에 한글 단어와 정확히 일치하는 것만 리스트 형태로 추출해줘.
                
                예시 결과: ["용어1", "용어2", "용어3", ...]
                
                결과는 절대 ["용어1", "용어2", "용어3", ...] 이거 왜 다른 내용이나 글자가 나오면 안되
                
                용어1, 용어2 이 단어들은 한글이 아닌 해당 단어의 언어로 되어 있어야해.
                
                일치하는 단어가 없으면 어떠한 부연설명도 없이 그냥 빈 리스트로 표현해줘.
                
                <한글 단어>
                {ko_words}
                
                <다음 단어 리스트>
                {non_ko_words}

                <다음 단어 언어>
                {lang_info}
            """
            
            prompt = PromptTemplate(
                input_variables=["ko_words", "non_ko_words", "lang_info"],
                template=template_text
            )
            
            non_ko_excel_path = f'keywords/{cate}/{name}.xlsx'
            non_pdf_df = pd.read_excel(non_ko_excel_path, engine='openpyxl')
            
            if 'Language' in list(non_pdf_df.keys()):
                continue
            
            for i in tqdm(range(len(non_pdf_df))):
                ko_w = str(non_pdf_df['Keyword'][i])
                non_ko_list = ast.literal_eval(non_pdf_df['Mapping'][i])
                
                if non_ko_list == []:
                    continue
                
                inputs = {
                    "ko_words": ko_w,
                    "non_ko_words": non_ko_list, 
                    "lang_info": lang_check[0]
                }
                
                chain = prompt | llm4
                response = chain.invoke(inputs)
                
                try:
                    non_ko_words_list = ast.literal_eval(response.content)
                except Exception as e:
                    print("응답 파싱 실패:", e)
                    print(response.content)
                    non_ko_words_list = []
                koo_list.append(ko_w)
                non_koo_list.append(non_ko_words_list)
                
                
            folder_path = os.path.join("keywords", cate)
            excel_file = os.path.join(folder_path, f"{name}.xlsx")
            
            data = []
            for ii in range(len(koo_list)):
                data.append({'Keyword': koo_list[ii], 'Mapping': non_koo_list[ii], 'Language': lang_check[0]})
            df_key_pdf = pd.DataFrame(data, columns=["Keyword", "Mapping", "Language"])
            df_key_pdf.to_excel(excel_file, index=False)

###################################################################################################






###################################################################################################






###################################################################################################






###################################################################################################
###################################################################################################