---
name: relay-scraper
description: >
  MUST USE when user needs images from any website. Auto-extracts images
  across 10+ engines including free photography sites (Unsplash/Pexels/
  Pixabay/Burst); generates source docs with license info; skipped blocked
  engines silently.
triggers:
  - image: 配图/图片/图/找图/搜图/照片/插图/插画/image/picture/photo/illustration
  - fail: 搜不到/找不到/图不对/空白/没找到/没有图/扒图/采集/人机验证/captcha/被墙/403
  - action: 接力/手动/协作/交互/你浏览我提取/帮我看看/来源/版权/出处/商用
  - engine: 引擎链/fallback/自动换/换一个/换引擎/这个不行/免费/摄影/cc0/unsplash
metadata:
  type: skill
  platforms: windows
---

# 接力爬虫 — 人机协作万能搜索器

## 核心理念

```
你(用户)         我(AI)          浏览器
 |                |               |
 |  "搜封面设计"  |               |
 | -------------  |               |
 |          --search 模式         |
 |                | Bing -> Baidu -> Google -> ...
 |                | (CAPTCHA)     |
 |                | X Bing        |
 |                | <---Baidu OK  |
 | <---10条结果-- |               |
```

**我能干的：**
  - 🔍 **搜图** — 8个引擎自动链 -> 滚动 -> 提取 -> 下载
  - 🔎 **搜文字** (`--search`) — 6个搜索引擎，标题+链接+摘要
  - 📖 **读网页** (`--read URL`) — 打开任意网页提取正文
  - 🤝 **手动模式** — 你浏览我提取

**碰到验证码/拦截：** 跳过，换下一个引擎
**所有引擎都挂了：** 弹出浏览器，交给你手动

## 模式说明

### 🔍 搜图模式（默认）

`python scraper.py "关键词" [选项]`

自动链：`unsplash -> pexels -> pixabay -> burst -> bing -> baidu -> brave -> ddg -> sogou -> so360`

免费摄影站优先（可商用），通用搜索兜底（版权未知）。

### 🔎 文字搜索模式

`python scraper.py --search "关键词" [选项]`

自动链：`bing-web -> baidu-web -> google-web -> ddg-web -> brave-web -> sogou-web`

输出每条结果的标题、链接、摘要片段。

### 📖 读网页模式

`python scraper.py --read "https://example.com/article"`

自动提取正文，显示标题+字数+内容（前200行）。

## 使用示例

```bash
# 搜图（默认）
python scraper.py "猫"

# 文字搜索
python scraper.py --search "B站封面设计技巧 高点击"

# 读网页
python scraper.py --read "https://example.com/article"

# 仅用免费摄影站（可以商用）
python scraper.py "风景" --free --download -o pics

# 指定图片引擎
python scraper.py "猫" -e unsplash

# 自定义图片引擎链
python scraper.py "乔丹" -e bing,baidu

# 搜图 + 下载 + 来源文档
python scraper.py "狗" -e unsplash,pixabay --download -o pics -n 20

# 扒任意网页的图
python scraper.py --url "https://example.com"

# 手动模式：你浏览我提取
python scraper.py --url "https://pixiv.net" --manual
```

## 版权 & 来源文档

每次 `--download` 会自动在输出目录生成 `_sources_{时间戳}.json`。

## 接力规则

| 状况 | 我做什么 | 你做什么 |
|------|---------|---------|
| OK 引擎出图 | 自动提取 + 下载 | 关浏览器 |
| 人机验证 | 跳过，换下一个引擎 | 等结果 |
| 拦截/403 | 跳过，换下一个引擎 | 等结果 |
| 7个引擎全挂 | 弹出浏览器等你手动搜 | 自己逛 -> 回车 |
| 手动模式 (-m) | 等你浏览完按回车 | 自己逛 -> 回车 |
| 下载失败 | 提示防盗链 | 手动打开链接 |

## 可用引擎

| key | 引擎 | 许可证 | 地区 |
|-----|------|--------|------|
| **unsplash** | **Unsplash** | **✅ 免费商用** | 全球 |
| **pexels** | **Pexels** | **✅ 免费商用** | 全球 |
| **pixabay** | **Pixabay** | **✅ 免费商用** | 全球 |
| **burst** | **Burst (Shopify)** | **✅ 免费商用** | 全球 |
| bing | Bing Images | ⚠️ 未知 | 全球 |
| baidu | 百度图片 | ⚠️ 未知 | 中国 |
| yandex | Yandex Images | ⚠️ 未知 | 俄罗斯 |
| ddg | DuckDuckGo Images | ⚠️ 未知 | 全球 |
| brave | Brave Image Search | ⚠️ 未知 | 全球 |
| sogou | 搜狗图片 | ⚠️ 未知 | 中国 |
| so360 | 360图片 | ⚠️ 未知 | 中国 |
| google | Google Images | ⚠️ 未知 (易拦截) | 全球 |

## 安装

```bash
pip install playwright
playwright install chromium
```
