"""图片下载处理模块"""
import os
import hashlib
import requests
from urllib.parse import urljoin
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


_CONTENT_TYPE_EXT = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/svg+xml': '.svg',
}


def download_image(url: str, save_path_without_ext: str, timeout: int = 10) -> Optional[str]:
    """
    下载单张图片，从 GET 响应的 Content-Type 推断扩展名。
    返回最终保存路径，失败返回 None。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mp.weixin.qq.com/'
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        # 从响应 Content-Type 推断扩展名，避免额外 HEAD 请求
        content_type = response.headers.get('Content-Type', '')
        mime = content_type.split(';')[0].strip()
        ext = _CONTENT_TYPE_EXT.get(mime, '')

        # 如果 Content-Type 无法推断，尝试从 URL 路径取扩展名
        if not ext:
            from urllib.parse import urlparse
            url_ext = os.path.splitext(urlparse(url).path)[1].lower()
            ext = url_ext if url_ext and len(url_ext) <= 5 else '.jpg'

        final_path = save_path_without_ext + ext
        with open(final_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return final_path
    except Exception as e:
        print(f"⚠️ 图片下载失败：{url} - {e}")
        return None


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
    """线程池任务：下载单张图片（扩展名由 GET 响应 Content-Type 决定），返回 (img_url, relative_path | None)"""
    img_url, images_dir, idx = args
    url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
    base_name = f"img_{idx:03d}_{url_hash}"
    save_path_without_ext = os.path.join(images_dir, base_name)
    final_path = download_image(img_url, save_path_without_ext)
    if final_path:
        return img_url, f"images/{os.path.basename(final_path)}"
    return img_url, None


def save_images_and_update_html(
    image_urls: List[str],
    output_dir: str,
    base_url: str,
    max_workers: int = 5,
) -> dict:
    """
    并发下载所有图片，返回 URL → 相对路径 的映射。
    扩展名由 GET 响应的 Content-Type 决定，无需额外 HEAD 请求。
    """
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # 构建任务列表：传 images_dir + idx，由 _download_task 组合完整路径
    tasks = [
        (img_url, images_dir, idx)
        for idx, img_url in enumerate(image_urls, 1)
    ]

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
