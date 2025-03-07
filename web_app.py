from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_socketio import SocketIO  # 用于实时进度反馈
import redis  # 用于缓存
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF用于PDF预览
from PIL import Image
import io
import base64
from pdf_to_markdown import PDFToMarkdown
from pathlib import Path
from datetime import datetime, timedelta
import json
import hashlib
from config import LANGUAGE_DISPLAY_NAMES

app = Flask(__name__)
socketio = SocketIO(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 最大文件大小

# Redis缓存配置
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)
CACHE_EXPIRE_TIME = 3600 * 24  # 缓存24小时

# 批量处理配置
MAX_BATCH_FILES = 10  # 最大批量文件数
SUPPORTED_FORMATS = {
    'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
    'image': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'],
    'presentation': ['.ppt', '.pptx'],
    'spreadsheet': ['.xls', '.xlsx', '.csv'],
    'ebook': ['.epub', '.mobi']
}

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'webp',
    'doc', 'docx', 'txt', 'csv', 'json', 'xml', 'html', 'md', 'rst'
}

def allowed_file(filename):
    """检查文件是否为允许的格式"""
    ext = os.path.splitext(filename)[1].lower()
    for formats in SUPPORTED_FORMATS.values():
        if ext in formats:
            return True
    return ext in SUPPORTED_TEXT_FORMATS

def get_file_preview(file_path: str) -> dict:
    """获取文件预览内容"""
    ext = Path(file_path).suffix.lower()
    
    try:
        if ext == '.pdf':
            # PDF预览：获取第一页转为图片
            doc = fitz.open(file_path)
            page = doc[0]
            pix = page.get_pixmap()
            img_data = pix.tobytes()
            img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
            
            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                'type': 'image',
                'data': f'data:image/png;base64,{img_base64}'
            }
            
        elif ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}:
            # 图片预览
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()
            return {
                'type': 'image',
                'data': f'data:image/{ext[1:]};base64,{img_data}'
            }
            
        elif ext in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.rst'}:
            # 文本预览
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                'type': 'text',
                'data': content
            }
            
        elif ext in {'.doc', '.docx'}:
            # Word文档预览：提取文本
            import docx
            doc = docx.Document(file_path)
            content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            return {
                'type': 'text',
                'data': content
            }
            
        else:
            return {
                'type': 'unsupported',
                'data': '不支持预览此类型文件'
            }
    except Exception as e:
        return {
            'type': 'error',
            'data': f'预览生成失败: {str(e)}'
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    try:
        # 获取原始文件名和扩展名
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        base_name = os.path.splitext(original_filename)[0]
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 构建文件路径
        safe_filename = secure_filename(original_filename)
        file_path = os.path.join(
            app.config['UPLOAD_FOLDER'], 
            f"{timestamp}_{safe_filename}"
        )
        
        output_path = os.path.join(
            app.config['UPLOAD_FOLDER'], 
            f"{timestamp}_{base_name}.md"
        )
        
        raw_path = os.path.join(
            app.config['UPLOAD_FOLDER'], 
            f"{timestamp}_{base_name}_raw.txt"
        )
        
        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # 保存上传的文件
        file.save(file_path)
        
        print(f"文件已保存到: {file_path}")
        
        # 获取文件预览
        preview = get_file_preview(file_path)
        
        # 获取参数
        clean_level = int(request.form.get('cleanLevel', 1))
        ocr_language = request.form.get('language', 'chi_sim')
        display_language = LANGUAGE_DISPLAY_NAMES.get(ocr_language, ocr_language)
        
        # 设置语言相关配置
        converter = PDFToMarkdown()
        converter.set_ocr_language(ocr_language)
        
        # 根据OCR语言设置是否需要翻译
        need_translation = not ocr_language.startswith(('chi_sim', 'chi_tra'))
        converter.set_need_translation(need_translation)
        
        # 处理文件
        result = converter.process_file(
            file_path=file_path,
            output_path=output_path,
            clean_level=clean_level
        )
        
        if result:
            # 读取原始文本
            try:
                with open(raw_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
            except FileNotFoundError:
                raw_content = "无法读取原始文本"
            except Exception as e:
                raw_content = f"读取原始文本时出错: {str(e)}"
            
            response_data = {
                'success': True,
                'preview': preview,
                'raw_text': raw_content,
                'markdown': result['original'],
                'language': display_language,
                'file_id': timestamp,
                'original_name': original_filename,
                'files': {
                    'source': f"{timestamp}_{safe_filename}",
                    'raw': f"{timestamp}_{base_name}_raw.txt",
                    'markdown': f"{timestamp}_{base_name}.md"
                }
            }
            
            if result.get('translated'):
                response_data['translated'] = result['translated']
                response_data['files']['translated'] = f"{timestamp}_{base_name}_zh.md"
            
            return jsonify(response_data)
        else:
            return jsonify({'error': '处理文件失败'}), 500
            
    except Exception as e:
        print(f"处理上传文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# 添加文件下载路由
@app.route('/download/<file_id>/<file_type>')
def download_file(file_id, file_type):
    """下载处理后的文件"""
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        target_file = next((f for f in files if f.startswith(file_id) and f.endswith(file_type)), None)
        
        if target_file:
            return send_file(
                os.path.join(app.config['UPLOAD_FOLDER'], target_file),
                as_attachment=True,
                download_name=target_file.replace(file_id + '_', '')
            )
        return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch_upload', methods=['POST'])
def batch_upload():
    """批量文件上传处理"""
    if 'files[]' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
        
    files = request.files.getlist('files[]')
    if len(files) > MAX_BATCH_FILES:
        return jsonify({'error': f'最多支持{MAX_BATCH_FILES}个文件同时处理'}), 400
    
    results = []
    task_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for file in files:
        try:
            # 处理单个文件
            result = process_single_file(file, task_id)
            results.append(result)
        except Exception as e:
            results.append({
                'filename': file.filename,
                'error': str(e)
            })
    
    return jsonify({
        'task_id': task_id,
        'results': results
    })

def process_single_file(file, task_id):
    """处理单个文件，支持进度反馈"""
    try:
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # 检查缓存
        params = {
            'clean_level': request.form.get('cleanLevel', 1),
            'language': request.form.get('language', 'chi_sim')
        }
        
        # 保存文件并获取缓存键
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{task_id}_{secure_filename(original_filename)}")
        file.save(temp_path)
        cache_key = get_cache_key(temp_path, params)
        
        # 检查缓存
        cached_result = redis_client.get(cache_key)
        if cached_result:
            os.remove(temp_path)
            return json.loads(cached_result)
        
        # 实际处理文件
        converter = PDFToMarkdown(progress_callback=lambda p: socketio.emit('progress', {
            'task_id': task_id,
            'filename': original_filename,
            'progress': p
        }))
        
        result = converter.process_file(temp_path, params)
        
        # 保存缓存
        redis_client.setex(cache_key, CACHE_EXPIRE_TIME, json.dumps(result))
        
        os.remove(temp_path)
        return result
        
    except Exception as e:
        raise Exception(f"处理文件 {file.filename} 时出错: {str(e)}")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=True) 