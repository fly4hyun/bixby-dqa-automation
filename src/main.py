###################################################################################################
###################################################################################################

import os
import argparse

import easyocr
from ultralytics import YOLO

from utils.utils_pdf import LoadPDF, YamlProcessor
from utils.utils_yolo import DetectionYOLO
from utils.utils_parsing import load_yaml_data, save_to_xlsx

###################################################################################################
###################################################################################################

def parse_opt():
    parser = argparse.ArgumentParser()
    
    ###############################################################################################
    ### pdf 이름 및 폴더 경로로
    parser.add_argument('--pdf_path', type=str, default='pdf')
    #parser.add_argument('--pdf_path', type=str, default='pdf/핀란드어-378-432-NQ5B6753CA_DG68_01401A_03.pdf')
    
    ###############################################################################################
    ### 라벨링 저장 위치
    parser.add_argument('--labeling_data', type=str, default='temp_data')
    
    ###############################################################################################
    ### 결과 저장 위치
    parser.add_argument('--pdf_to_image_path', type=str, default='pdf_to_image')
    parser.add_argument('--pdf_to_text_path', type=str, default='pdf_results/pdf_text')
    parser.add_argument('--pdf_refined_text_path', type=str, default='pdf_results/pdf_refined_text')
    
    ###############################################################################################
    ### yolo 모델 경로로
    parser.add_argument('--model_path', type=str, default='weights/best.pt')
    parser.add_argument('--datasets', type=str, default='pdf_samsung_datasets', help='datasets name')

    opt = parser.parse_args()
    return opt

###################################################################################################
###################################################################################################

def main(opt):
    
    ###############################################################################################
    
    yolo_model = YOLO(opt.model_path)
    reader = easyocr.Reader(['en', 'ko'], gpu=True)
    
    ###############################################################################################
    ### pdf 단일 파일
    pdf_path = opt.pdf_path
    labeling_path = opt.labeling_data
    if os.path.isfile(pdf_path) and pdf_path.split('/')[-1].split('.')[-1].lower() == 'pdf':
        pdf_name = pdf_path.split('/')[-1].split('.')[0]
        pdf_to_image_path = opt.pdf_to_image_path
        
        ###########################################################################################
        ### pdf 로드 및 이미지 저장
        pdf_parser = LoadPDF(pdf_path, pdf_to_image_path)
        pdf_image_list = pdf_parser.load_image_list()
        pdf_parser.pdf_load_text_save(opt.pdf_to_text_path)
        
        ###########################################################################################
        ### pdf 객체 탐지 및 라벨 로드
        yolo_re = DetectionYOLO(yolo_model, reader, labeling_path, pdf_path)
        yolo_re.detect_and_postprocess(pdf_image_list, pdf_name)

        ###########################################################################################
        ### pdf DQA Data 처리
        processor = YamlProcessor(pdf_path, opt.pdf_to_text_path, opt.pdf_refined_text_path, labeling_path)
        processor.process_yaml()
        
        ###########################################################################################
        ### YAML 데이터 로드
        yaml_data = load_yaml_data(pdf_name)
        
        ###########################################################################################
        ### CSV 파일 저장
        save_to_xlsx(pdf_name, yaml_data)
    
    ###############################################################################################
    ### pdf 폴더 내 모든 파일
    else:
        pdf_list = os.listdir(pdf_path)
        for pdf_path_one in pdf_list:
            pdf_path_one = os.path.join(pdf_path, pdf_path_one)
            pdf_name = pdf_path_one.split('\\')[-1].split('.')[0]
            pdf_name = pdf_name.split('/')[-1]
            pdf_to_image_path = opt.pdf_to_image_path
            
            #######################################################################################
            ### pdf 로드 및 이미지 저장
            pdf_parser = LoadPDF(pdf_path_one, pdf_to_image_path)
            pdf_image_list = pdf_parser.load_image_list()
            pdf_parser.pdf_load_text_save(opt.pdf_to_text_path)

            #######################################################################################
            ### pdf 객체 탐지 및 라벨 로드
            yolo_re = DetectionYOLO(yolo_model, reader, labeling_path, pdf_path_one)
            print(pdf_name)
            yolo_re.detect_and_postprocess(pdf_image_list, pdf_name)

            #######################################################################################
            ### pdf DQA Data 처리
            processor = YamlProcessor(pdf_path_one, opt.pdf_to_text_path, opt.pdf_refined_text_path, labeling_path)
            processor.process_yaml()

            #######################################################################################
            ### YAML 데이터 로드
            yaml_data = load_yaml_data(pdf_name)

            #######################################################################################
            ### CSV 파일 저장
            save_to_xlsx(pdf_name, yaml_data)

###################################################################################################
###################################################################################################

if __name__ == "__main__":
    opt = parse_opt()
    main(opt)

###################################################################################################
###################################################################################################