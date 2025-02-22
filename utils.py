import os
import shutil
from typing import Optional

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