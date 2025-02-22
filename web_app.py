from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF用于PDF预览
from PIL import Image
import io
import base64
from pdf_to_markdown import PDFToMarkdown
from pathlib import Path

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
        # 保存上传的文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 获取文件预览
        preview = get_file_preview(file_path)
        
        # 获取参数
        clean_level = int(request.form.get('cleanLevel', 1))
        ocr_language = request.form.get('language', 'chi_sim')  # 默认简体中文
        
        # 处理文件
        converter = PDFToMarkdown()
        # 设置OCR语言
        converter.set_ocr_language(ocr_language)
        
        output_path = os.path.join(
            app.config['UPLOAD_FOLDER'], 
            f"{Path(filename).stem}.md"
        )
        result = converter.process_file(file_path, output_path, clean_level)
        
        if result:
            # 读取原始文本
            raw_path = output_path.replace('.md', '_raw.txt')
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            response_data = {
                'success': True,
                'preview': preview,
                'raw_text': raw_content,
                'markdown': result['original'],
                'language': result['language']
            }
            
            # 如果有翻译版本，添加到响应中
            if result['translated']:
                response_data['translated'] = result['translated']
            
            return jsonify(response_data)
        else:
            return jsonify({'error': '处理文件失败'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理临时文件
        try:
            os.remove(file_path)
            os.remove(output_path)
            os.remove(raw_path)
        except:
            pass

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=True) 