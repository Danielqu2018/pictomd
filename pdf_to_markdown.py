import os
from pdf2image import convert_from_path  # 用于将PDF转换为图片
import pytesseract  # OCR文字识别工具
import requests  # 用于发送HTTP请求
import json
import fitz  # PyMuPDF，用于处理PDF文件
from typing import List, Optional, Union, Tuple
from PIL import Image  # 图片处理
import re  # 正则表达式
from pathlib import Path  # 路径处理
import langdetect  # 用于语言检测
import docx  # 导入python-docx库
from PIL import ImageEnhance

# 导入配置
from config import (
    API_KEY, TESSERACT_CMD, POPPLER_PATH, API_URL, 
    MODEL_NAME, OCR_LANG, TEMPERATURE, MAX_TOKENS,
    SUPPORTED_IMAGE_FORMATS, SUPPORTED_TEXT_FORMATS, OCR_CONFIG
)
from utils import check_file_exists, ensure_directory_exists

class PDFToMarkdown:
    """PDF/图片/文本转Markdown工具类"""
    
    def __init__(self):
        """初始化配置"""
        self._init_api_config()
        self._init_ocr_config()
        self._init_language_patterns()
        self.ocr_language = 'chi_sim'  # 默认简体中文
        self.need_translation = False   # 默认不需要翻译
    
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
    
    def _init_language_patterns(self):
        """初始化不同语言的清理模式"""
        self.language_patterns = {
            'zh': {  # 中文（简体和繁体）
                'space': r'([^\u4e00-\u9fff])\s+([^\u4e00-\u9fff])',
                'punctuation': r'[""'']+',
                'noise': r'[·・︰]',
                'level2': r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u0020-\u007f\n]'
            },
            'en': {  # 英文
                'space': r'\s+',
                'punctuation': r'[""'']+',
                'noise': r'[·・︰]',
                'level2': r'[^\x20-\x7f\n]'
            },
            'ja': {  # 日文
                'space': r'([^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff])\s+([^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff])',
                'punctuation': r'[""'']+',
                'noise': r'[·・︰]',
                'level2': r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u3000-\u303f\uff00-\uffef\u0020-\u007f\n]'
            },
            'default': {  # 其他语言
                'space': r'\s+',
                'punctuation': r'[""'']+',
                'noise': r'[·・︰]',
                'level2': r'[^\x20-\x7f\n]'
            }
        }
    
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
    
    def set_ocr_language(self, language: str):
        """设置OCR识别语言"""
        self.ocr_language = language
    
    def set_need_translation(self, need_translation: bool):
        """设置是否需要翻译"""
        self.need_translation = need_translation
    
    def process_image(self, image_path: str) -> str:
        """处理单个图片文件，优化OCR识别效果"""
        if not check_file_exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 打开图片
        image = Image.open(image_path)
        
        # 转换为灰度图
        image = image.convert('L')
        
        # 图像增强
        from PIL import ImageEnhance
        # 增加对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        # 增加锐度
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # 放大图片可以提高小字的识别率
        width, height = image.size
        image = image.resize((width*2, height*2), Image.Resampling.LANCZOS)
        
        # 设置OCR配置参数
        custom_config = f'-l {self.ocr_language} --oem 1 --psm 3'
        
        # 进行OCR识别
        try:
            text = pytesseract.image_to_string(
                image, 
                config=custom_config,
                lang=self.ocr_language
            )
            return text
        except Exception as e:
            print(f"OCR识别出错: {str(e)}")
            raise
    
    def extract_text_from_images(self, images: Union[List[Image.Image], List[str]]) -> str:
        """从图片中提取文本"""
        extracted_text = []
        total = len(images)
        
        # 获取语言特定的OCR配置
        custom_config = OCR_CONFIG.get(self.ocr_language, '--oem 1 --psm 3')
        
        for i, image in enumerate(images, 1):
            try:
                if isinstance(image, str):  # 如果是图片路径
                    text = self.process_image(image)
                else:  # 如果是PIL Image对象
                    # 预处理图像
                    image = image.convert('L')  # 转灰度
                    # 增强对比度
                    enhancer = ImageEnhance.Contrast(image)
                    image = enhancer.enhance(2.0)
                    # 增强锐度
                    enhancer = ImageEnhance.Sharpness(image)
                    image = enhancer.enhance(2.0)
                    # 放大图片
                    width, height = image.size
                    image = image.resize((width*2, height*2), Image.Resampling.LANCZOS)
                    
                    text = pytesseract.image_to_string(
                        image,
                        config=custom_config,
                        lang=self.ocr_language
                    )
                extracted_text.append(text)
                print(f'处理进度: {i}/{total}')
            except Exception as e:
                print(f"处理第{i}张图片时出错: {str(e)}")
                
        return '\n'.join(extracted_text)
    
    def detect_language(self, text: str) -> str:
        """
        检测文本主要语言
        返回语言代码：
        'zh_cn' - 简体中文
        'zh_tw' - 繁体中文
        'en' - 英文
        'ja' - 日文
        'de' - 德语
        'fr' - 法语
        'ar' - 阿拉伯语
        """
        try:
            # 根据OCR语言设置优先判断
            if self.ocr_language == 'chi_sim':
                return 'zh_cn'
            elif self.ocr_language == 'chi_tra':
                return 'zh_tw'
            elif self.ocr_language == 'eng':
                return 'en'
            elif self.ocr_language == 'jpn':
                return 'ja'
            elif self.ocr_language == 'deu':
                return 'de'
            elif self.ocr_language == 'fra':
                return 'fr'
            elif self.ocr_language == 'ara':
                return 'ar'
            
            # 如果没有预设语言，则进行自动检测
            # 移除可能影响检测的内容
            cleaned_text = re.sub(r'[0-9\s\W]+', ' ', text)
            
            # 使用 langdetect 进行初步检测
            lang = langdetect.detect(cleaned_text)
            
            # 对中文进行进一步判断（简体/繁体）
            if lang == 'zh':
                # 计算简体和繁体字符的比例
                simplified = len([c for c in cleaned_text if '\u4e00' <= c <= '\u9fff' and c in simplified_chars])
                traditional = len([c for c in cleaned_text if '\u4e00' <= c <= '\u9fff' and c in traditional_chars])
                return 'zh_cn' if simplified >= traditional else 'zh_tw'
            
            # 映射语言代码
            lang_map = {
                'ja': 'ja',
                'de': 'de',
                'fr': 'fr',
                'ar': 'ar',
                'en': 'en'
            }
            
            return lang_map.get(lang, 'en')  # 默认返回英文
        except:
            # 如果检测失败，返回OCR设置的语言
            if self.ocr_language.startswith('chi_'):
                return 'zh_cn' if self.ocr_language == 'chi_sim' else 'zh_tw'
            return 'en'  # 其他情况默认返回英文
    
    def is_text_file(self, file_path: str) -> bool:
        """判断是否为文本文件（包括Word文档）"""
        return Path(file_path).suffix.lower() in SUPPORTED_TEXT_FORMATS
    
    def read_text_file(self, file_path: str) -> Tuple[str, str]:
        """
        读取文本文件并检测编码
        支持Word文档和普通文本文件
        返回：(文本内容, 检测到的语言)
        """
        file_ext = Path(file_path).suffix.lower()
        
        # 处理Word文档
        if file_ext in ['.doc', '.docx']:
            try:
                doc = docx.Document(file_path)
                content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                language = self.detect_language(content)
                return content, language
            except Exception as e:
                print(f"处理Word文档时出错: {str(e)}")
                raise
        
        # 处理其他文本文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    language = self.detect_language(content)
                    return content, language
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"无法以支持的编码格式读取文件: {file_path}")
    
    def clean_text(self, text: str, clean_level: int = 1) -> str:
        """根据语言和清理级别清理文本"""
        if clean_level == 0:
            return text
        
        # 获取语言对应的清理规则
        lang_code = self.ocr_language[:2]  # 获取语言代码前两位
        patterns = self.language_patterns.get(
            lang_code, 
            self.language_patterns['default']
        )
        
        # 基础清理（所有语言通用）
        text = re.sub(r'\r\n', '\n', text)  # 统一换行符
        text = re.sub(r'\n{3,}', '\n\n', text)  # 合并多个空行
        
        # 根据语言特点清理
        if lang_code in ['zh', 'ja']:  # 中文和日文
            text = re.sub(patterns['space'], r'\1\2', text)  # 保留中日文间的空格
        else:  # 其他语言
            text = re.sub(patterns['space'], ' ', text)  # 合并空格
        
        # 清理标点符号
        text = re.sub(patterns['punctuation'], '"', text)
        
        if clean_level >= 1:
            # 清理确定的干扰字符
            text = re.sub(patterns['noise'], '', text)
            
        if clean_level >= 2:
            # 强化清理
            text = re.sub(patterns['level2'], '', text)
        
        return text.strip()
    
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
    
    def translate_to_chinese(self, text: str) -> str:
        """将文本翻译成中文"""
        try:
            # 准备API请求
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的翻译专家。请将输入的文本翻译成中文，保持原有的格式和结构。"
                    },
                    {
                        "role": "user",
                        "content": f"请将以下文本翻译成中文，保持Markdown格式：\n\n{text}"
                    }
                ],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS
            }
            
            # 发送API请求
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"翻译时发生错误: {str(e)}")
            return text
    
    def process_file(self, input_path: str, output_path: str, clean_level: int = 1) -> Optional[dict]:
        """处理输入文件并保存为Markdown"""
        try:
            print(f"开始处理文件: {input_path}")
            file_ext = Path(input_path).suffix.lower()
            
            # 处理文本文件
            if self.is_text_file(input_path):
                print("检测到文本文件，直接处理...")
                raw_text, detected_language = self.read_text_file(input_path)
                print(f"检测到文本语言: {detected_language}")
            # 处理PDF和图片
            elif file_ext == '.pdf':
                if self._is_scanned_pdf(input_path):
                    print("检测到扫描版PDF，使用OCR处理...")
                    images = self.convert_pdf_to_images(input_path)
                    raw_text = self.extract_text_from_images(images)
                else:
                    print("检测到可直接提取文本的PDF...")
                    raw_text = self.extract_text_from_pdf(input_path)
                detected_language = self.detect_language(raw_text)
            elif file_ext in SUPPORTED_IMAGE_FORMATS:
                print("处理图片文件...")
                raw_text = self.process_image(input_path)
                detected_language = self.detect_language(raw_text)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 清理文本
            print(f"使用{detected_language}语言规则清理文本...")
            cleaned_text = self.clean_text(raw_text, clean_level)
            
            # 保存清理后的原始文本
            raw_output_path = output_path.replace('.md', '_raw.txt')
            print(f"保存清理后的原始文本到: {raw_output_path}")
            ensure_directory_exists(raw_output_path)
            with open(raw_output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            # 转换为Markdown
            print("转换为Markdown格式...")
            markdown_text = self.convert_to_markdown(cleaned_text)
            
            print("保存原始语言的Markdown")
            ensure_directory_exists(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            result = {
                'original': markdown_text,
                'translated': None,
                'translated_path': None,
                'language': detected_language
            }
            
            # 根据设置决定是否翻译
            if self.need_translation:
                print("检测到非中文文本，正在翻译...")
                translated_text = self.translate_to_chinese(markdown_text)
                translated_path = output_path.replace('.md', '_zh.md')
                
                # 保存翻译后的Markdown
                with open(translated_path, 'w', encoding='utf-8') as f:
                    f.write(translated_text)
                
                result['translated'] = translated_text
                result['translated_path'] = translated_path
                print(f"翻译完成，结果保存在：{translated_path}")
            
            return result
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
        # 添加文本文件扩展名到检查列表
        supported_extensions = ['.pdf'] + list(SUPPORTED_IMAGE_FORMATS) + ['.txt', '.csv', '.json', '.xml', '.html', '.md', '.rst']
        
        for ext in supported_extensions:
            test_path = f'{input_name}{ext}'
            if check_file_exists(test_path):
                found_file = test_path
                break
        
        if not found_file:
            print(f"错误：未找到文件 {input_name}.*")
            print("支持的文件格式：")
            print("- PDF文件 (.pdf)")
            print("- 图片文件", ", ".join(SUPPORTED_IMAGE_FORMATS))
            print("- 文本文件", ", ".join(SUPPORTED_TEXT_FORMATS))
            return
        
        # 执行转换
        output_path = f'{input_name}.md'
        
        # 修改 process_file 方法调用，传入清理级别
        result = converter.process_file(found_file, output_path, clean_level)
        
        if result:
            print(f'转换完成，结果保存在：{result["original"]}')
            if result['translated']:
                print(f'翻译后的中文版本保存在：{result["translated_path"]}')
        else:
            print('转换失败')
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")

if __name__ == '__main__':
    main()