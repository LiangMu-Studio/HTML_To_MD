# HTML ↔ Markdown Pro v1.0

批量 HTML 和 Markdown 双向转换工具，支持网页抓取、PDF/DOCX 导出。

## 功能特性

### 📄 格式转换

- **双向转换** - HTML ↔ Markdown 自动检测
- **批量处理** - 支持文件夹批量转换，多线程加速
- **格式导出** - 可选导出 PDF / DOCX（保留格式）
- **自动备份** - 转换前自动备份到 `BACKUP/<日期>/`

### 🌐 网页抓取

- **URL 抓取** - 从网址直接抓取内容
- **正文提取** - 智能提取正文，去除导航、广告等
- **图片内嵌** - 自动下载图片并转为 Base64
- **增强模式** - 使用浏览器抓取（用于反爬虫网站）

### 🎨 界面功能

- **实时预览** - 渲染/纯文本切换
- **MathJax 支持** - 数学公式渲染
- **中英双语** - 支持中文/英文界面切换
- **明暗主题** - 支持浅色/深色主题

## 使用指南

### 第一次使用

1. **启动软件** - 运行 `python main.py` 或打包后的 EXE
2. **批量转换** - 添加文件或文件夹，点击转换按钮
3. **网页抓取** - 切换到"网页抓取"标签，输入 URL 抓取

### 批量转换

1. **添加文件** - 点击"添加文件"或"添加文件夹"
2. **设置输出目录**（可选）- 默认与源文件同目录
3. **选择导出格式**（可选）- 可同时导出 PDF/DOCX
4. **开始转换** - 点击转换按钮

### 网页抓取

1. **输入 URL** - 在输入框中粘贴网址
2. **选择选项**
  - 勾选"正文"提取正文内容
  - 勾选"增强模式"使用浏览器抓取
3. **选择格式** - MD / HTML / PDF / DOCX
4. **点击抓取** - 内容会自动保存到输出目录

## 安装

```bash
pip install -r requirements.txt
```

可选依赖：

- `weasyprint` - PDF 导出
- `python-docx` - DOCX 导出
- `readability-lxml` - 网页正文提取
- `PyQtWebEngine` - 渲染预览
- `DrissionPage` - 增强模式浏览器抓取

## 打包 EXE

```bash
python build.py
```

打包后的 EXE 在 `dist/` 文件夹中。

## 项目结构

```
HTML_To_MD/
├── src/
│   ├── core/            # 核心转换逻辑
│   │   ├── converter.py # HTML/MD 转换
│   │   ├── fetch_url.py # 网页抓取
│   │   └── settings.py  # 配置管理
│   └── ui/              # 界面组件
│       ├── main_window.py
│       └── styles.py
├── tests/               # 单元测试
├── main.py              # 入口文件
├── build.py             # 打包脚本
├── requirements.txt
└── README.md
```

## 快捷键速查

| 快捷键 | 功能  |
| --- | --- |
| `Ctrl+O` | 添加文件 |
| `Delete` | 移除选中文件 |
| `Enter` | 开始转换 |

## 常见问题

**Q: 支持哪些文件格式？**
A: 输入支持 HTML、MD 文件。输出支持 HTML、MD、PDF、DOCX。

**Q: 增强模式是什么？**
A: 增强模式使用真实浏览器抓取网页，可以绑过一些反爬虫机制，获取 JavaScript 渲染后的内容。

**Q: 配置文件在哪里？**
A: 配置保存在程序同目录的 `settings.json` 文件中。

**Q: 支持哪些操作系统？**
A: 主要支持 Windows。增强模式需要系统安装 Chrome/Edge 等 Chromium 内核浏览器。

## 版本历史

### v1.0 (2024-12-29)

- 新增增强模式（浏览器抓取）
- 新增深色主题
- 优化 UI 布局
- 改进正文提取算法

### v0.9

- 初始版本
- 支持 HTML/MD 双向转换
- 网页抓取功能
- PDF/DOCX 导出

## 版本信息

- 当前版本：1.0
- 许可证：MIT License
- 开发者：LiangMu-Studio
- 反馈：[Issues](https://github.com/LiangMu-Studio/HTML_To_MD/issues)
