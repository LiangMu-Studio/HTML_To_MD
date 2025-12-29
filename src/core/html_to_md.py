import re
from html.parser import HTMLParser
from html import unescape
from typing import List, Optional
from pathlib import Path
from urllib.parse import urljoin
from .path_utils import resolve_url
from .tag_policy import is_allowed, DEFAULT_ALLOWED_INLINE, DEFAULT_ALLOWED_BLOCK, load_allowlist

class HTMLToMarkdownParser(HTMLParser):
    def __init__(
        self,
        base_url: Optional[str] = None,
        base_path: Optional[Path] = None,
        rewrite_paths: bool = False,
        drop_unknown_tags: bool = False,
        allow_inline=DEFAULT_ALLOWED_INLINE,
        allow_block=DEFAULT_ALLOWED_BLOCK,
    ):
        super().__init__()
        self.text: List[str] = []
        self.list_stack: List[str] = []
        self.link_stack: List[str] = []
        self.in_code = False
        self.in_pre = False
        self.in_li = False
        self.after_checkbox = False
        # Table state
        self.in_table = False
        self.current_row: Optional[List[tuple[str, Optional[str]]]] = None
        self.current_row_is_header = False
        self.current_cell: Optional[List[str]] = None
        self.current_cell_align: Optional[str] = None
        self.table_rows: List[dict] = []
        self.base_url = base_url
        self.base_path = base_path
        self.rewrite_paths = rewrite_paths
        self.drop_unknown_tags = drop_unknown_tags
        self.allow_inline = allow_inline
        self.allow_block = allow_block

    def handle_starttag(self, tag, attrs):
        if self.drop_unknown_tags and not is_allowed(tag, self.allow_inline, self.allow_block):
            return
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            self.text.append('\n' + '#' * level + ' ')
        elif tag == 'p':
            pass  # 不在段落开始加换行
        elif tag == 'br':
            self.text.append('\n')
        elif tag in ['strong', 'b']:
            self.text.append('**')
        elif tag in ['em', 'i']:
            self.text.append('*')
        elif tag == 'code':
            self.text.append('`')
            self.in_code = True
        elif tag == 'pre':
            self.in_pre = True
            self.text.append('\n```\n')
        elif tag in ['ul', 'ol']:
            self.list_stack.append(tag)
        elif tag == 'li':
            indent = '  ' * (len(self.list_stack) - 1)
            # Check if parent is ol to use number
            if self.list_stack and self.list_stack[-1] == 'ol':
                self.text.append(f'\n{indent}1. ')
            else:
                self.text.append(f'\n{indent}- ')
            self.in_li = True
        elif tag == 'a':
            self.text.append('[')
            href = ''
            for attr, value in attrs:
                if attr == 'href':
                    href_raw = value or ''
                    href = resolve_url(href_raw, self.base_url, self.base_path, self.rewrite_paths)
                    break
            self.link_stack.append(href)
        elif tag == 'blockquote':
            self.text.append('\n> ')
        elif tag == 'div':
            self.text.append('\n')
        elif tag == 'input':
            input_type = None
            is_checked = False
            for attr, value in attrs:
                if attr.lower() == 'type':
                    input_type = value.lower()
                if attr.lower() == 'checked':
                    is_checked = True
            if input_type == 'checkbox':
                mark = '[x]' if is_checked else '[ ]'
                if self.in_table and self.current_cell is not None:
                    self.current_cell.append(mark)
                else:
                    self.text.append(mark + ' ')
                self.after_checkbox = True
        elif tag == 'img':
            src = ''
            alt = ''
            for attr, value in attrs:
                if attr == 'src':
                    src = value or ''
                if attr == 'alt':
                    alt = value or ''
            src_resolved = resolve_url(src, self.base_url, self.base_path, self.rewrite_paths)
            self.text.append(f'![{alt}]({src_resolved})')
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
        elif tag == 'tr':
            if self.in_table:
                self.current_row = []
                self.current_row_is_header = False
        elif tag in ['th', 'td']:
            if self.in_table:
                self.current_cell = []
                self.current_cell_align = None
                for attr, value in attrs:
                    if attr.lower() == "align" and value:
                        self.current_cell_align = value.lower()
                    if attr.lower() == "style" and value and "text-align" in value:
                        style = value.lower()
                        if "text-align" in style:
                            if "center" in style:
                                self.current_cell_align = "center"
                            elif "right" in style:
                                self.current_cell_align = "right"
                            elif "left" in style:
                                self.current_cell_align = "left"
                if tag == 'th':
                    self.current_row_is_header = True

    def handle_endtag(self, tag):
        if self.drop_unknown_tags and not is_allowed(tag, self.allow_inline, self.allow_block):
            return
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            self.text.append('\n')
        elif tag in ['strong', 'b']:
            self.text.append('**')
        elif tag in ['em', 'i']:
            self.text.append('*')
        elif tag == 'code':
            self.text.append('`')
            self.in_code = False
        elif tag == 'pre':
            self.text.append('\n```\n')
            self.in_pre = False
        elif tag == 'a':
            href = ''
            if self.link_stack:
                href = self.link_stack.pop()
            suffix = f']({href})' if href else ']'
            self.text.append(suffix)
        elif tag in ['ul', 'ol']:
            if self.list_stack:
                self.list_stack.pop()
            self.text.append('\n')
        elif tag == 'li':
            self.in_li = False
        elif tag in ['th', 'td']:
            if self.in_table and self.current_cell is not None:
                cell_text = ''.join(self.current_cell).strip()
                self.current_row.append((cell_text, self.current_cell_align))
                self.current_cell = None
                self.current_cell_align = None
        elif tag == 'tr':
            if self.in_table and self.current_row is not None:
                self.table_rows.append(
                    {
                        "header": self.current_row_is_header,
                        "cells": self.current_row,
                    }
                )
                self.current_row = None
        elif tag == 'table':
            if self.in_table:
                self._flush_table()
                self.in_table = False
                self.table_rows = []

    def handle_data(self, data):
        if self.in_table and self.current_cell is not None:
            if self.after_checkbox:
                data = data.lstrip()
                self.after_checkbox = False
            self.current_cell.append(data)
            return

        if data.strip():
            if self.after_checkbox:
                data = data.lstrip()
                self.after_checkbox = False
            self.text.append(data)
        elif self.in_code or self.in_pre: 
            # Preserve whitespace in code blocks
            self.text.append(data)

    def get_markdown(self) -> str:
        md = ''.join(self.text)
        # 多个换行合并为��个
        md = re.sub(r'\n{3,}', '\n\n', md)
        md = re.sub(r'\[\]\(url\)', '', md)
        md = re.sub(r'\[\]', '', md)
        md = re.sub(r'^([^\n#]+)\n(# \1)', r'\2', md)
        return md.strip()

    def _flush_table(self) -> None:
        if not self.table_rows:
            return

        # Determine header/body
        header_cells: List[tuple[str, Optional[str]]] = []
        body_rows: List[List[tuple[str, Optional[str]]]] = []

        for idx, row in enumerate(self.table_rows):
            if not header_cells and row.get("header"):
                header_cells = row["cells"]
                continue
            if not header_cells and idx == 0:
                header_cells = row["cells"]
                continue
            body_rows.append(row["cells"])

        if not header_cells:
            return

        col_count = max(len(header_cells), *(len(r) for r in body_rows) if body_rows else [0])

        def normalize_row(
            cells: List[tuple[str, Optional[str]]]
        ) -> List[tuple[str, Optional[str]]]:
            padded = list(cells)
            while len(padded) < col_count:
                padded.append(('', None))
            return padded

        header_cells = normalize_row(header_cells)
        body_rows = [normalize_row(r) for r in body_rows]

        lines = []
        lines.append('| ' + ' | '.join(cell.strip() for cell, _ in header_cells) + ' |')

        def divider_for_align(align: Optional[str]) -> str:
            if align == "left":
                return ":---"
            if align == "right":
                return "---:"
            if align == "center":
                return ":---:"
            return "---"

        lines.append('| ' + ' | '.join(divider_for_align(align) for _, align in header_cells) + ' |')
        for row in body_rows:
            lines.append('| ' + ' | '.join(cell.strip() for cell, _ in row) + ' |')

        table_md = '\n'.join(lines)
        self.text.append('\n' + table_md + '\n')

def html_to_markdown(
    html_content: str,
    base_url: Optional[str] = None,
    base_path: Optional[Path] = None,
    rewrite_paths: bool = False,
    drop_unknown_tags: bool = False,
    allow_inline=DEFAULT_ALLOWED_INLINE,
    allow_block=DEFAULT_ALLOWED_BLOCK,
    allowlist_file: Optional[Path] = None,
) -> str:
    """Convert HTML string to Markdown string."""
    if allowlist_file:
        try:
            allow_inline, allow_block = load_allowlist(allowlist_file)
        except Exception:
            pass
    # Pre-processing
    html = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    html = re.sub(r'<div[^>]*>', '', html)  # 开始标签移除
    html = re.sub(r'(</div>)+', '\n', html)  # 连续结束标签只产生一个换行
    html = re.sub(r'\s*style="[^"]*"', '', html)
    html = re.sub(r'<span[^>]*>', '', html)
    html = re.sub(r'</span>', '', html)
    html = unescape(html)

    parser = HTMLToMarkdownParser(
        base_url=base_url,
        base_path=base_path,
        rewrite_paths=rewrite_paths,
        drop_unknown_tags=drop_unknown_tags,
        allow_inline=allow_inline,
        allow_block=allow_block,
    )
    try:
        parser.feed(html)
        return parser.get_markdown()
    except Exception as e:
        # Fallback or log error
        print(f"Error parsing HTML: {e}")
        return html_content
