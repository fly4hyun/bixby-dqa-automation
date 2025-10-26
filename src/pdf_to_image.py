###################################################################################################
###################################################################################################

import os
from pdf2image import convert_from_path

###################################################################################################
###################################################################################################

def convert_pdf_to_images(pdf_path, destination_folder):
    pdf_images = convert_from_path(pdf_path)
    for i, image in enumerate(pdf_images):
        image_path = os.path.join(destination_folder, f"{i}.jpg")
        image.save(image_path)


###################################################################################################

pdf_path = 'pdf'
pdf_save_path = 'temp_data'

###################################################################################################

pdf_list = os.listdir(pdf_path)
pdf_num = len(pdf_list)
num = 1
for pdf_file in pdf_list:
    pdf_name, exe_ = os.path.splitext(os.path.basename(pdf_file))

    print(f'{num}/{pdf_num} : {pdf_name}')
    num += 1

    if exe_.lower() != '.pdf':  # 확장자 검사를 위해 소문자로 변환 후 비교
        continue

    # 'exist_ok=True'를 추가하여 이미 폴더가 존재해도 에러를 방지
    os.makedirs(os.path.join(pdf_save_path, pdf_name, 'ori_images'), exist_ok=True)
    convert_pdf_to_images(os.path.join(pdf_path, pdf_file), os.path.join(pdf_save_path, pdf_name, 'ori_images'))


###################################################################################################




###################################################################################################
###################################################################################################