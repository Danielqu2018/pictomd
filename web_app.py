from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF用于PDF预览
from PIL import Image
import io
import base64
from pdf_to_markdown import PDFToMarkdown
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 最大文件大小

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'webp',
    'doc', 'docx', 'txt', 'csv', 'json', 'xml', 'html', 'md', 'rst'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400
    
    try:
        # 生成唯一的文件标识符
        file_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 构建文件路径
        filename = secure_filename(file.filename)
        base_name = Path(filename).stem
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{base_name}.md")
        raw_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{base_name}_raw.txt")
        
        # 保存上传的文件
        file.save(file_path)
        
        # 获取文件预览
        preview = get_file_preview(file_path)
        
        # 获取参数
        clean_level = int(request.form.get('cleanLevel', 1))
        ocr_language = request.form.get('language', 'chi_sim')
        
        # 设置语言相关配置
        converter = PDFToMarkdown()
        converter.set_ocr_language(ocr_language)
        
        # 根据OCR语言设置是否需要翻译
        need_translation = not ocr_language.startswith(('chi_sim', 'chi_tra'))
        converter.set_need_translation(need_translation)
        
        # 处理文件
        result = converter.process_file(file_path, output_path, clean_level)
        
        if result:
            # 读取原始文本
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # 设置响应的语言标识
            language_display = {
                'chi_sim': 'zh_cn',
                'chi_tra': 'zh_tw',
                'eng': 'en',
                'jpn': 'ja',
                'deu': 'de',
                'fra': 'fr',
                'ara': 'ar'
            }.get(ocr_language, ocr_language)
            
            response_data = {
                'success': True,
                'preview': preview,
                'raw_text': raw_content,
                'markdown': result['original'],
                'language': language_display,  # 使用OCR语言设置
                'file_id': file_id,
                'original_name': filename,
                'files': {
                    'source': f"{file_id}_{filename}",
                    'raw': f"{file_id}_{base_name}_raw.txt",
                    'markdown': f"{file_id}_{base_name}.md"
                }
            }
            
            if result['translated']:
                translated_path = output_path.replace('.md', '_zh.md')
                response_data['translated'] = result['translated']
                response_data['files']['translated'] = f"{file_id}_{base_name}_zh.md"
            
            return jsonify(response_data)
        else:
            return jsonify({'error': '处理文件失败'}), 500
            
    except Exception as e:
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

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=True) 