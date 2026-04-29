---
name: wechat-article-spider
version: 2.0.0
description: 微信公众号文章抓取并转换为 Markdown + 本地图片。基于 Playwright Firefox 浏览器自动化 + markdownify 高质量转换。
---

# wechat-article-spider

微信公众号文章爬虫 — 基于 `wechat-article-to-markdown`（jackwener，594⭐）的内核，将微信公号文章转换为干净的 Markdown 格式。

## 核心优势

- 🛡️ **Playwright 浏览器自动化**：无头 Firefox 渲染，获取完整 DOM，绕过微信反爬
- 🖼️ **图片本地化**：自动下载图片到本地 `images/` 目录
- 📝 **高质量 Markdown**：基于 `markdownify` 库，排版保留远超自写转换器
- 💻 **代码块处理**：正确处理微信 `code-snippet` 代码块 + 语言标识
- 📋 **元数据提取**：带 YAML frontmatter（标题、公众号、发布时间、原文链接、抓取时间）

## 关键改进（v1.0 → v2.0）

| 项目 | v1.0（旧） | v2.0（新） |
|------|-----------|-----------|
| 抓取方式 | `requests` 静态请求 | Playwright Firefox 无头浏览器 |
| HTML→MD | 自写递归转换器 | `markdownify` 专业库 |
| 反爬能力 | 无 | 浏览器指纹 + User-Agent 伪装 |
| 排版质量 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

## 依赖

- Python 3.8+
- `wechat-article-to-markdown` 包（自动安装 markdownify、playwright 等）
- Playwright Firefox 浏览器引擎

## 安装

```bash
# 安装 Python 包
pip install wechat-article-to-markdown

# 安装浏览器引擎
python -m playwright install firefox
```

## 用法

### 命令行

```bash
python scripts/main.py <文章URL>
```

### 示例

```bash
# 下载到 scripts/ 同级的 output/ 目录
python scripts/main.py https://mp.weixin.qq.com/s/xxxxx
```

### 输出结构

```
output/
└── <文章标题>/
    ├── <文章标题>.md
    └── images/
        ├── img_001_xxx.jpg
        ├── img_002_xxx.png
        └── ...
```

### Markdown 文件格式

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

## 注意事项

- 首次运行会启动无头 Firefox 浏览器（约需 5-15 秒）
- 微信可能有更严格的反爬，如遇失败可稍后重试
- 部分动态加载的图片可能无法获取
- 公众号名称在某些页面结构中为 JS 动态渲染，可能为空
