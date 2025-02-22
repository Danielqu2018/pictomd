import os
from pdf2image import convert_from_path
import pytesseract
import requests
import json
from typing import List, Optional
from PIL import Image

from config import (
    API_KEY, TESSERACT_CMD, POPPLER_PATH, API_URL, 
    MODEL_NAME, OCR_LANG, TEMPERATURE, MAX_TOKENS
)
from utils import check_file_exists, ensure_directory_exists

class PDFToMarkdown:
    """PDF转Markdown工具类"""
    
    def __init__(self):
        """初始化配置"""
        self._init_api_config()
        self._init_ocr_config()
    
    def _init_api_config(self):
        """初始化API配置"""
        self.api_url = API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
    
    def _init_ocr_config(self):
        """初始化OCR配置"""
        if os.name == 'nt':
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            self.poppler_path = POPPLER_PATH
    
    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """将PDF转换为图片列表"""
        if not check_file_exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        if os.name == 'nt':
            return convert_from_path(pdf_path, poppler_path=self.poppler_path)
        return convert_from_path(pdf_path)
    
    def extract_text_from_images(self, images: List[Image.Image]) -> str:
        """从图片中提取文本"""
        extracted_text = []
        for i, image in enumerate(images, 1):
            try:
                text = pytesseract.image_to_string(image, lang=OCR_LANG)
                extracted_text.append(text)
                print(f"已完成第 {i}/{len(images)} 页的文字识别")
            except Exception as e:
                print(f"处理第 {i} 页时发生错误: {str(e)}")
                extracted_text.append("")
        
        return '\n'.join(extracted_text)
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(cleaned_lines)
    
    def convert_to_markdown(self, text: str) -> str:
        """将文本转换为Markdown格式"""
        try:
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个文本格式转换专家，擅长将文本转换为结构清晰的 Markdown 格式。"
                    },
                    {
                        "role": "user",
                        "content": f"请将以下文本转换为结构良好的 Markdown 格式，保持原有的层级结构和重要信息：\n\n{text}"
                    }
                ],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"调用 API 时发生错误: {str(e)}")
            return text
    
    def process_pdf(self, pdf_path: str, output_path: str) -> Optional[str]:
        """处理PDF文件并保存为Markdown"""
        try:
            print("开始转换PDF为图片...")
            images = self.convert_pdf_to_images(pdf_path)
            
            print("开始提取文本...")
            raw_text = self.extract_text_from_images(images)
            
            print("清理文本...")
            cleaned_text = self.clean_text(raw_text)
            
            # 保存原始OCR文本
            ocr_output_path = output_path.replace('.md', '_ocr.txt')
            print(f"保存OCR识别文本到: {ocr_output_path}")
            ensure_directory_exists(ocr_output_path)
            with open(ocr_output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            print("转换为Markdown格式...")
            markdown_text = self.convert_to_markdown(cleaned_text)
            
            print("保存Markdown结果...")
            ensure_directory_exists(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            return output_path
        except Exception as e:
            print(f"处理PDF时发生错误: {str(e)}")
            return None

def main():
    """主函数"""
    try:
        converter = PDFToMarkdown()
        
        pdf_name = input('请输入要转换的PDF文件名(不带后缀): ')
        pdf_path = f'{pdf_name}.pdf'
        output_path = f'{pdf_name}.md'
        
        if not check_file_exists(pdf_path):
            print(f"错误：文件 {pdf_path} 不存在")
            return
        
        result_path = converter.process_pdf(pdf_path, output_path)
        if result_path:
            print(f'转换完成，结果保存在：{result_path}')
        else:
            print('转换失败')
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")

if __name__ == '__main__':
    main() 