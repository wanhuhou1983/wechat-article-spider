#!/usr/bin/env python3
"""
微信公众号文章爬虫 — 基于 Playwright + wechat-article-to-markdown

使用 Playwright Firefox 浏览器自动化抓取 + markdownify 高质量 HTML→Markdown 转换。
解决旧版 requests + 手动转换器排版丢失的问题。

用法:
    python main.py <文章 URL>
"""

import sys
import os
import re
import asyncio
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

# ---------- 导入依赖 ----------
try:
    from bs4 import BeautifulSoup, Tag
    from wechat_article_to_markdown import (
        process_content,
        convert_to_markdown,
        download_all_images,
        replace_image_urls,
        extract_publish_time,
    )
    from playwright.async_api import async_playwright
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("   请执行: pip install wechat-article-to-markdown playwright")
    sys.exit(1)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def extract_metadata_robust(soup: BeautifulSoup, html: str, url: str) -> dict:
    """健壮的文章元数据提取，兼容多版本微信页面结构"""

    # ---- 标题 ----
    title = ""
    for sel in [
        "h1#js_text_title",
        "h1.rich_media_title",
        "h2.rich_media_title",
        "#activity-name",
        "meta[property='og:title']",
    ]:
        el = soup.select_one(sel)
        if el:
            if el.name == "meta":
                title = el.get("content", "")
            else:
                title = el.get_text(strip=True)
            break

    # ---- 作者/公众号 ----
    author = ""
    for sel in [
        "#js_name",
        "span.rich_media_meta_nickname",
        "strong.rich_media_meta_nickname",
        "#js_author_name",
        "meta[property='og:article:author']",
    ]:
        el = soup.select_one(sel)
        if el:
            if el.name == "meta":
                author = el.get("content", "") or el.get("value", "")
            else:
                author = el.get_text(strip=True)
            break

    # ---- 发布时间 ----
    publish_time = extract_publish_time(html)

    return {
        "title": title or f"微信文章 - {url}",
        "author": author,
        "publish_time": publish_time,
        "source_url": url,
    }


def build_markdown_robust(meta: dict, md_body: str) -> str:
    """构建带 YAML frontmatter 的 Markdown（不重复添加标题，正文已有）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "---",
        f'title: "{meta["title"]}"',
        f'author: "{meta["author"]}"',
        f'date: "{meta["publish_time"]}"',
        f'source: "{meta["source_url"]}"',
        f'crawled_at: "{now}"',
        "---",
        "",
    ]
    return "\n".join(lines) + "\n" + md_body


async def fetch_article(url: str, output_dir: Path) -> Path:
    """使用 Playwright Firefox 抓取微信文章并保存为 Markdown"""
    print(f"🔄 正在抓取: {url}")

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass

        # 等待正文加载
        try:
            await page.wait_for_selector("#js_content", timeout=15000)
        except Exception:
            print("⚠️  正文容器未检测到，尝试强制读取...")

        await asyncio.sleep(3)
        html = await page.content()
        await browser.close()

    # 解析
    soup = BeautifulSoup(html, "html.parser")

    # 提取元数据（健壮版）
    meta = extract_metadata_robust(soup, html, url)
    if not meta["title"]:
        print("❌ 未能提取到文章标题，可能触发了验证码")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "debug.html").write_text(html, encoding="utf-8")
        print(f"🔍 已保存原始 HTML 到 {output_dir / 'debug.html'}")
        sys.exit(1)

    print(f"📄 标题: {meta['title']}")
    print(f"👤 公众号: {meta.get('author', '未知')}")
    print(f"📅 时间: {meta.get('publish_time', '未知')}")

    # 处理正文（复用库的 process_content，它找 #js_content 没问题）
    content_html, code_blocks, img_urls = process_content(soup)
    if not content_html:
        print("❌ 未能提取到正文内容")
        sys.exit(1)

    # HTML → Markdown（markdownify，保留排版质量）
    print("📝 转换 Markdown...")
    md = convert_to_markdown(content_html, code_blocks)

    # 下载图片
    safe_title = re.sub(r'[/\\?%*:|"<>]', "_", meta["title"])[:80]
    article_dir = output_dir / safe_title
    img_dir = article_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    if img_urls:
        print(f"🖼️  下载 {len(img_urls)} 张图片...")
        url_map = await download_all_images(img_urls, img_dir)
        md = replace_image_urls(md, url_map)
    else:
        print("📭 无图片需要下载")

    # 构建最终 Markdown
    result = build_markdown_robust(meta, md)
    md_path = article_dir / f"{safe_title}.md"
    md_path.write_text(result, encoding="utf-8")

    print(f"✅ 已保存: {md_path}")
    print(f"📊 统计: {len(md)} 字 / {len(img_urls)} 图")
    return md_path


def main():
    if len(sys.argv) < 2:
        print("❌ 用法：python main.py <文章URL>")
        print(f"   例如：python main.py https://mp.weixin.qq.com/s/xxxxx")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("https://mp.weixin.qq.com/"):
        print("❌ 无效的微信文章 URL")
        sys.exit(1)

    output_dir = DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    try:
        md_path = asyncio.run(fetch_article(url, output_dir))
        print(f"\n🎉 完成!")
        print(f"   📄 Markdown: {md_path}")
        print(f"   📁 图片: {md_path.parent / 'images'}")
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
