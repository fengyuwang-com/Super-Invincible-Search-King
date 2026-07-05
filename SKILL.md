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

# 接力爬虫 — 人机协作图片采集

## 核心理念

```
你(用户)         我(AI)          浏览器
 |                |               |
 |  "搜猫图"      |               |
 | -------------  |               |
 |                | Bing -> Baidu -> Yandex -> ...
 |                | (CAPTCHA)     |
 |                | X Bing        |
 |                | X Baidu       |
 |                | <---Yandex OK |
 | <---15张图---  |               |
```

**我能干的：** 8个引擎自动链 -> 滚动 -> 提取 -> 下载
**碰到验证码/拦截：** 跳过，换下一个引擎
**所有引擎都挂了：** 弹出浏览器，交给你手动

## 引擎链 (默认顺序)

`unsplash -> pexels -> pixabay -> burst -> bing -> baidu -> brave -> ddg -> sogou -> so360`

免费摄影站优先（可商用），通用搜索引擎兜底（版权未知）。

遇到CAPTCHA/拦截自动跳过，直到有引擎出图为止。

## 使用

```bash
# 默认引擎链（免费站优先，搜索兜底）
python scraper.py "狗"

# 仅用免费摄影站（Unsplash/Pexels/Pixabay/Burst）
python scraper.py "狗" --free --download -o pics

# 指定引擎
python scraper.py "猫" -e unsplash

# 自定义链
python scraper.py "风景" -e unsplash,pixabay,pexels

# 搜 + 下载 + 生成来源文档
python scraper.py "狗" -e unsplash,pixabay --download -o pics -n 20
# 每次下载自动生成 _sources_{时间戳}.json

# 扒任意网页
python scraper.py --url "https://example.com"

# 手动模式：你浏览我提取（循环接力）
python scraper.py --url "https://pixiv.net" --manual
```

## 版权 & 来源文档

每次 `--download` 会自动在输出目录生成 `_sources_{时间戳}.json`：

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
