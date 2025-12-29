import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Callable, Optional
from .html_to_md import html_to_markdown
from .md_to_html import markdown_to_html

__all__ = [
    "html_to_markdown",
    "markdown_to_html",
    "convert_file",
    "batch_convert",
    "conversion_result",
]


class conversion_result:
    def __init__(
        self,
        success: bool,
        message: str,
        file_path: str,
        output_path: Optional[str] = None,
    ):
        self.success = success
        self.message = message
        self.file_path = file_path
        self.output_path = output_path


def convert_file(
    file_path: str,
    target_format: str = "auto",
    output_dir: Optional[Path] = None,
    base_dir: Optional[Path] = None,
    base_url: Optional[str] = None,
    rewrite_paths: bool = False,
    drop_unknown_tags: bool = False,
    allowlist_file: Optional[Path] = None,
) -> conversion_result:
    """
    Convert a single file to target format.
    target_format: 'md', 'html', or 'auto' (detects from extension)
    """
    path = Path(file_path)
    if not path.exists():
        return conversion_result(False, "File not found", file_path)

    try:
        content = path.read_text(encoding="utf-8")
        result_content = ""
        output_path: Path

        # Auto-detect target format
        final_target = target_format
        if final_target == "auto":
            suffix = path.suffix.lower()
            if suffix == ".html":
                final_target = "md"
            elif suffix == ".md":
                final_target = "html"
            else:
                return conversion_result(
                    False, f"Cannot auto-detect target for: {suffix}", file_path
                )

        if final_target == "md":
            base_path = base_dir or path.parent
            result_content = html_to_markdown(
                content,
                base_url=base_url,
                base_path=base_path,
                rewrite_paths=rewrite_paths,
                drop_unknown_tags=drop_unknown_tags,
                allowlist_file=allowlist_file,
            )
            output_path = path.with_suffix(".md")
        elif final_target == "html":
            base_path = base_dir or path.parent
            result_content = markdown_to_html(
                content,
                base_url=base_url,
                base_path=base_path,
                rewrite_paths=rewrite_paths,
            )
            output_path = path.with_suffix(".html")
        else:
            return conversion_result(
                False, f"Unsupported target format: {target_format}", file_path
            )

        if output_dir:
            output_dir = Path(output_dir)
            if base_dir:
                try:
                    rel = path.resolve().relative_to(base_dir.resolve())
                except Exception:
                    rel = Path(path.name)
            else:
                rel = Path(path.name)
            output_path = (output_dir / rel).with_suffix(output_path.suffix)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(result_content, encoding="utf-8")
        return conversion_result(True, f"Saved to {output_path}", file_path, output_path=str(output_path))

    except Exception as e:
        return conversion_result(False, str(e), file_path)


def batch_convert(
    files: List[str],
    target_format: str = "auto",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    output_dir: Optional[Path] = None,
    base_dir: Optional[Path] = None,
    cancel_callback: Optional[Callable[[], bool]] = None,
    base_url: Optional[str] = None,
    rewrite_paths: bool = False,
    drop_unknown_tags: bool = False,
    max_workers: int = 1,
    pause_callback: Optional[Callable[[], bool]] = None,
    allowlist_file: Optional[Path] = None,
) -> List[conversion_result]:
    """
    Convert a list of files.
    progress_callback: (current, total, current_filename) -> None
    """
    results = []
    total = len(files)

    def worker(idx_path: tuple[int, str]) -> conversion_result:
        i, file_path = idx_path
        if cancel_callback and cancel_callback():
            return conversion_result(False, "Cancelled", "<cancelled>", None)
        if progress_callback:
            progress_callback(i + 1, total, os.path.basename(file_path))
        return convert_file(
            file_path,
            target_format=target_format,
            output_dir=output_dir,
            base_dir=base_dir,
            base_url=base_url,
            rewrite_paths=rewrite_paths,
            drop_unknown_tags=drop_unknown_tags,
            allowlist_file=allowlist_file,
        )

    if max_workers and max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for res in ex.map(worker, list(enumerate(files))):
                if pause_callback:
                    while pause_callback():
                        time.sleep(0.1)
                results.append(res)
                if cancel_callback and cancel_callback():
                    break
    else:
        for i, file_path in enumerate(files):
            if pause_callback:
                while pause_callback():
                    time.sleep(0.1)
            res = worker((i, file_path))
            results.append(res)
            if cancel_callback and cancel_callback():
                break

    return results


def get_files_in_directory(
    directory: str, extensions: List[str], recursive: bool = False
) -> List[str]:
    """Get all files with matching extensions in directory."""
    path = Path(directory)
    files = []

    pattern = "**/*" if recursive else "*"

    for item in path.glob(pattern):
        if item.is_file() and item.suffix.lower() in extensions:
            files.append(str(item))

    return files
