def _check(module_name: str, attr: str = None) -> bool:
    try:
        mod = __import__(module_name)
        if attr:
            getattr(mod, attr)
        return True
    except Exception:
        return False


OPTIONAL_FEATURES = {
    "pyqtwebengine": _check("PyQt5.QtWebEngineWidgets"),
    "weasyprint": _check("weasyprint"),
    "python_docx": _check("docx"),
    "playwright": _check("playwright"),
    "pywin32": _check("win32clipboard"),
    "readability": _check("readability"),
}


def get_feature_status():
    return OPTIONAL_FEATURES.copy()
