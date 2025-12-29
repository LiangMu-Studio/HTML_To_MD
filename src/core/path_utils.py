from pathlib import Path
from urllib.parse import urljoin
from typing import Optional


def resolve_url(
    url: str,
    base_url: Optional[str] = None,
    base_path: Optional[Path] = None,
    rewrite_paths: bool = False,
) -> str:
    """
    Resolve relative href/src to absolute using base_url or base_path.
    Only rewrites when rewrite_paths is True.
    """
    if not rewrite_paths:
        return url
    if base_url:
        return urljoin(base_url, url)
    if base_path:
        try:
            p = (base_path / url).resolve()
            return p.as_uri()
        except Exception:
            return url
    return url
