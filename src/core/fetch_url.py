"""URL 抓取模块 - 支持提取网页正文"""
import re
import base64
import random
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests

# 记录浏览器是否已经以调试模式重启过
_browser_restarted = False

# 简化版笔画数据：相对坐标点
STROKES = {
    "横": [(0, 0), (0.3, 0.02), (0.6, -0.01), (1, 0)],
    "竖": [(0, 0), (0.02, 0.3), (-0.01, 0.6), (0, 1)],
    "撇": [(0, 0), (-0.2, 0.3), (-0.4, 0.6), (-0.5, 1)],
    "捺": [(0, 0), (0.2, 0.3), (0.4, 0.6), (0.5, 1)],
    "点": [(0, 0), (0.1, 0.2), (0.15, 0.4)],
}

DEBUG_STROKE = False  # 设为 True 可在页面上看到笔画轨迹


def _simulate_stroke(page):
    """在页面上模拟一两笔鼠标移动"""
    import time
    stroke_name = random.choice(list(STROKES.keys()))
    points = STROKES[stroke_name]

    start_x = random.randint(200, 800)
    start_y = random.randint(200, 500)
    scale = random.randint(30, 80)

    js_points = []
    for px, py in points:
        x = start_x + px * scale + random.uniform(-2, 2)
        y = start_y + py * scale + random.uniform(-2, 2)
        js_points.append(f"[{x:.1f}, {y:.1f}]")

    debug_js = ""
    if DEBUG_STROKE:
        debug_js = f'''
            const canvas = document.createElement('canvas');
            canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:99999';
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            document.body.appendChild(canvas);
            const ctx = canvas.getContext('2d');
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(points[0][0], points[0][1]);
            points.forEach(p => ctx.lineTo(p[0], p[1]));
            ctx.stroke();
            ctx.fillStyle = 'red';
            ctx.font = '16px sans-serif';
            ctx.fillText('笔画: {stroke_name}', points[0][0], points[0][1] - 10);
            setTimeout(() => canvas.remove(), 2000);
        '''
        print(f"[DEBUG] 模拟笔画: {stroke_name}, 起点: ({start_x}, {start_y})")

    page.run_js(f'''
        const points = [{", ".join(js_points)}];
        {debug_js}
        let i = 0;
        const interval = setInterval(() => {{
            if (i >= points.length) {{ clearInterval(interval); return; }}
            const [x, y] = points[i++];
            document.elementFromPoint(x, y)?.dispatchEvent(
                new MouseEvent('mousemove', {{clientX: x, clientY: y, bubbles: true}})
            );
        }}, {random.randint(30, 60)});
    ''')
    time.sleep(0.2)


def _extract_page_content(page, embed_images: bool, save_path: str = None, save_callback=None) -> Tuple[str, str]:
    """从页面提取内容和图片"""
    import time
    import random

    def save_snapshot():
        """保存当前页面快照"""
        if not save_callback:
            return
        try:
            content = page.html
            title = page.title
            save_callback(content, title)
        except Exception:
            pass

    # 欺骗页面可见性检测，防止最小化/切换应用时懒加载停止
    page.run_js('''
        Object.defineProperty(document, 'hidden', { get: () => false });
        Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
        document.addEventListener('visibilitychange', e => e.stopImmediatePropagation(), true);
        // 欺骗 IntersectionObserver，让所有元素都被认为可见
        if (window.IntersectionObserver) {
            window.IntersectionObserver = class {
                constructor(cb) { this.cb = cb; }
                observe(el) { this.cb([{ isIntersecting: true, target: el }]); }
                unobserve() {}
                disconnect() {}
            };
        }
    ''')

    initial_height = page.run_js('return document.body.scrollHeight')

    # 分段滚动到底部
    scroll_pos = 0
    while scroll_pos < page.run_js('return document.body.scrollHeight'):
        scroll_pos += 1600
        page.run_js(f'window.scrollTo(0, {scroll_pos})')
        time.sleep(round(random.uniform(0.1, 0.4), 3))

        # 随机画一笔（30%概率），画的时候停下来
        if random.random() < 0.3:
            time.sleep(0.3)
            _simulate_stroke(page)
            time.sleep(0.5)

    # 第一轮滚动后等待，让懒加载有时间触发
    time.sleep(1.0)
    save_snapshot()  # 第一轮滚动后保存
    final_height = page.run_js('return document.body.scrollHeight')

    is_lazy = final_height > initial_height

    if is_lazy:
        # 懒加载页面，继续滚动直到没有新内容
        no_change_count = 0
        while no_change_count < 3:
            last_height = page.run_js('return document.body.scrollHeight')
            scroll_pos = page.run_js('return window.scrollY')
            while scroll_pos < last_height:
                scroll_pos += 1600
                page.run_js(f'window.scrollTo(0, {scroll_pos})')
                time.sleep(round(random.uniform(0.1, 0.4), 3))

                # 随机画一笔（30%概率）
                if random.random() < 0.3:
                    time.sleep(0.3)
                    _simulate_stroke(page)
                    time.sleep(0.5)

            # 在底部停顿更久，等待懒加载
            time.sleep(1.0)
            save_snapshot()  # 每轮滚动后保存
            new_height = page.run_js('return document.body.scrollHeight')
            if new_height == last_height:
                no_change_count += 1
            else:
                no_change_count = 0

    page.run_js('window.scrollTo(0, 0)')
    time.sleep(0.5)

    img_cache = {}
    if embed_images:
        for img in page.eles('tag:img'):
            src = img.attr('src')
            if not src or src.startswith('data:'):
                continue
            try:
                b64 = page.run_js('''
                    var img = arguments[0];
                    var canvas = document.createElement('canvas');
                    canvas.width = img.naturalWidth || img.width;
                    canvas.height = img.naturalHeight || img.height;
                    var ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    try { return canvas.toDataURL(); } catch(e) { return null; }
                ''', img)
                if b64:
                    img_cache[src] = b64
            except Exception:
                pass

    content = page.html
    title = page.title

    if img_cache:
        for src, b64 in img_cache.items():
            content = content.replace(f'src="{src}"', f'src="{b64}"')
            content = content.replace(f"src='{src}'", f"src='{b64}'")

    return content, title


def _fetch_with_browser(url: str, timeout: float, embed_images: bool = True, save_path: str = None, save_callback=None) -> Tuple[str, str]:
    """用 DrissionPage 打开页面并自动获取内容（使用系统默认浏览器）"""
    from DrissionPage import ChromiumPage, ChromiumOptions
    import socket
    import subprocess
    import os
    import time

    def port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    # 尝试连接已有调试端口的浏览器
    for debug_port in [9222, 9223, 9224]:
        if port_in_use(debug_port):
            try:
                co = ChromiumOptions()
                co.set_local_port(debug_port)
                page = ChromiumPage(co)
                # 新开标签页
                tab = page.new_tab(url)
                tab.wait.doc_loaded(timeout=timeout)
                result = _extract_page_content(tab, embed_images, save_path, save_callback)
                tab.close()
                return result
            except Exception:
                pass

    # 获取默认浏览器路径
    import winreg
    browser_path = None
    user_data = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
            cmd = winreg.QueryValueEx(key, "")[0]
            browser_path = cmd.split('"')[1] if cmd.startswith('"') else cmd.split()[0]
        # 确定用户数据目录
        if 'Edge Dev' in browser_path:
            user_data = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge Dev\User Data')
        elif 'Edge' in browser_path:
            user_data = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data')
        elif 'Chrome' in browser_path:
            user_data = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
    except Exception:
        pass

    # 检查浏览器是否在运行（无调试端口）
    global _browser_restarted
    browser_name = os.path.basename(browser_path) if browser_path else 'msedge.exe'
    result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {browser_name}'], capture_output=True, text=True)
    browser_running = browser_name.lower() in result.stdout.lower()

    if browser_running and not _browser_restarted:
        # 弹窗询问用户
        import ctypes
        msg = "未检测到调试端口。\n\n是否关闭当前浏览器并以调试模式重启？\n（这样可以保留你的登录状态）"
        ret = ctypes.windll.user32.MessageBoxW(0, msg, "需要重启浏览器", 0x31)  # MB_OKCANCEL | MB_ICONWARNING
        if ret != 1:  # 用户取消
            raise Exception("用户取消操作")

        # 关闭浏览器
        subprocess.run(['taskkill', '/F', '/IM', browser_name], capture_output=True)
        time.sleep(1)
        _browser_restarted = True

    # 以调试模式启动浏览器
    if browser_path and user_data:
        if not port_in_use(9222):
            cmd = [browser_path, '--remote-debugging-port=9222', f'--user-data-dir={user_data}', '--restore-last-session']
            subprocess.Popen(cmd)
            time.sleep(1)

        # 连接到新启动的浏览器
        co = ChromiumOptions()
        co.set_local_port(9222)
        page = ChromiumPage(co)
        tab = page.new_tab(url)
        tab.wait.doc_loaded(timeout=timeout)
        result = _extract_page_content(tab, embed_images, save_path, save_callback)
        tab.close()
        return result

    # 回退：启动新实例（无cookies）
    co = ChromiumOptions()
    if browser_path:
        co.set_browser_path(browser_path)
    port = 19222
    while port_in_use(port):
        port += 1
    co.set_local_port(port)
    page = ChromiumPage(co)
    page.get(url)
    page.wait.doc_loaded(timeout=timeout)
    return _extract_page_content(page, embed_images, save_path, save_callback)


def fetch_url(
    url: str,
    timeout: float = 15.0,
    proxy: Optional[str] = None,
    main_only: bool = False,
    download_images: bool = True,
    cookie: Optional[str] = None,
    use_browser: bool = False,
    save_path: Optional[str] = None,
    save_callback=None
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
        content, title = _fetch_with_browser(url, timeout, embed_images=download_images, save_path=save_path, save_callback=save_callback)
    else:
        resp = requests.get(url, timeout=timeout, proxies=proxies, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        content = resp.text
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else url

    if main_only:
        # 知乎特殊处理
        if 'zhihu.com' in url:
            if use_browser:
                zhihu_content = _extract_zhihu_from_dom(content)
            else:
                zhihu_content = _extract_zhihu_content(content)
            if zhihu_content:
                content = zhihu_content
            else:
                content = _simple_extract(content)
        # CSDN特殊处理
        elif 'csdn.net' in url:
            content = _extract_csdn_content(content)
        # 微博特殊处理
        elif 'weibo.com' in url or 'weibo.cn' in url:
            content = _extract_weibo_content(content)
        else:
            content = _simple_extract(content)
        # 过滤噪音图片
        content = _filter_noise_images(content)

    # 下载图片并转为base64（非浏览器模式）
    if download_images and not use_browser:
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


def _extract_csdn_content(html: str) -> str:
    """从CSDN页面提取正文"""
    # 提取文章主体 (article_content 或 content_views)
    match = re.search(r'<article[^>]*class="[^"]*baidu_pl[^"]*"[^>]*>([\s\S]+?)</article>', html, re.IGNORECASE)
    if not match:
        match = re.search(r'<div[^>]*id="content_views"[^>]*>([\s\S]+?)</div>\s*<div[^>]*class="[^"]*hide-article-box', html, re.IGNORECASE)
    if not match:
        match = re.search(r'<div[^>]*id="article_content"[^>]*>([\s\S]+?)</div>\s*(?=<div[^>]*class="[^"]*recommend|<div[^>]*id="[^"]*comment)', html, re.IGNORECASE)

    if match:
        content = match.group(1)
        # 移除"阅读更多"遮罩
        content = re.sub(r'<div[^>]*class="[^"]*hide-article-box[^"]*"[^>]*>[\s\S]*?</div>', '', content, flags=re.IGNORECASE)
        return content

    return html


def _extract_weibo_content(html: str) -> str:
    """从微博页面提取正文和互动数据"""
    results = []

    # 提取微博卡片
    cards = re.split(r'<div[^>]*class="[^"]*card-wrap[^"]*"', html)

    for card in cards[1:]:
        # 提取用户名
        user_match = re.search(r'nick-name="([^"]+)"', card)
        user = user_match.group(1) if user_match else ''

        # 提取正文
        text_match = re.search(r'<p[^>]*class="[^"]*txt[^"]*"[^>]*>([\s\S]+?)</p>', card)
        if not text_match:
            continue
        text = text_match.group(1).strip()

        # 提取互动数据
        stats = []
        # 转发
        repost_match = re.search(r'转发\s*(\d+)', card)
        if repost_match and repost_match.group(1) != '0':
            stats.append(f"🔄 {repost_match.group(1)}")
        # 评论
        comment_match = re.search(r'评论\s*(\d+)', card)
        if comment_match and comment_match.group(1) != '0':
            stats.append(f"💬 {comment_match.group(1)}")
        # 点赞
        like_match = re.search(r'赞\s*(\d+)', card)
        if like_match and like_match.group(1) != '0':
            stats.append(f"👍 {like_match.group(1)}")

        stats_line = f'<p><em>{" | ".join(stats)}</em></p>' if stats else ''

        content = f'<p><strong>@{user}</strong></p>\n{text}\n{stats_line}' if user else text
        results.append(content)

    if results:
        return '<hr>\n'.join(results)

    # 回退：简单提取
    return _simple_extract(html)


def _extract_zhihu_from_dom(html: str) -> str:
    """从知乎页面DOM提取正文（浏览器模式，懒加载后的内容）"""
    results = []

    # 用分割法：按AnswerItem分割，每块提取作者和内容
    parts = re.split(r'<div[^>]*class="[^"]*AnswerItem[^"]*"', html)

    for part in parts[1:]:  # 跳过第一个（AnswerItem之前的内容）
        # 提取作者名
        author_match = re.search(r'class="[^"]*UserLink-link[^"]*"[^>]*>([^<]+)</a>', part)
        author = author_match.group(1).strip() if author_match else ''

        # 提取互动数据（点赞、评论）
        stats = []
        vote_match = re.search(r'button[^>]*VoteButton[^>]*>([^<]*\d+[^<]*)</button>', part)
        if vote_match:
            stats.append(f"👍 {vote_match.group(1).strip()}")
        comment_match = re.search(r'>(\d+)\s*条评论<', part)
        if comment_match:
            stats.append(f"💬 {comment_match.group(1)}")
        stats_line = f'<p><em>{" | ".join(stats)}</em></p>\n' if stats else ''

        # 提取内容（RichContent-inner到下一个主要div结束）
        content_match = re.search(r'<div[^>]*class="[^"]*RichContent-inner[^"]*"[^>]*>([\s\S]+?)<div[^>]*class="[^"]*ContentItem-actions', part)
        if content_match:
            content = content_match.group(1).strip()
            if author:
                content = f'<p><strong>答主：{author}</strong></p>\n' + stats_line + content
            results.append(content)

    if results:
        return '<hr>\n'.join(results)
    return ''


def _extract_zhihu_content(html: str) -> str:
    """从知乎页面提取正文（从内嵌JSON中）"""
    import json
    match = re.search(r'<script[^>]*id="js-initialData"[^>]*>([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            entities = data.get('initialState', {}).get('entities', {})
            users = entities.get('users', {})
            results = []

            # 尝试专栏文章
            articles = entities.get('articles', {})
            for article in articles.values():
                content = article.get('content', '')
                if content:
                    author_id = article.get('author', '')
                    author = users.get(author_id, {})
                    author_name = author.get('name', '')
                    # 互动数据
                    stats = []
                    if article.get('voteupCount'):
                        stats.append(f"👍 {article['voteupCount']}")
                    if article.get('commentCount'):
                        stats.append(f"💬 {article['commentCount']}")
                    stats_line = f'<p><em>{" | ".join(stats)}</em></p>\n' if stats else ''
                    if author_name:
                        content = f'<p><strong>作者：{author_name}</strong></p>\n' + stats_line + content
                    results.append(content)

            # 尝试问答（收集所有回答）
            answers = entities.get('answers', {})
            for answer in answers.values():
                content = answer.get('content', '')
                if content:
                    author_info = answer.get('author', {})
                    author_name = author_info.get('name', '') if isinstance(author_info, dict) else users.get(author_info, {}).get('name', '')
                    # 互动数据
                    stats = []
                    if answer.get('voteupCount'):
                        stats.append(f"👍 {answer['voteupCount']}")
                    if answer.get('commentCount'):
                        stats.append(f"💬 {answer['commentCount']}")
                    stats_line = f'<p><em>{" | ".join(stats)}</em></p>\n' if stats else ''
                    if author_name:
                        content = f'<p><strong>答主：{author_name}</strong></p>\n' + stats_line + content
                    results.append(content)

            if results:
                return '<hr>\n'.join(results)
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
    noise_kw += r'|logo|copyright|qrcode|二维码|版权|分享|评论|推荐|相关|热榜|热搜|trending|search'
    pattern = rf'<div[^>]*(?:class|id)=["\'][^"\']*(?:{noise_kw})[^"\']*["\'][^>]*>[\s\S]*?</div>'
    html = re.sub(pattern, '', html, flags=re.IGNORECASE)

    # 尝试提取 article 或 main 或特定class
    content_classes = r'post-content|article-content|entry-content|content-body'
    content_classes += r'|post_body|post_text|article_body|news_body|main-content'
    content_classes += r'|RichContent|Post-RichText|AnswerItem|ztext'  # 知乎
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
    """过滤噪音图片（logo、二维码、小图标、SVG占位图等）"""
    def should_remove(match):
        img_tag = match.group(0)
        # 过滤SVG占位图
        if 'data:image/svg+xml' in img_tag:
            return ''
        # 检查是否是logo/icon/qrcode等
        if re.search(r'(?:logo|icon|qrcode|二维码|badge|avatar)', img_tag, re.IGNORECASE):
            return ''
        # 检查尺寸，过滤小图片（宽或高<100）
        size_match = re.search(r'(?:width|height)[=:]\s*["\']?(\d+)', img_tag, re.IGNORECASE)
        if size_match and int(size_match.group(1)) < 100:
            return ''
        return img_tag

    return re.sub(r'<img[^>]*>', should_remove, html, flags=re.IGNORECASE)
