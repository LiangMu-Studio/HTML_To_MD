from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import shutil
import os
import tempfile
from pathlib import Path
from typing import List, Optional
import requests
import pyperclip

try:
    from src.converter import Converter  # when imported as a package
    from src.core import manager
    from src.core.exporter import export_content, ExportError
    from src.core.feature_flags import get_feature_status
except ImportError:
    from converter import Converter
    from core import manager
    from core.exporter import export_content, ExportError
    from core.feature_flags import get_feature_status

app = FastAPI(title="HTML <-> MD Converter")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for processing
TEMP_DIR = Path(tempfile.gettempdir()) / "html_md_converter"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

class ConvertRequest(BaseModel):
    content: str
    type: str # 'html' or 'md'
    base_url: Optional[str] = None
    rewrite_paths: bool = False
    drop_unknown_tags: bool = False

class BatchRequest(BaseModel):
    path: str
    recursive: bool = False
    output_dir: Optional[str] = None
    enable_backup: bool = True
    base_url: Optional[str] = None
    rewrite_paths: bool = False
    drop_unknown_tags: bool = False

class URLRequest(BaseModel):
    url: str
    target_format: str = "md" # 'md' or 'html'
    timeout: float = 10.0
    dynamic: bool = False
    wait_ms: int = 1500
    proxy: Optional[str] = None
    main_only: bool = False

class ClipboardRequest(BaseModel):
    type: str # 'html' or 'md'

class ExportRequest(BaseModel):
    content: str
    type: str # 'html' or 'md'
    export: str # 'pdf' or 'docx'
    filename: str = "export"
    css: Optional[str] = None

@app.get("/")
async def read_root():
    return {"status": "ok", "message": "Converter API is running"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "features": get_feature_status(),
    }

@app.post("/api/convert/text")
async def convert_text(request: ConvertRequest):
    try:
        if request.type == 'html':
            result = Converter.html_to_markdown(
                request.content,
                base_url=request.base_url,
                rewrite_paths=request.rewrite_paths,
                drop_unknown_tags=request.drop_unknown_tags,
            )
            return {"result": result}
        elif request.type == 'md':
            result = Converter.markdown_to_html(
                request.content,
                base_url=request.base_url,
                rewrite_paths=request.rewrite_paths,
            )
            return {"result": result}
        else:
            raise HTTPException(status_code=400, detail="Invalid type. Use 'html' or 'md'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/convert/file")
async def convert_file(
    file: UploadFile = File(...),
    target_format: str = Body(...),
    base_url: Optional[str] = Body(default=None),
    rewrite_paths: bool = Body(default=False),
):
    try:
        content = (await file.read()).decode('utf-8')
        filename = file.filename
        stem = Path(filename).stem
        
        if target_format == 'md':
            result = Converter.html_to_markdown(content, base_url=base_url, rewrite_paths=rewrite_paths)
            output_filename = f"{stem}.md"
            media_type = "text/markdown"
        elif target_format == 'html':
            result = Converter.markdown_to_html(content, base_url=base_url, rewrite_paths=rewrite_paths)
            output_filename = f"{stem}.html"
            media_type = "text/html"
        else:
            raise HTTPException(status_code=400, detail="Invalid target format")
            
        return JSONResponse({
            "filename": output_filename,
            "content": result
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batch")
async def batch_convert(request: BatchRequest):
    directory = Path(request.path)
    if not directory.exists() or not directory.is_dir():
        raise HTTPException(status_code=400, detail="Directory not found")
    
    converted_count = 0
    errors = []
    
    try:
        extensions = ['.html', '.md']
        files = []
        if request.recursive:
            files = [p for p in directory.rglob("*") if p.is_file()]
        else:
            files = [p for p in directory.glob("*") if p.is_file()]

        selected_files = [str(p) for p in files if p.suffix.lower() in extensions]
        results = manager.batch_convert(
            selected_files,
            target_format="auto",
            enable_backup=request.enable_backup,
            output_dir=request.output_dir,
            base_dir=directory,
            base_url=request.base_url,
            rewrite_paths=request.rewrite_paths,
            drop_unknown_tags=request.drop_unknown_tags,
        )

        for r in results:
            if r.success:
                converted_count += 1
            else:
                errors.append(f"{Path(r.file_path).name}: {r.message}")

        return {
            "converted": converted_count,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/convert/url")
async def convert_url(request: URLRequest):
    try:
        content = ""
        if request.dynamic:
            try:
                from playwright.sync_api import sync_playwright  # Optional dependency
            except Exception as e:
                raise HTTPException(
                    status_code=501,
                    detail="Dynamic rendering requires playwright. Install with `pip install playwright` and run `playwright install chromium`."
                ) from e

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(request.url, wait_until="networkidle")
                page.wait_for_timeout(request.wait_ms)
                content = page.content()
                browser.close()
        else:
            proxies = {"http": request.proxy, "https": request.proxy} if request.proxy else None
            resp = requests.get(request.url, timeout=request.timeout, proxies=proxies)
            resp.raise_for_status()
            content = resp.text

        if request.main_only:
            try:
                from readability import Document  # type: ignore
                doc = Document(content)
                content = doc.summary(html_partial=True)
            except Exception:
                # fallback to full content
                pass

        if request.target_format == "md":
            result = Converter.html_to_markdown(content)
            media_type = "text/markdown"
            filename = "converted.md"
        elif request.target_format == "html":
            result = content
            media_type = "text/html"
            filename = "converted.html"
        else:
            raise HTTPException(status_code=400, detail="Invalid target_format, use 'md' or 'html'")

        return JSONResponse({"filename": filename, "content": result}, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/convert/clipboard")
async def convert_clipboard(request: ClipboardRequest):
    try:
        try:
            from src.core.clipboard_utils import read_clipboard_text
        except ImportError:
            from core.clipboard_utils import read_clipboard_text
        prefer_html = request.type == 'html'
        text = read_clipboard_text(prefer_html=prefer_html)
        if not text:
            raise HTTPException(status_code=400, detail="Clipboard is empty")

        if request.type == 'html':
            result = Converter.html_to_markdown(text)
            media_type = "text/markdown"
        elif request.type == 'md':
            result = Converter.markdown_to_html(text)
            media_type = "text/html"
        else:
            raise HTTPException(status_code=400, detail="Invalid type. Use 'html' or 'md'.")

        return JSONResponse({"result": result}, media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def export_content_api(request: ExportRequest):
    try:
        if request.type not in ("html", "md"):
            raise HTTPException(status_code=400, detail="Invalid type. Use 'html' or 'md'.")
        if request.export not in ("pdf", "docx"):
            raise HTTPException(status_code=400, detail="Invalid export. Use 'pdf' or 'docx'.")

        output_path = TEMP_DIR / f"{request.filename}.{request.export}"
        export_path = export_content(
            request.content,
            request.type,
            request.export,
            output_path,
            css_text=request.css,
        )
        return FileResponse(
            export_path,
            filename=export_path.name,
            media_type="application/octet-stream",
        )
    except ExportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
