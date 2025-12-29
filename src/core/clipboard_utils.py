from typing import Optional


def read_clipboard_text(prefer_html: bool = False) -> str:
    """
    Attempt to read text from clipboard.
    If prefer_html=True on Windows and pywin32 is available, try CF_HTML first.
    """
    if prefer_html:
        try:
            import win32clipboard  # type: ignore
            import win32con  # type: ignore

            html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(html_format):
                data = win32clipboard.GetClipboardData(html_format)
                win32clipboard.CloseClipboard()
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="ignore")
                # Extract HTML fragment if markers exist
                start_marker = "StartFragment:"
                end_marker = "EndFragment:"
                start = data.find(start_marker)
                end = data.find(end_marker)
                if start != -1 and end != -1:
                    try:
                        start_idx = int(data[start + len(start_marker):].split("\r\n", 1)[0])
                        end_idx = int(data[end + len(end_marker):].split("\r\n", 1)[0])
                        return data[start_idx:end_idx]
                    except Exception:
                        pass
                return data
            win32clipboard.CloseClipboard()
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

    # Fallback to plain text via pyperclip
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        return ""
