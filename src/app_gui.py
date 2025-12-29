import argparse
import sys
from pathlib import Path
from typing import Optional

from converter import Converter

try:
    from core import manager
except ImportError:
    from src.core import manager


def convert_paths(
    paths,
    target_format: str,
    recursive: bool,
    output_dir: Optional[str],
    enable_backup: bool,
    export: Optional[str] = None,
    export_css: Optional[str] = None,
    base_url: Optional[str] = None,
    base_dir: Optional[str] = None,
    rewrite_paths: bool = False,
    main_only: bool = False,
    timeout: float = 10.0,
    show_optional: bool = False,
    max_workers: int = 1,
    drop_unknown_tags: bool = False,
    allowlist_file: Optional[str] = None,
):
    output_dir_path = Path(output_dir) if output_dir else None
    base_dir_path = Path(base_dir) if base_dir else None
    total_results = []

    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files = manager.get_files_in_directory(
                str(path),
                extensions=[".html", ".md"],
                recursive=recursive,
            )
            if not files:
                print(f"[skip] No supported files in folder: {path}")
                continue

            results = manager.batch_convert(
                files,
                target_format=target_format,
                enable_backup=enable_backup,
                output_dir=output_dir_path,
                base_dir=path,
                base_url=base_url,
                rewrite_paths=rewrite_paths,
                drop_unknown_tags=drop_unknown_tags,
                max_workers=max_workers,
            )
            total_results.extend(results)
        elif path.is_file():
            res = manager.convert_file(
                str(path),
                target_format=target_format,
                enable_backup=enable_backup,
                output_dir=output_dir_path,
                base_dir=base_dir_path or path.parent,
                base_url=base_url,
                rewrite_paths=rewrite_paths,
                drop_unknown_tags=drop_unknown_tags,
                allowlist_file=allowlist_file,
            )
            total_results.append(res)
        elif str(path).startswith(("http://", "https://")):
            from core.fetch_url import fetch_url
            try:
                html = fetch_url(str(path), timeout=timeout, main_only=main_only)
                base_name = Path(path).name or "page"
                if target_format in ("auto", "md"):
                    result_content = Converter.html_to_markdown(html, base_url=path, rewrite_paths=rewrite_paths)
                    suffix = ".md"
                else:
                    result_content = html
                    suffix = ".html"
                output_base = output_dir_path or Path(".")
                output_file = (output_base / base_name).with_suffix(suffix)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(result_content, encoding="utf-8")
                total_results.append(manager.conversion_result(True, f"Saved to {output_file}", str(path), output_path=str(output_file)))
            except Exception as e:
                total_results.append(manager.conversion_result(False, str(e), str(path)))
        else:
            print(f"[warn] Not found: {path}")

    if export and export.lower() != "none":
        from core.exporter import export_content, ExportError
        for r in total_results:
            if not r.success or not r.output_path:
                continue
            out_path = Path(r.output_path)
            try:
                text = out_path.read_text(encoding="utf-8")
                content_type = "html" if out_path.suffix.lower() == ".html" else "md"
                css_text = None
                if export_css:
                    try:
                        css_text = Path(export_css).read_text(encoding="utf-8")
                    except Exception:
                        css_text = None
                export_path = export_content(text, content_type, export.lower(), out_path, css_text=css_text)
                r.message += f" (exported: {export_path})"
            except ExportError as e:
                r.message += f" (export failed: {e})"
            except Exception as e:
                r.message += f" (export failed: {e})"

    return total_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HTML ↔ Markdown Converter CLI",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="File(s) or folder(s) to convert",
    )
    parser.add_argument(
        "--target-format",
        choices=["auto", "md", "html"],
        default="auto",
        help="Convert to markdown (md), html, or auto-detect",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories when a folder is provided",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Optional output directory (keeps relative structure when folder input)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Disable automatic BACKUP/<date>/ copy",
    )
    parser.add_argument(
        "--export",
        choices=["none", "pdf", "docx"],
        default="none",
        help="Optional export to PDF or DOCX (requires optional dependencies)",
    )
    parser.add_argument(
        "--export-css",
        type=str,
        help="Optional CSS file applied when exporting PDF (requires weasyprint)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="Optional base URL to rewrite relative links/images",
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        help="Optional base directory to resolve relative links/images",
    )
    parser.add_argument(
        "--rewrite-paths",
        action="store_true",
        help="Rewrite relative links/images using base-url or base-dir",
    )
    parser.add_argument(
        "--drop-unknown-tags",
        action="store_true",
        help="HTML->Markdown: drop tags not in allow-list (keeps text)",
    )
    parser.add_argument(
        "--allowlist-file",
        type=str,
        help="JSON file with {'inline': [...], 'block': [...]} to override allow-list",
    )
    parser.add_argument(
        "--main-only",
        action="store_true",
        help="When converting URLs, extract main content (readability) if possible",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout for URL fetching (seconds)",
    )
    parser.add_argument(
        "--show-optional",
        action="store_true",
        help="Show optional dependency availability and exit",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Max worker threads for batch conversion",
    )

    args = parser.parse_args()
    if args.show_optional:
        from core.feature_flags import get_feature_status
        print(get_feature_status())
        return 0
    results = convert_paths(
        paths=args.paths,
        target_format=args.target_format,
        recursive=args.recursive,
        output_dir=args.output_dir,
        enable_backup=not args.no_backup,
        export=args.export,
        export_css=args.export_css,
        base_url=args.base_url,
        base_dir=args.base_dir,
        rewrite_paths=args.rewrite_paths,
        main_only=args.main_only,
        timeout=args.timeout,
        show_optional=args.show_optional,
        max_workers=args.max_workers,
        drop_unknown_tags=args.drop_unknown_tags,
        allowlist_file=args.allowlist_file,
    )

    success = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    for r in success:
        print(f"[ok] {r.file_path} -> {r.message}")
    for r in failed:
        print(f"[fail] {r.file_path}: {r.message}")

    print(f"\nSummary: {len(success)} success, {len(failed)} failed")
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
