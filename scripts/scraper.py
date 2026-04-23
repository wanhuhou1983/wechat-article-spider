"""微信文章抓取和解析模块"""
import re
from typing import Optional, Dict
from bs4 import BeautifulSoup, NavigableString, Tag
import requests

# 智能拼接逻辑：判断相邻文本片段是否需要插入空格
# 结尾标点/空白集合（以此结尾则不加空格）
_PUNCT_END = set(' \n\t，。！？；：、…）】』"\'-')
# 开头标点/空白集合（以此开头则不加空格）
_PUNCT_START = set(' \n\t，。！？；：、…（【『"\'')


def fetch_article(url: str) -> Optional[str]:
    """抓取文章 HTML 内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding  # 自动检测编码
        return response.text
    except Exception as e:
        print(f"❌ 抓取失败：{e}")
        return None


def extract_article_content(html: str, url: str) -> Dict:
    """提取文章标题、正文等核心内容"""
    soup = BeautifulSoup(html, 'lxml')
    
    # 提取标题
    title = ""
    title_tag = soup.find('h1', class_='rich_media_title') or soup.find('h2', class_='rich_media_title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        # 备用：从 meta 标签获取
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            title = meta_title.get('content', '')
    
    # 如果没有标题，用 URL 生成
    if not title:
        title = f"微信文章 - {url}"
    
    # 提取正文
    content_html = ""
    content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
    
    if content_div:
        content_html = str(content_div)
    else:
        # 备用：查找包含主要内容的 div
        for div in soup.find_all('div', class_='rich_media_area_primary'):
            content_div = div.find('section')
            if content_div:
                content_html = str(content_div)
                break
    
    # 提取作者
    author = ""
    author_tag = soup.find('span', class_='rich_media_meta_nickname')
    if author_tag:
        author = author_tag.get_text(strip=True)
    
    # 提取发布时间
    publish_date = ""
    date_tag = soup.find('em', class_='rich_media_meta_text')
    if date_tag:
        publish_date = date_tag.get_text(strip=True)
    
    return {
        'title': title,
        'author': author,
        'publish_date': publish_date,
        'content_html': content_html,
        'raw_html': html
    }


def html_to_markdown(content_html: str, url: str, image_mapping: dict) -> str:
    """将 HTML 内容转换为 Markdown，替换图片链接"""
    if not content_html:
        return ""
    
    soup = BeautifulSoup(content_html, 'lxml')
    markdown_parts = []
    
    # 递归处理元素
    def process_element(element):
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                return text
            return None
        
        if not isinstance(element, Tag):
            return None

        if element.name == 'img':
            src = element.get('src') or element.get('data-src')
            if src:
                from urllib.parse import urljoin
                full_url = urljoin(url, src)
                if full_url in image_mapping:
                    alt = element.get('alt', '')
                    return f"![{alt}]({image_mapping[full_url]})"
            return None
        
        if element.name == 'strong' or element.name == 'b':
            text = element.get_text(strip=True)
            return f"**{text}**" if text else None

        if element.name == 'em' or element.name == 'i':
            text = element.get_text(strip=True)
            return f"*{text}*" if text else None

        if element.name == 'a':
            href = element.get('href', '')
            text = element.get_text(strip=True)
            if href and text:
                return f"[{text}]({href})"
            return text or None

        if element.name in ['p', 'section']:
            parts = []
            for child in element.children:
                result = process_element(child)
                if result:
                    parts.append(result)
            if parts:
                # 智能拼接：inline 格式标记（**x**、*x*、![...](...) 等）直接连接，
                # 相邻纯文本节点之间补空格，避免 <span> 文字粘连
                joined = []
                for i, part in enumerate(parts):
                    joined.append(part)
                    if i < len(parts) - 1:
                        cur_end = parts[i][-1] if parts[i] else ''
                        nxt_start = parts[i + 1][0] if parts[i + 1] else ''
                        # 如果当前片段不以标点/空格结尾，且下一个不以标点开头，补一个空格
                        if cur_end not in _PUNCT_END and nxt_start not in _PUNCT_START:
                            joined.append(' ')
                result = ''.join(joined)
                # 压缩多余空格（保留换行）
                result = re.sub(r'  +', ' ', result)
                return result.strip() or None
            return None
        
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(element.name[1])
            text = element.get_text(strip=True)
            if text:
                return f"{'#' * level} {text}"
            return None
        
        if element.name in ['ul', 'ol']:
            return process_list(element)
        
        if element.name == 'blockquote':
            lines = element.get_text(strip=True).splitlines()
            quoted_lines = [f"> {line}" for line in lines if line.strip()]
            if not quoted_lines:
                return None
            # 末尾加一个空的引用行，确保连续 blockquote 之间有空行分隔，
            # 防止渲染器将多个引用块合并为一段
            quoted_lines.append(">")
            return '\n'.join(quoted_lines)
        
        if element.name == 'br':
            return "\n"
        
        # 默认：递归处理子元素
        parts = []
        for child in element.children:
            result = process_element(child)
            if result:
                parts.append(result)
        
        if parts:
            return ''.join(parts)
        return None
    
    # 处理所有顶级元素
    for element in soup.children:
        result = process_element(element)
        if result and result.strip():
            markdown_parts.append(result.strip())
    
    # 合并结果
    result = '\n\n'.join(markdown_parts)
    
    # 清理多余空白
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()
    
    return result


def process_list(list_tag, depth: int = 0) -> str:
    """递归处理列表元素，支持嵌套"""
    items = []
    is_ordered = list_tag.name == 'ol'
    indent = '  ' * depth

    for idx, li in enumerate(list_tag.find_all('li', recursive=False), 1):
        # 分离直接文本和嵌套列表
        nested_parts = []
        text_parts = []

        for child in li.children:
            if isinstance(child, NavigableString):
                t = str(child).strip()
                if t:
                    text_parts.append(t)
            elif isinstance(child, Tag):
                if child.name in ('ul', 'ol'):
                    nested_parts.append(process_list(child, depth + 1))
                else:
                    t = child.get_text(strip=True)
                    if t:
                        text_parts.append(t)

        text = ''.join(text_parts).strip()
        prefix = f"{indent}{idx}." if is_ordered else f"{indent}-"
        line = f"{prefix} {text}" if text else f"{prefix}"
        items.append(line)

        for nested in nested_parts:
            if nested:
                items.append(nested)

    return '\n'.join(items) if items else ""
