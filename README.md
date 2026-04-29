# wechat-article-spider

微信公众号文章爬虫 — 将微信公号文章转换为干净的 Markdown + 本地图片。

## 核心改进（v1.0 → v2.0）

| 项目 | v1.0（旧） | v2.0（新） |
|------|-----------|-----------|
| 抓取方式 | `requests` 静态请求 | **Playwright Firefox** 无头浏览器 |
| HTML→MD | 自写递归转换器 | **`markdownify`** 专业库 |
| 反爬能力 | 无 | 完整浏览器指纹 + UA 伪装 |
| 排版质量 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

基于 `wechat-article-to-markdown`（jackwener，594⭐）内核，使用 Playwright 替代 Camoufox（国内网络环境兼容性更好）。

## 功能

- 输入微信公号文章 URL
- 自动抓取文章内容（标题、正文、作者、发布时间）
- 下载所有图片到 `images/` 文件夹
- 生成带 YAML frontmatter 的 Markdown 文件
- 图片使用相对路径引用

## 安装

```bash
pip install wechat-article-to-markdown
python -m playwright install firefox
```

## 用法

```bash
python scripts/main.py https://mp.weixin.qq.com/s/xxxxx
```

## 输出结构

```
output/
└── <文章标题>/
    ├── <文章标题>.md
    └── images/
        ├── img_001_xxx.jpg
        ├── img_002_xxx.png
        └── ...
```

### Markdown 格式

```markdown
---
title: "文章标题"
author: "公众号名称"
date: "2024-01-01 12:00:00"
source: "https://mp.weixin.qq.com/s/xxxxx"
crawled_at: "2024-01-01 12:30:00"
---

# 文章标题

正文内容...

![图片描述](./images/img_001.png)
```

## 依赖

- Python 3.8+
- wechat-article-to-markdown
- playwright（Firefox 引擎）
