import os
import shutil
from typing import Optional, List
import re

def check_file_exists(file_path: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(file_path)

def ensure_directory_exists(file_path: str) -> None:
    """确保目录存在"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def get_file_name(file_path: str) -> str:
    """获取不带扩展名的文件名"""
    return os.path.splitext(os.path.basename(file_path))[0]

def backup_file(file_path: str) -> Optional[str]:
    """备份文件，返回备份文件路径"""
    if not os.path.exists(file_path):
        return None
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    return backup_path

def clean_temp_files(directory: str, pattern: str = "*_temp.*") -> None:
    """清理临时文件"""
    import glob
    for temp_file in glob.glob(os.path.join(directory, pattern)):
        try:
            os.remove(temp_file)
        except OSError:
            pass

def clean_markdown_format(text: str) -> str:
    """
    清理和规范化Markdown格式
    
    Args:
        text: 要清理的Markdown文本
        
    Returns:
        清理后的Markdown文本
    """
    # 移除代码块标记和语言标识
    text = re.sub(r'```\s*markdown\s*\n', '', text)
    text = re.sub(r'```\s*\n', '', text)
    text = re.sub(r'```\s*$', '', text)
    
    # 统一换行符
    text = text.replace('\r\n', '\n')
    
    # 合并多个空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 确保标题和正文之间有空行
    text = re.sub(r'(#+\s+.+)\n([^#\n])', r'\1\n\n\2', text)
    
    # 规范化列表格式
    text = re.sub(r'^\s*[-*+]\s+', '- ', text, flags=re.MULTILINE)
    
    # 规范化标题格式
    text = re.sub(r'^(#+)([^#\s])', r'\1 \2', text, flags=re.MULTILINE)
    
    # 移除多余的空格
    text = re.sub(r' +$', '', text, flags=re.MULTILINE)
    
    # 确保文档以换行符结尾
    text = text.strip() + '\n'
    
    return text

def merge_markdown_chunks(chunks: List[str]) -> str:
    """
    合并Markdown文本块，处理重复的标题等问题
    
    Args:
        chunks: Markdown文本块列表
        
    Returns:
        合并后的Markdown文本
    """
    merged = []
    seen_headers = set()
    current_level = 0  # 跟踪当前标题级别
    
    for chunk in chunks:
        # 清理当前块的格式
        chunk = clean_markdown_format(chunk)
        
        # 提取所有标题
        headers = re.findall(r'^(#+)\s+(.+)$', chunk, re.MULTILINE)
        
        # 处理标题
        for level, title in headers:
            level_num = len(level)
            header = f"{level} {title}"
            
            # 如果标题已存在，移除该标题
            if header in seen_headers:
                chunk = re.sub(f"^{re.escape(header)}$\n+", '', chunk, flags=re.MULTILINE)
            else:
                seen_headers.add(header)
                # 更新当前标题级别
                current_level = level_num
        
        # 添加处理后的块
        if chunk.strip():
            merged.append(chunk)
    
    # 合并所有块
    merged_text = '\n'.join(merged)
    
    # 最终清理
    return clean_markdown_format(merged_text) 