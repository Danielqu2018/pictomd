# PDF to Markdown Converter

一个功能强大的文档转换工具，支持将 PDF、图片和其他格式文档转换为 Markdown 格式。

## 功能特点

- 多格式支持：PDF、Word、图片、演示文稿、电子表格、电子书等
- OCR 文字识别：支持扫描版 PDF 和图片文件
- 多语言支持：中文、英文、日文等多种语言
- 自动翻译：非中文文档自动翻译为中文
- 实时进度反馈：通过 WebSocket 提供处理进度
- 结果缓存：使用 Redis 缓存处理结果
- 批量处理：支持多文件同时处理
- 格式优化：智能优化 Markdown 格式

## 项目结构
```
.
├── pdf_to_markdown.py  # 主程序
├── web_app.py         # Web应用
├── config.py          # 配置文件
├── utils.py          # 工具函数
├── templates/        # HTML模板
│   └── index.html   # 主页面
├── static/          # 静态资源
│   ├── css/        # 样式文件
│   └── js/         # JavaScript文件
├── uploads/         # 上传和处理文件目录
├── requirements.txt  # 依赖清单
├── README.md         # 说明文档
└── .gitignore       # Git忽略配置
```

## 系统要求

- Python 3.8+
- Tesseract OCR
- Poppler Utils
- Redis Server

## 安装步骤

1. 克隆仓库：
```bash
git clone <repository-url>
cd pdf-to-markdown
```

2. 安装 Python 依赖：
```bash
pip install -r requirements.txt
```

3. 安装系统依赖：

Windows:
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)
- [Redis](https://github.com/microsoftarchive/redis/releases)

Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils redis-server
```

4. 配置：
- 复制 `config.py.example` 为 `config.py`
- 修改配置文件中的路径和 API 密钥

## 使用方法

### 命令行方式

```bash
python pdf_to_markdown.py
```
按提示输入文件名和处理选项。

### Web 界面

1. 启动服务器：
```bash
python web_app.py
```

2. 访问 Web 界面：
- 打开浏览器访问 `http://localhost:5000`
- 上传文件并选择处理选项
- 等待处理完成后下载结果

### 下载处理结果

处理完成后可以通过以下方式下载文件：

1. 直接下载链接：
```
http://localhost:5000/download/<file_id>/<file_type>
```

2. 可用的文件类型：
- `source`: 原始上传文件
- `raw`: 提取的原始文本
- `markdown`: 转换后的 Markdown 文件
- `translated`: 翻译后的中文版本（如果有）

3. 示例：
```python
# 下载 Markdown 文件
file_id = "20250224_154538"
download_url = f"http://localhost:5000/download/{file_id}/markdown"

# 下载原始文本
raw_text_url = f"http://localhost:5000/download/{file_id}/raw"

# 下载翻译后的文件（如果存在）
translated_url = f"http://localhost:5000/download/{file_id}/translated"
```

4. 使用 curl 下载：
```bash
# 下载 Markdown 文件
curl -O http://localhost:5000/download/20250224_154538/markdown

# 下载原始文本
curl -O http://localhost:5000/download/20250224_154538/raw
```

### 批量处理

使用 POST 请求访问 `/batch_upload` 接口，支持同时处理多个文件。

## 支持的文件格式

- 文档：
  - PDF (.pdf)
  - Word (.doc, .docx)
  - 文本 (.txt, .rtf, .odt)
- 图片：
  - PNG (.png)
  - JPEG (.jpg, .jpeg)
  - TIFF (.tiff)
  - BMP (.bmp)
  - GIF (.gif)
  - WebP (.webp)
- 演示文稿：
  - PowerPoint (.ppt, .pptx)
- 电子表格：
  - Excel (.xls, .xlsx)
  - CSV (.csv)
- 电子书：
  - EPUB (.epub)
  - MOBI (.mobi)

## API 使用

### 单文件处理
```python
import requests

url = 'http://localhost:5000/upload'
files = {'file': open('example.pdf', 'rb')}
data = {'cleanLevel': 1, 'language': 'chi_sim'}
response = requests.post(url, files=files, data=data)
```

### 批量处理
```python
import requests

url = 'http://localhost:5000/batch_upload'
files = [
    ('files[]', open('file1.pdf', 'rb')),
    ('files[]', open('file2.pdf', 'rb'))
]
response = requests.post(url, files=files)
```

## 配置说明

在使用前需要正确配置以下文件：

1. 复制 `config.py.example` 为 `config.py`
2. 修改 `config.py` 中的配置：
   - 设置 API 密钥
   - 配置 Tesseract OCR 路径
   - 配置 Poppler 路径
   - 根据需要调整其他参数

主要配置项说明：
- `API_KEY`: API访问密钥
- `TESSERACT_CMD`: Tesseract OCR执行文件路径
- `POPPLER_PATH`: Poppler工具路径
- `OCR_LANG`: OCR支持的语言

## 故障排除

1. OCR 识别问题：
   - 检查 Tesseract 安装和路径配置
   - 确保图片质量良好

2. PDF 处理问题：
   - 检查 Poppler 安装和路径配置
   - 确认 PDF 文件未加密

3. 缓存问题：
   - 确保 Redis 服务正在运行
   - 检查 Redis 连接配置

4. API 调用问题：
   - 验证 API 密钥是否正确
   - 检查网络连接

## 开发计划

- [ ] 添加更多文件格式支持
- [ ] 优化处理速度
- [ ] 添加用户界面
- [ ] 支持自定义模板
- [ ] 添加批量导出功能

## 贡献指南

欢迎提交 Pull Request 或创建 Issue。

## 许可证

MIT License

## 作者

[Your Name]

## 更新日志

### v1.0.0 (2024-02-24)
- 初始版本发布
- 支持基本文件格式转换
- 添加 Web 界面
- 实现批量处理功能
