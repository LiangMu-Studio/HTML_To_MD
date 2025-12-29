"""
Markdown 规则处理引擎 - 基于CommonMark规范
完整支持Mark Text的所有Markdown语法
可独立使用，无外部依赖
"""

import re
from typing import List, Dict, Optional, Tuple


class MarkdownParser:
    """Markdown解析器"""

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split('\n')
        self.pos = 0
        self.result = []

    def parse(self) -> str:
        """解析Markdown文本"""
        while self.pos < len(self.lines):
            line = self.lines[self.pos]

            # 空行
            if not line.strip():
                self.pos += 1
                continue

            # 标题 # ## ### 等
            if match := re.match(r'^(#{1,6})\s+(.+)$', line):
                level = len(match.group(1))
                content = self._process_inline(match.group(2))
                self.result.append(f'<h{level}>{content}</h{level}>')
                self.pos += 1
                continue

            # 分割线 --- *** ___
            if re.match(r'^(\*{3,}|-{3,}|_{3,})$', line.strip()):
                self.result.append('<hr/>')
                self.pos += 1
                continue

            # 代码块 ```
            if line.strip().startswith('```'):
                self._parse_code_block()
                continue

            # 引用块 >
            if line.startswith('>'):
                self._parse_blockquote()
                continue

            # 列表
            if re.match(r'^\s*[*\-+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                self._parse_list()
                continue

            # 普通段落
            content = self._process_inline(line)
            self.result.append(f'<p>{content}</p>')
            self.pos += 1

        return '\n'.join(self.result)

    def _parse_code_block(self):
        """解析代码块"""
        self.pos += 1
        code_lines = []
        lang = ''

        # 获取语言标识
        if self.pos > 0:
            first_line = self.lines[self.pos - 1]
            lang = first_line[3:].strip()

        # 收集代码行
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if line.strip().startswith('```'):
                self.pos += 1
                break
            code_lines.append(line)
            self.pos += 1

        # 先转义每行，再用<br>连接
        escaped_lines = [line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for line in code_lines]
        code = '<br>'.join(escaped_lines)

        lang_label = f'<div class="code-lang">{lang}</div>' if lang else ''
        html = f'<div class="code-block">{lang_label}<pre><code class="language-{lang if lang else "text"}">{code}</code></pre></div>'

        self.result.append(html)

    def _parse_blockquote(self):
        """解析引用块"""
        quote_lines = []

        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if not line.startswith('>'):
                break
            quote_lines.append(line[1:].lstrip())
            self.pos += 1

        quote_text = '\n'.join(quote_lines)
        parser = MarkdownParser(quote_text)
        inner_html = parser.parse()
        self.result.append(f'<blockquote>{inner_html}</blockquote>')

    def _parse_list(self):
        """解析列表"""
        list_items = []
        list_type = None

        while self.pos < len(self.lines):
            line = self.lines[self.pos]

            # 检查无序列表
            if match := re.match(r'^(\s*)([*\-+])\s+(.+)$', line):
                indent = len(match.group(1))
                content = match.group(3)
                list_items.append({
                    'type': 'unordered',
                    'indent': indent,
                    'content': content
                })
                self.pos += 1
                continue

            # 检查有序列表
            if match := re.match(r'^(\s*)(\d+)\.\s+(.+)$', line):
                indent = len(match.group(1))
                content = match.group(3)
                list_items.append({
                    'type': 'ordered',
                    'indent': indent,
                    'content': content
                })
                self.pos += 1
                continue

            # 列表项延续（缩进的行）
            if line and line[0] == ' ' and list_items:
                list_items[-1]['content'] += '\n' + line
                self.pos += 1
                continue

            break

        # 生成HTML
        self._generate_list_html(list_items)

    def _generate_list_html(self, items: List[Dict]):
        """生成列表HTML"""
        if not items:
            return

        html = []
        stack = []  # 用于跟踪嵌套级别

        for item in items:
            indent = item['indent'] // 4
            content = self._process_inline(item['content'])

            # 关闭更深层的列表
            while stack and stack[-1] >= indent:
                stack.pop()
                html.append('</ul>')

            # 打开新的列表
            while len(stack) < indent + 1:
                html.append('<ul>')
                stack.append(len(stack))

            # 添加列表项
            html.append(f'<li>{content}</li>')

        # 关闭所有打开的列表
        while stack:
            stack.pop()
            html.append('</ul>')

        self.result.extend(html)

    def _process_inline(self, text: str) -> str:
        """处理行内格式"""
        # 代码 `code`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # 加粗 **text** 或 __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

        # 斜体 *text* 或 _text_
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)

        # 删除线 ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)

        # 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

        # 图片 ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1"/>', text)

        return text


# 向后兼容接口
class MarkdownRules:
    """Markdown规则处理类"""

    BULLET_SYMBOL = '●'
    LIST_INDENT_SPACES = 4
    UNORDERED_MARKERS = ['-', '*', '+']
    LIST_INDENT_TAB = '\t'

    @classmethod
    def configure(cls, **kwargs):
        """配置规则参数"""
        for key, value in kwargs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)

    @staticmethod
    def to_html(text: str) -> str:
        """将Markdown转换为HTML"""
        try:
            parser = MarkdownParser(text)
            return parser.parse()
        except Exception as e:
            import logging
            logging.error(f"Markdown解析错误: {e}")
            # 降级：返回纯文本HTML
            import html
            return f'<p>{html.escape(text)}</p>'

    @staticmethod
    def normalize_list_indent(text: str) -> str:
        """规范化列表缩进"""
        lines = text.split('\n')
        result = []

        for line in lines:
            match = re.match(r'^(\s+)([*\-+])\s+', line)
            if match:
                indent = match.group(1)
                marker = match.group(2)
                content = line[match.end():]
                level = len(indent) // 4
                new_indent = '    ' * level
                result.append(f'{new_indent}{marker} {content}')
            else:
                result.append(line)

        return '\n'.join(result)

    @staticmethod
    def convert_bullet_to_dot(text: str) -> str:
        """将列表标记符转换为圆点"""
        lines = text.split('\n')
        result = []

        for line in lines:
            match = re.match(r'^(\s*)([*\-+])\s+(.*)$', line)
            if match:
                indent = match.group(1)
                content = match.group(3)
                result.append(f'{indent}● {content}')
            else:
                result.append(line)

        return '\n'.join(result)

    @staticmethod
    def is_list_item(line: str) -> bool:
        """检查一行是否是列表项"""
        return bool(re.match(r'^\s*[*\-+]\s+', line))

    @staticmethod
    def get_list_level(line: str) -> int:
        """获取列表项的缩进级别"""
        match = re.match(r'^(\s+)', line)
        if not match:
            return 0
        indent = match.group(1)
        if indent.startswith('\t'):
            return indent.count('\t')
        else:
            return len(indent) // 4

    @staticmethod
    def parse_list_structure(text: str) -> List[Dict]:
        """解析列表结构"""
        lines = text.split('\n')
        items = []

        for line in lines:
            if MarkdownRules.is_list_item(line):
                level = MarkdownRules.get_list_level(line)
                content = re.sub(r'^\s*[*\-+]\s+', '', line)
                marker_match = re.search(r'[*\-+]', line)
                items.append({
                    'level': level,
                    'content': content,
                    'marker': marker_match.group() if marker_match else '*'
                })

        return items
