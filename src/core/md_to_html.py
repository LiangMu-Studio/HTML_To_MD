"""
Muya 风格 Markdown 渲染器 - 纯 Python 实现
基于 MarkText/Muya 的正则规则，修复了中文支持
"""
import re
from typing import Optional
from pathlib import Path
from .path_utils import resolve_url


class MuyaRenderer:
    """基于 Muya 正则规则的 Markdown 渲染器"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        base_path: Optional[Path] = None,
        rewrite_paths: bool = False,
    ):
        self.base_url = base_url
        self.base_path = base_path
        self.rewrite_paths = rewrite_paths

    def render(self, markdown: str) -> str:
        html = markdown

        # 代码块（先处理，避免内部被转义）
        html = re.sub(
            r'```(\w*)\n([\s\S]*?)```',
            lambda m: f'<pre><code class="language-{m.group(1) or "text"}">{self._escape(m.group(2))}</code></pre>',
            html
        )

        # 行内代码
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # 标题
        html = re.sub(
            r'^(#{1,6})\s+(.+)$',
            lambda m: f'<h{len(m.group(1))}>{self._render_inline(m.group(2))}</h{len(m.group(1))}>',
            html,
            flags=re.MULTILINE
        )

        # 水平线
        html = re.sub(r'^(\*{3,}|-{3,}|_{3,})$', '<hr/>', html, flags=re.MULTILINE)

        # 引用块
        html = re.sub(r'^>\s?(.*)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        html = re.sub(r'</blockquote>\n<blockquote>', '\n', html)

        # 图片（带路径重写）
        html = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            lambda m: f'<img src="{self._resolve(m.group(2))}" alt="{m.group(1)}"/>',
            html
        )

        # 链接（带路径重写）
        html = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            lambda m: f'<a href="{self._resolve(m.group(2))}">{m.group(1)}</a>',
            html
        )

        # 加粗（修复中文支持）
        html = re.sub(r'(\*\*|__)(?=\S)([\s\S]*?\S)\1', r'<strong>\2</strong>', html)

        # 斜体
        html = re.sub(r'(\*|_)(?=\S)([\s\S]*?\S)\1(?!\1)', r'<em>\2</em>', html)

        # 删除线
        html = re.sub(r'~~(?=\S)([\s\S]*?\S)~~', r'<del>\1</del>', html)

        # 段落
        blocks = html.split('\n\n')
        result = []
        for block in blocks:
            if re.match(r'^<(h[1-6]|pre|blockquote|hr|ul|ol|li)', block):
                result.append(block)
            elif block.strip():
                result.append(f'<p>{block.strip()}</p>')
        html = '\n'.join(result)

        return html

    def _render_inline(self, text: str) -> str:
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        text = re.sub(r'(\*\*|__)(?=\S)([\s\S]*?\S)\1', r'<strong>\2</strong>', text)
        text = re.sub(r'(\*|_)(?=\S)([\s\S]*?\S)\1(?!\1)', r'<em>\2</em>', text)
        text = re.sub(r'~~(?=\S)([\s\S]*?\S)~~', r'<del>\1</del>', text)
        text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            lambda m: f'<a href="{self._resolve(m.group(2))}">{m.group(1)}</a>',
            text
        )
        return text

    def _resolve(self, url: str) -> str:
        return resolve_url(url, self.base_url, self.base_path, self.rewrite_paths)

    def _escape(self, text: str) -> str:
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def markdown_to_html(
    markdown_content: str,
    base_url: Optional[str] = None,
    base_path: Optional[Path] = None,
    rewrite_paths: bool = False,
) -> str:
    """Convert Markdown string to HTML string."""
    renderer = MuyaRenderer(base_url=base_url, base_path=base_path, rewrite_paths=rewrite_paths)
    try:
        return renderer.render(markdown_content)
    except Exception as e:
        import html
        print(f"Error parsing Markdown: {e}")
        return f'<p>{html.escape(markdown_content)}</p>'
