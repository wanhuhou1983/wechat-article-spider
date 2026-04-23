# wechat-article-spider

微信公众号文章爬虫 - 将微信公号文章转换为 Markdown + 本地图片

## 功能

- 输入微信公号文章 URL
- 自动抓取文章内容（标题、正文、作者、发布时间）
- 下载所有图片到 `images/` 文件夹
- 生成 Markdown 文件，图片使用相对路径引用

## 安装

```bash
cd scripts
pip install -r requirements.txt
```

## 用法

```bash
# 下载到当前目录
python scripts/main.py https://mp.weixin.qq.com/s/xxxxx

# 指定输出目录
python scripts/main.py https://mp.weixin.qq.com/s/xxxxx ./my-articles
```

## 输出结构

```
output/
├── 文章标题.md
└── images/
    ├── img_001_xxx.jpg
    └── ...
```

## 依赖

- requests
- beautifulsoup4
- lxml

## 注意事项

- 微信文章可能有反爬机制，如遇失败可稍后重试
- 部分动态加载的图片可能无法获取