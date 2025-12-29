"""URL 抓取模块 - 支持提取网页正文"""
import re
import base64
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests


def _fetch_with_browser(url: str, timeout: float) -> Tuple[str, str]:
    """用 DrissionPage 打开页面并自动获取内容（使用系统默认浏览器）"""
    from DrissionPage import ChromiumPage, ChromiumOptions
    import winreg

    # 从注册表获取默认浏览器路径
    browser_path = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        # 从 ProgId 获取实际的浏览器路径
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
            cmd = winreg.QueryValueEx(key, "")[0]
            # 提取 exe 路径（去掉引号和参数）
            if cmd.startswith('"'):
                browser_path = cmd.split('"')[1]
            else:
                browser_path = cmd.split()[0]
    except Exception:
        pass

    co = ChromiumOptions()
    if browser_path:
        co.set_browser_path(browser_path)

    page = ChromiumPage(co)
    page.set.load_mode.eager()
    page.get(url)
    page.wait.doc_loaded(timeout=timeout)

    content = page.html
    title = page.title
    page.quit()
    return content, title


def fetch_url(
    url: str,
    timeout: float = 15.0,
    proxy: Optional[str] = None,
    main_only: bool = False,
    download_images: bool = True,
    cookie: Optional[str] = None,
    use_browser: bool = False
) -> Tuple[str, str]:
    """
    抓取 URL 内容
    返回: (html_content, title)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    if cookie:
        headers['Cookie'] = cookie
    proxies = {"http": proxy, "https": proxy} if proxy else None

    if use_browser:
        content, title = _fetch_with_browser(url, timeout)
    else:
        resp = requests.get(url, timeout=timeout, proxies=proxies, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        content = resp.text
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else url

    if main_only:
        # 知乎专栏特殊处理
        if 'zhihu.com' in url:
            zhihu_content = _extract_zhihu_content(content)
            if zhihu_content:
                content = zhihu_content
            else:
                content = _simple_extract(content)
        else:
            # 先尝试精准提取
            extracted = _simple_extract(content)
            if len(extracted) < len(content) * 0.8:
                content = extracted
            else:
                try:
                    from readability import Document
                    doc = Document(content)
                    content = doc.summary(html_partial=True)
                    title = doc.title() or title
                except Exception:
                    content = extracted
        # 过滤噪音图片
        content = _filter_noise_images(content)

    # 下载图片并转为base64内嵌
    if download_images:
        content = _embed_images(content, url, headers, proxies, timeout)

    return content, title


def _embed_images(html: str, base_url: str, headers: dict, proxies: dict, timeout: float) -> str:
    """下载图片并转为base64内嵌"""
    def replace_img(match):
        img_url = match.group(2)
        if img_url.startswith('data:'):
            return match.group(0)
        full_url = urljoin(base_url, img_url)
        try:
            img_headers = {**headers, 'Referer': base_url}
            resp = requests.get(full_url, timeout=timeout, proxies=proxies, headers=img_headers)
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', 'image/jpeg')
                if 'image' in content_type:
                    b64 = base64.b64encode(resp.content).decode('utf-8')
                    return f'{match.group(1)}data:{content_type};base64,{b64}{match.group(3)}'
        except Exception:
            pass
        return match.group(0)

    # 匹配 src="..." 或 src='...'
    pattern = r'(<img[^>]*\ssrc=["\'])([^"\']+)(["\'][^>]*>)'
    return re.sub(pattern, replace_img, html, flags=re.IGNORECASE)


def _extract_zhihu_content(html: str) -> str:
    """从知乎页面提取正文（从内嵌JSON中）"""
    import json
    # 知乎把文章数据放在 script 标签的 JSON 中
    match = re.search(r'<script[^>]*id="js-initialData"[^>]*>([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            # 尝试从 initialState 中提取文章内容
            entities = data.get('initialState', {}).get('entities', {})
            articles = entities.get('articles', {})
            for article in articles.values():
                content = article.get('content', '')
                if content:
                    return content
        except Exception:
            pass
    return ''


def _simple_extract(html: str) -> str:
    """简单提取正文（当 readability 不可用时）"""
    # 移除 script/style/注释
    html = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<!--[\s\S]*?-->', '', html)
    # 移除导航/页眉/页脚/侧边栏/广告/noscript
    for tag in ['nav', 'header', 'footer', 'aside', 'iframe', 'noscript']:
        html = re.sub(rf'<{tag}[^>]*>[\s\S]*?</{tag}>', '', html, flags=re.IGNORECASE)
    # 移除常见无关class/id的div
    noise_kw = r'nav|menu|sidebar|footer|header|comment|recommend|related|ad|share|social'
    noise_kw += r'|logo|copyright|qrcode|二维码|版权|分享|评论|推荐|相关'
    pattern = rf'<div[^>]*(?:class|id)=["\'][^"\']*(?:{noise_kw})[^"\']*["\'][^>]*>[\s\S]*?</div>'
    html = re.sub(pattern, '', html, flags=re.IGNORECASE)

    # 尝试提取 article 或 main 或特定class
    content_classes = r'post-content|article-content|entry-content|content-body'
    content_classes += r'|post_body|post_text|article_body|news_body|main-content'
    for pattern in [
        r'<article[^>]*>([\s\S]*?)</article>',
        r'<main[^>]*>([\s\S]*?)</main>',
        rf'<div[^>]*class=["\'][^"\']*(?:{content_classes})[^"\']*["\'][^>]*>([\s\S]*?)</div>',
    ]:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(0)

    return html


def _filter_noise_images(html: str) -> str:
    """过滤噪音图片（logo、二维码、小图标等）"""
    def should_remove(match):
        img_tag = match.group(0)
        # 检查是否是logo/icon/qrcode等
        if re.search(r'(?:logo|icon|qrcode|二维码|badge|avatar)', img_tag, re.IGNORECASE):
            return ''
        # 检查尺寸，过滤小图片（宽或高<100）
        size_match = re.search(r'(?:width|height)[=:]\s*["\']?(\d+)', img_tag, re.IGNORECASE)
        if size_match and int(size_match.group(1)) < 100:
            return ''
        return img_tag

    return re.sub(r'<img[^>]*>', should_remove, html, flags=re.IGNORECASE)
