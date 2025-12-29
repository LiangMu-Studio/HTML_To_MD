import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core.html_to_md import html_to_markdown
from core.md_to_html import markdown_to_html


def test_html_links():
    html = '<p><a href="https://example.com">Example</a></p>'
    md = html_to_markdown(html)
    assert "[Example](https://example.com)" in md


def test_html_task_list():
    html = "<ul><li><input type='checkbox' checked> Done</li><li><input type='checkbox'> Todo</li></ul>"
    md = html_to_markdown(html)
    assert "- [x] Done" in md
    assert "- [ ] Todo" in md


def test_html_table():
    html = """
    <table>
      <tr><th>Name</th><th>Done</th></tr>
      <tr><td>Task A</td><td><input type="checkbox" checked></td></tr>
      <tr><td>Task B</td><td><input type="checkbox"></td></tr>
    </table>
    """
    md = html_to_markdown(html)
    assert "| Name | Done |" in md
    assert "| Task A | [x] |" in md
    assert "| Task B | [ ] |" in md


def test_md_task_and_table():
    md = """
    - [x] finished
    - [ ] todo

    | Col1 | Col2 |
    | --- | --- |
    | A | B |
    """
    html = markdown_to_html(md)
    assert 'type="checkbox"' in html
    assert "<table>" in html


def test_md_math():
    md = "$a^2 + b^2 = c^2$\n\n$$\nE=mc^2\n$$"
    html = markdown_to_html(md)
    assert '<span class="math">' in html
    assert '<div class="math">' in html


def test_nested_list():
    md = "- item 1\n    - sub 1\n    - [x] sub 2\n- item 2"
    html = markdown_to_html(md)
    assert html.count("<ul>") >= 2
    assert 'type="checkbox"' in html


def test_base_url_resolution():
    md = "[link](/path/page) ![img](images/a.png)"
    html = markdown_to_html(md, base_url="https://example.com", rewrite_paths=True)
    assert 'https://example.com/path/page' in html
    assert 'https://example.com/images/a.png' in html


def main() -> int:
    tests = [
        test_html_links,
        test_html_task_list,
        test_html_table,
        test_md_task_and_table,
        test_md_math,
        test_nested_list,
        test_base_url_resolution,
    ]
    for t in tests:
        t()
    print(f"OK: {len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
