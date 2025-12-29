from core.html_to_md import html_to_markdown
from core.md_to_html import markdown_to_html


class Converter:
    @staticmethod
    def html_to_markdown(html: str, **kwargs) -> str:
        return html_to_markdown(html, **kwargs)

    @staticmethod
    def markdown_to_html(markdown: str, **kwargs) -> str:
        return markdown_to_html(markdown, **kwargs)
