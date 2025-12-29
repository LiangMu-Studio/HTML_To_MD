import json
from pathlib import Path
from typing import Set, Tuple, Iterable

# Simple tag policy to drop or keep unknown tags if needed.
# Currently unused in parser but can be wired to HTMLToMarkdown if desired.

DEFAULT_ALLOWED_INLINE: Set[str] = {
    "a", "strong", "b", "em", "i", "code", "span", "img", "sup", "sub", "del"
}

DEFAULT_ALLOWED_BLOCK: Set[str] = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "table", "thead", "tbody", "tr", "th", "td", "hr"
}

def load_allowlist(path: Path) -> Tuple[Set[str], Set[str]]:
    """Load allowlist from JSON file: {"inline": [...], "block": [...]}"""
    data = json.loads(path.read_text(encoding="utf-8"))
    inline = set(data.get("inline", []))
    block = set(data.get("block", []))
    return inline, block


def is_allowed(tag: str, allow_inline=DEFAULT_ALLOWED_INLINE, allow_block=DEFAULT_ALLOWED_BLOCK) -> bool:
    t = tag.lower()
    return t in allow_inline or t in allow_block
