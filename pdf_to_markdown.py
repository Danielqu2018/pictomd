import os
from pdf2image import convert_from_path  # 用于将PDF转换为图片
import pytesseract  # OCR文字识别工具
import requests  # 用于发送HTTP请求
import json
import fitz  # PyMuPDF，用于处理PDF文件
from typing import List, Optional, Union  # 类型提示
from PIL import Image  # 图片处理
import re  # 正则表达式
from pathlib import Path  # 路径处理

# 导入配置
from config import (
    API_KEY, TESSERACT_CMD, POPPLER_PATH, API_URL, 
    MODEL_NAME, OCR_LANG, TEMPERATURE, MAX_TOKENS,
    SUPPORTED_IMAGE_FORMATS
)
from utils import check_file_exists, ensure_directory_exists

class PDFToMarkdown:
    """PDF/图片转Markdown工具类"""
    
    def __init__(self):
        """初始化配置"""
        self._init_api_config()  # 初始化API相关配置
        self._init_ocr_config()  # 初始化OCR相关配置
    
    def _init_api_config(self):
        """初始化API配置"""
        self.api_url = API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"  # 设置API认证头
        }
    
    def _init_ocr_config(self):
        """初始化OCR配置"""
        if os.name == 'nt':  # Windows系统
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD  # 设置Tesseract路径
            self.poppler_path = POPPLER_PATH  # 设置Poppler路径
    
    def _is_scanned_pdf(self, pdf_path: str) -> bool:
        """
        判断是否为扫描版PDF
        通过尝试提取文本来判断：如果无法提取文本，则认为是扫描版
        """
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            if not text.strip():  # 如果页面没有可提取的文本
                return True
        return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        从PDF中直接提取文本（用于非扫描版PDF）
        使用PyMuPDF提取每页文本并合并
        """
        doc = fitz.open(pdf_path)
        text = []
        for page in doc:
            text.append(page.get_text())
        return "\n".join(text)
    
    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        将PDF转换为图片列表
        用于扫描版PDF的处理
        """
        if not check_file_exists(pdf_path):
            raise FileNotFoundError(f"文件不存在: {pdf_path}")
            
        if os.name == 'nt':
            return convert_from_path(pdf_path, poppler_path=self.poppler_path)
        return convert_from_path(pdf_path)
    
    def process_image(self, image_path: str) -> str:
        """
        处理单个图片文件
        使用OCR识别图片中的文字
        """
        if not check_file_exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        image = Image.open(image_path)
        return pytesseract.image_to_string(image, lang=OCR_LANG)
    
    def extract_text_from_images(self, images: Union[List[Image.Image], List[str]]) -> str:
        """
        从图片中提取文本
        支持处理图片对象列表或图片路径列表
        """
        extracted_text = []
        total = len(images)
        
        for i, image in enumerate(images, 1):
            try:
                if isinstance(image, str):  # 如果是图片路径
                    text = self.process_image(image)
                else:  # 如果是PIL Image对象
                    text = pytesseract.image_to_string(image, lang=OCR_LANG)
                extracted_text.append(text)
                print(f"已完成第 {i}/{total} 个文件的文字识别")
            except Exception as e:
                print(f"处理第 {i} 个文件时发生错误: {str(e)}")
                extracted_text.append("")
        
        return '\n'.join(extracted_text)
    
    def clean_text(self, text: str, clean_level: int = 1) -> str:
        """
        根据清理级别清理文本
        clean_level: 
            0 - 不清理
            1 - 适当清理（默认）
            2 - 强化清理
        """
        if clean_level == 0:
            return text
        
        lines = text.split('\n')
        cleaned_lines = []
        
        # 基本的无用内容过滤（适当清理）
        basic_patterns = [
            # 页码
            r'^Page \d+ of \d+$',  # 标准页码格式
            r'^第\s*\d+\s*页\s*共\s*\d+\s*页$',  # 中文页码
            
            # 传真页眉
            r'^To:\s*\d{8,}',  # 传真号码
            r'^From:\s*\d{8,}',  # 传真号码
            r'^Date:\s*\d{2,4}[-/]\d{1,2}[-/]\d{1,2}',  # 日期
            r'^Time:\s*\d{1,2}:\d{2}',  # 时间
            
            # 空白行
            r'^\s*$',
        ]
        
        # 强化清理的额外规则
        advanced_patterns = [
            r'^[A-Za-z\s\d]+$',  # 纯英文和数字的行
            r'.*[A-Z]{3,}.*$',  # 包含3个以上连续大写字母的行
            r'^\W*(?:[A-Za-z]\W*){1,3}$',  # 少于3个字母的独立行
            r'.*[^\u4e00-\u9fff\w\s,.，。、：:；;！!？?（）()《》<>""\'\']+.*$',  # 包含过多特殊字符的行
        ]
        
        # 根据清理级别选择过滤规则
        patterns = [re.compile(pattern) for pattern in basic_patterns]
        if clean_level == 2:
            patterns.extend([re.compile(pattern) for pattern in advanced_patterns])
        
        def clean_line(line: str, level: int) -> str:
            """根据清理级别清理行内容"""
            line = line.strip()
            
            if level == 1:
                # 适当清理：只合并多余的空白字符
                line = re.sub(r'[\s\u3000]{2,}', ' ', line)
            elif level == 2:
                # 强化清理：清理特殊字符和格式
                line = re.sub(r'^[^\u4e00-\u9fff\w]+', '', line)  # 清理行首非中文和字母数字的字符
                line = re.sub(r'[^\u4e00-\u9fff\w]+$', '', line)  # 清理行尾非中文和字母数字的字符
                line = re.sub(r'[^\u4e00-\u9fff\w\s,.，。、：:；;！!？?（）()《》<>""\'\']+', ' ', line)
                line = re.sub(r'\s+', ' ', line)
            
            return line
        
        # 处理每一行
        for line in lines:
            line = line.strip()
            
            if not line:  # 跳过空行
                continue
            
            # 根据清理级别跳过无用内容
            if any(pattern.match(line) for pattern in patterns):
                continue
            
            # 清理行内容
            line = clean_line(line, clean_level)
            
            if line:
                cleaned_lines.append(line)
        
        # 合并短行（仅在清理级别>0时）
        if clean_level > 0:
            merged_lines = []
            i = 0
            while i < len(cleaned_lines):
                current_line = cleaned_lines[i]
                if i + 1 < len(cleaned_lines):
                    next_line = cleaned_lines[i + 1]
                    # 根据清理级别调整合并条件
                    merge_condition = (
                        len(current_line) < 20 and
                        not current_line.endswith(('。', '！', '？', '：', '；', '.', '!', '?', ':', ';'))
                    )
                    if clean_level == 2:
                        # 强化清理时更激进地合并行
                        merge_condition = merge_condition and len(next_line) < 30
                    else:
                        # 适当清理时更保守
                        merge_condition = merge_condition and len(next_line) < 20 and not re.match(r'^[一二三四五六七八九十]、|^\d+\.|^[①②③④⑤⑥⑦⑧⑨⑩]', next_line)
                    
                    if merge_condition:
                        merged_lines.append(current_line + next_line)
                        i += 2
                        continue
                merged_lines.append(current_line)
                i += 1
            return '\n'.join(merged_lines)
        
        return '\n'.join(cleaned_lines)
    
    def convert_to_markdown(self, text: str) -> str:
        """
        将文本转换为Markdown格式
        使用大语言模型进行格式转换
        """
        try:
            # 准备API请求
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
            
            # 发送API请求
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()  # 检查请求是否成功
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"调用 API 时发生错误: {str(e)}")
            return text  # 出错时返回原始文本
    
    def process_file(self, input_path: str, output_path: str, clean_level: int = 1) -> Optional[str]:
        """
        处理输入文件（PDF或图片）并保存为Markdown
        clean_level: 文本清理级别（0-不清理，1-适当清理，2-强化清理）
        """
        try:
            print(f"开始处理文件: {input_path}")
            file_ext = Path(input_path).suffix.lower()
            
            # 根据文件类型选择处理方式
            if file_ext == '.pdf':
                if self._is_scanned_pdf(input_path):
                    print("检测到扫描版PDF，使用OCR处理...")
                    images = self.convert_pdf_to_images(input_path)
                    raw_text = self.extract_text_from_images(images)
                else:
                    print("检测到可直接提取文本的PDF...")
                    raw_text = self.extract_text_from_pdf(input_path)
            elif file_ext in SUPPORTED_IMAGE_FORMATS:
                print("处理图片文件...")
                raw_text = self.process_image(input_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 清理和保存文本
            print("清理文本...")
            cleaned_text = self.clean_text(raw_text, clean_level)
            
            # 保存清理后的原始文本
            raw_output_path = output_path.replace('.md', '_raw.txt')
            print(f"保存清理后的原始文本到: {raw_output_path}")
            ensure_directory_exists(raw_output_path)
            with open(raw_output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            # 转换为Markdown并保存
            print("转换为Markdown格式...")
            markdown_text = self.convert_to_markdown(cleaned_text)
            
            print("保存Markdown结果...")
            ensure_directory_exists(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            return output_path
        except Exception as e:
            print(f"处理文件时发生错误: {str(e)}")
            return None

def main():
    """主函数：处理用户输入并执行转换流程"""
    try:
        converter = PDFToMarkdown()
        
        # 获取用户输入的文件名
        input_name = input('请输入要转换的文件名(不带后缀): ')
        
        # 选择清理级别
        print("\n请选择文本清理级别：")
        print("0 - 不清理（保留所有OCR识别内容）")
        print("1 - 适当清理（仅清理确定的无用内容）")
        print("2 - 强化清理（更积极地清理可能的干扰内容）")
        
        clean_level = -1
        while clean_level not in [0, 1, 2]:
            try:
                clean_level = int(input("请输入清理级别(0-2): "))
            except ValueError:
                print("请输入有效的数字(0-2)")
        
        # 检查所有支持的文件格式
        found_file = None
        for ext in ['.pdf'] + list(SUPPORTED_IMAGE_FORMATS):
            test_path = f'{input_name}{ext}'
            if check_file_exists(test_path):
                found_file = test_path
                break
        
        if not found_file:
            print(f"错误：未找到文件 {input_name}.*")
            return
        
        # 执行转换
        output_path = f'{input_name}.md'
        
        # 修改 process_file 方法调用，传入清理级别
        result_path = converter.process_file(found_file, output_path, clean_level)
        
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