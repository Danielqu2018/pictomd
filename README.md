# PDF 转 Markdown 工具

一个将 PDF 文档转换为 Markdown 格式的工具，支持多语言 OCR 识别，自动翻译，并使用大语言模型优化输出格式。

## 主要功能

- 支持多种输入格式：
  - PDF文档（扫描版和文本版）
  - 图片文件（PNG, JPG, JPEG, TIFF, BMP, GIF, WEBP）
  - Word文档（`.doc`, `.docx`）
  - 文本文件（`.txt`, `.csv`, `.json`, `.xml`, `.html`, `.md`, `.rst`）
- 多语言 OCR 识别：
  - 简体中文
  - 繁体中文
  - 英文
  - 日文
  - 德语
  - 法语
  - 阿拉伯语
- 三级文本清理选项：
  - 不清理：保留所有OCR识别内容
  - 适当清理：仅清理确定的无用内容
  - 强化清理：更积极地清理可能的干扰内容
- 使用 DeepSeek-V3 模型生成结构化 Markdown
- 保存中间结果，便于检查和修正
- 自动翻译功能：
  - 自动检测文档语言
  - 非中文文档自动翻译成中文
  - 保留原文格式和结构
- Web界面支持：
  - 拖拽上传文件
  - 实时预览源文件
  - 并排显示原文和翻译
  - 支持语言和清理级别选择
  - 所有文件可下载保存

## 安装说明

### 1. 安装 Python 依赖

首先创建并激活虚拟环境（推荐）：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

安装所有依赖：
```bash
pip install -r requirements.txt
```

### 2. 安装系统依赖

#### Windows 系统：

1. **Tesseract OCR**
   - 下载：[Tesseract-OCR installer](https://github.com/UB-Mannheim/tesseract/wiki)
   - 安装到：`C:\Program Files\Tesseract-OCR`
   - 下载语言包：
     - 简体中文：`chi_sim.traineddata`
     - 繁体中文：`chi_tra.traineddata`
     - 日文：`jpn.traineddata`
     - 德语：`deu.traineddata`
     - 法语：`fra.traineddata`
     - 阿拉伯语：`ara.traineddata`

2. **Poppler**
   - 下载：[poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - 解压到：`C:\Program Files\poppler-24.08.0`
   - 将 bin 目录添加到系统环境变量 Path 中

### 3. 配置

1. 复制 `config.py.example` 为 `config.py`
2. 修改 `config.py` 中的配置：
   ```python
   # 设置你的 API key
   API_KEY = "your_api_key_here"
   
   # 如果安装路径不同，修改以下配置
   TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   POPPLER_PATH = r'C:\Program Files\poppler-24.08.0\Library\bin'
   ```

## 使用方法

### Web界面（推荐）：

1. 启动Web服务：
   ```bash
   python web_app.py
   ```

2. 打开浏览器访问：`http://localhost:5000`

3. 在网页上：
   - 选择识别语言
   - 选择清理级别
   - 拖拽或选择文件上传
   - 等待处理完成
   - 查看源文件预览、原始文本和Markdown结果
   - 如果是非中文文档，还可以查看中文翻译
   - 可以下载所有处理结果文件

### 命令行界面：

1. 准备输入文件：
   - 将要转换的文件放在程序同目录下
   - 支持PDF、图片或文本文件

2. 运行程序：
   ```bash
   python pdf_to_markdown.py
   ```

3. 按提示操作：
   - 输入文件名（不带后缀）
   - 选择清理级别（0-2）
   - 等待处理完成

4. 查看结果：
   - `example.md`：转换后的Markdown文件
   - `example_raw.txt`：清理后的原始文本
   - `example_zh.md`：中文翻译（如果原文不是中文）

## 文件说明

处理过程中会生成以下文件：
- `[时间戳]_[原文件名]`：上传的原始文件
- `[时间戳]_[原文件名]_raw.txt`：OCR识别并清理后的原始文本
- `[时间戳]_[原文件名].md`：转换后的Markdown文件
- `[时间戳]_[原文件名]_zh.md`：中文翻译文件（如果原文不是中文）

所有生成的文件都会保留在 `uploads` 目录中，可以通过Web界面下载或直接从目录访问。

## 项目结构
```
.
├── pdf_to_markdown.py # 主程序
├── web_app.py        # Web应用
├── config.py         # 配置文件
├── utils.py         # 工具函数
├── templates/       # HTML模板
│   └── index.html  # 主页面
├── uploads/        # 上传和处理文件目录
├── README.md        # 说明文档
└── .gitignore      # Git忽略配置
```

## 开发环境

- Python 3.7+
- Windows 10/11
- Tesseract-OCR 5.x
- Poppler 24.x
- Flask 2.x

## 更新日志

### v1.2.0 (2025-03)
- ✨ 添加Web界面支持
- 🌍 支持多语言OCR识别
- 🔄 添加自动翻译功能
- 📱 优化用户交互体验
- 💾 保留所有处理文件
- 📥 支持文件下载

### v1.1.0 (2025-03)
- ✨ 添加三级文本清理选项
- 🔧 优化文本处理逻辑
- 📚 完善文档说明

### v1.0.0 (2025-03)
- 🎯 支持中英文 PDF 和图片转换
- 📝 添加文本清理功能
- 🔧 完善错误处理
- 📚 支持多种输入格式