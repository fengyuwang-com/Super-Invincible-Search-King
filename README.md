# Visual Scraper

有头浏览器图片采集工具——用 Playwright 打开真实浏览器窗口，从**任意网站**提取图片。

## 解决的问题

普通方式搜图（curl / requests / Jina Reader）经常失败：
- ❌ 搜到的图不对题
- ❌ 返回空白/占位图
- ❌ 因为搜索引擎图片都是 JS 动态加载的

**有了 Playwright 有头浏览器：**
- ✅ Bing / Google / 百度搜图都能用
- ✅ 任意网站都能扒图
- ✅ 有头模式不会被反爬识别
- ✅ 用户能看到浏览器窗口，遇到验证码可以手动处理

## 安装

```bash
pip install playwright
playwright install chromium
```

## 使用

```bash
# Bing 搜图（默认）
python scraper.py "富春山居图 黄公望"

# Google 搜图
python scraper.py "cute cat" -e google

# 百度搜图
python scraper.py "山水画" -e baidu

# 扒任意网页的图
python scraper.py --url "https://example.com/gallery"

# 搜索 + 下载
python scraper.py "Mona Lisa" --download -o ./pics

# 交互模式（你手动操作，我提取）
python scraper.py --url "https://example.com" -i
```

## 项目结构

```
image-finder/
├── scraper.py           # 主脚本
├── SKILL.md             # Claude Code skill
├── requirements.txt     # Python 依赖
└── README.md            # 本文件
```

## 支持的引擎

| 引擎 | 参数 |
|------|------|
| Bing | `-e bing` (默认) |
| Google | `-e google` |
| 百度 | `-e baidu` |
| 任意网页 | `--url URL` |
| 交互模式 | `--interactive` or `-i` |

## License

MIT
