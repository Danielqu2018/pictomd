# PDF 转 Markdown 工具

一个将 PDF 文档转换为 Markdown 格式的工具，支持中英文 OCR 识别，并使用大语言模型优化输出格式。

## 主要功能

- 支持中英文 PDF 文档转换
- OCR 文字识别（基于 Tesseract）
- 自动清理和格式化文本
- 使用 DeepSeek-V3 模型生成结构化 Markdown
- 保存 OCR 原始文本，方便对比和修正

## 快速开始

### 1. 安装依赖
bash
安装 Python 包
pip install pdf2image pytesseract requests pillow


### 2. 安装必要的系统组件

#### Windows 系统：

1. **Tesseract OCR**
   - 下载：[Tesseract-OCR installer](https://github.com/UB-Mannheim/tesseract/wiki)
   - 安装到：`C:\Program Files\Tesseract-OCR`
   - 确保安装中文语言包

2. **Poppler**
   - 下载：[poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - 解压到：`C:\Program Files\poppler-24.08.0`

### 3. 配置

1. 复制 `config.py.example` 为 `config.py`
2. 修改 `config.py` 中的配置：
   ```python
   # 设置你的 API key
   API_KEY = "your_api_key_here"
   
   # 如果需要，修改其他配置项
   TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   POPPLER_PATH = r'C:\Program Files\poppler-24.08.0\Library\bin'
   ```

### 4. 使用方法

1. 将 PDF 文件放在程序目录下
2. 运行程序：
   ```bash
   python pdf_to_markdown.py
   ```
3. 输入 PDF 文件名（不需要 .pdf 后缀）
4. 等待转换完成

### 5. 输出文件

- `{文件名}_ocr.txt`：OCR 识别的原始文本
- `{文件名}.md`：转换后的 Markdown 文件

## 常见问题

### OCR 识别效果不理想？
- 确保 PDF 文件清晰度高
- 检查 Tesseract 中文语言包是否正确安装
- 可以尝试调整 config.py 中的 OCR 相关参数

### 程序报错？
- 检查所有依赖是否正确安装
- 确认 Tesseract 和 Poppler 的安装路径是否正确
- 验证 API key 是否有效

### 转换很慢？
- OCR 识别需要一定时间，尤其是多页文档
- 可以尝试减小 PDF 文件大小
- 检查网络连接状况

## 注意事项

- PDF 文件质量直接影响识别效果
- 建议先用小文件测试
- API 调用可能产生费用
- 保持网络连接稳定

## 项目结构
.
├── pdf_to_markdown.py # 主程序
├── config.py # 配置文件
├── utils.py # 工具函数
├── README.md # 说明文档
└── .gitignore # Git 忽略配置


## 开发环境

- Python 3.7+
- Windows 10/11
- Tesseract-OCR 5.x
- Poppler 24.x

## 更新日志

### v1.0.0 (2024-03)
- ✨ 首次发布
- 🎯 支持中英文 PDF 转换
- 📝 添加 OCR 文本保存功能
- 🔧 完善错误处理