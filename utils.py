import os

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