"""图片下载处理模块"""
import os
import hashlib
import requests
from urllib.parse import urlparse, urljoin
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed


# Content-Type 到扩展名映射
_CONTENT_TYPE_EXT = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/svg+xml': '.svg',
}


def get_image_filename(url: str, index: int, content_type: str = '') -> str:
    """生成图片文件名，优先从 Content-Type 推断扩展名"""
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()

    # URL 无扩展名或扩展名过长时，从 Content-Type 推断
    if not ext or len(ext) > 5:
        if content_type:
            # Content-Type 可能含参数如 "image/jpeg; charset=..."
            mime = content_type.split(';')[0].strip()
            ext = _CONTENT_TYPE_EXT.get(mime, '.jpg')
        else:
            ext = '.jpg'

    # 使用 URL 哈希生成唯一文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"img_{index:03d}_{url_hash}{ext}"


def download_image(url: str, save_path: str, timeout: int = 10) -> bool:
    """下载单张图片，返回是否成功"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mp.weixin.qq.com/'
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"⚠️ 图片下载失败：{url} - {e}")
        return False


def get_content_type(url: str, timeout: int = 5) -> str:
    """HEAD 请求获取图片 Content-Type"""
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://mp.weixin.qq.com/'
    }
    try:
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        return resp.headers.get('Content-Type', '')
    except Exception:
        return ''


def extract_images(html_content: str, base_url: str) -> List[str]:
    """从 HTML 中提取所有图片 URL，返回去重后的 URL 列表"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'lxml')
    seen = set()
    images = []

    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src:
            full_url = urljoin(base_url, src)
            if full_url not in seen:
                seen.add(full_url)
                images.append(full_url)

    return images


def _download_task(args):
    """线程池任务：下载单张图片，返回 (img_url, relative_path | None)"""
    img_url, save_path, filename = args
    # 先获取 Content-Type 确定正确扩展名（save_path 已含正确扩展名）
    ok = download_image(img_url, save_path)
    if ok:
        return img_url, f"images/{filename}"
    return img_url, None


def save_images_and_update_html(
    image_urls: List[str],
    output_dir: str,
    base_url: str,
    max_workers: int = 5,
) -> dict:
    """
    并发下载所有图片，返回 URL → 相对路径 的映射。
    """
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # 构建任务列表：先用 HEAD 请求获取 Content-Type 以推断正确扩展名
    tasks = []
    for idx, img_url in enumerate(image_urls, 1):
        content_type = get_content_type(img_url)
        filename = get_image_filename(img_url, idx, content_type)
        save_path = os.path.join(images_dir, filename)
        tasks.append((img_url, save_path, filename))

    url_mapping = {}
    downloaded_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_download_task, task): task for task in tasks}
        for future in as_completed(futures):
            img_url, relative_path = future.result()
            if relative_path:
                url_mapping[img_url] = relative_path
                downloaded_count += 1

    print(f"✅ 下载 {downloaded_count}/{len(image_urls)} 张图片")
    return url_mapping
