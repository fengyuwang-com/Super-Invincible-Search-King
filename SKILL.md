---
name: visual-scraper
description: >
  MUST USE when the user needs to find/extract/download images from any website.
  Uses a headed Playwright browser (visible window) to bypass anti-bot measures.
triggers:
  - image: 配图/图片/图/找图/搜图/照片/插图/插画/image/picture/photo/illustration
  - search: 搜不到/找不到/图不对/空白/没找到/没有图/扒图/采集
  - engine: bing/必应/google/谷歌/baidu/百度/搜索引擎
  - url: 打开这个网页/看这个网站/这个页面有图
metadata:
  type: skill
  platforms: windows
---

# Visual Scraper — 有头浏览器图片采集

## 核心原理

搜索引擎的图片结果都是 **JavaScript 动态加载** 的，普通 HTTP 请求（curl / requests / Jina Reader）只拿到空壳页面，没有图片数据。

**`headless=False`（有头浏览器模式）** 启动真实 Chrome：
- 浏览器指纹与真实用户一致 → 不会被反爬识别
- JS 完整渲染 → 所有图片都能出来
- 用户能看到浏览器窗口 → 遇到验证码/登录可以手动处理

## 支持的来源

| 来源 | 命令 | 说明 |
|------|------|------|
| Bing 图片 | `python scraper.py "关键词"` | 默认引擎，最稳定 |
| Google 图片 | `python scraper.py "关键词" -e google` | 需能访问 Google |
| 百度图片 | `python scraper.py "关键词" -e baidu` | 中文结果好 |
| 任意网页 | `python scraper.py --url "https://..."` | 扒任何网站 |
| 交互模式 | `python scraper.py --url "..." -i` | 你手动浏览我提取 |

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
python scraper.py "cute cat" --engine google

# 百度搜图
python scraper.py "山水画" --engine baidu

# 扒任意网页的图
python scraper.py --url "https://unsplash.com"

# 搜索 + 下载到指定目录
python scraper.py "Mona Lisa" --download --output ./pics

# 交互模式（你手动浏览，我提取）
python scraper.py --url "https://example.com" --interactive
```

## 为什么能绕过反爬？

| 反爬手段 | 有头浏览器 (本工具) | 无头浏览器 | curl/requests |
|---------|-------------------|-----------|---------------|
| WebGL 指纹 | ✅ 真实 GPU | ⚠️ 可检测 | ❌ |
| navigator.webdriver | ✅ false | ⚠️ 可能暴露 | ❌ |
| JS 渲染 | ✅ 完整渲染 | ✅ 完整渲染 | ❌ 空壳页面 |
| 屏幕分辨率 | ✅ 真实 | ❌ 默认值 | ❌ |
| TLS 指纹 | ✅ Chrome 原生 | ✅ Chrome 原生 | ⚠️ 易识别 |
| 验证码 | ✅ 用户可以手动解决 | ❌ 卡住 | ❌ 卡住 |

## 图片 URL 怎么提取的？

每种搜索引擎的内部数据结构不同：

- **Bing**: `<div class="iusc" m="{"murl":"原始大图URL", ...}">` → `.iusc` 元素的 `m` 属性存着原始大图
- **Google**: `img.rg_i` 或 `img[data-src]` → 需要等待 JS 渲染完成
- **百度**: `img.main_img` → 或 `data-imgurl` 属性
- **任意网页**: 通用 `<img>` 标签提取 + 去重 + 按尺寸排序

## 注意事项

- **不要改为 `headless=True`** — 无头模式会被搜索引擎拦截，这是这个工具的核心
- 浏览器窗口弹出后自动操作，用户关闭窗口退出
- 交互模式 (`--interactive`) 让你手动浏览，我提取图片
- 图片版权归属原作者，仅供个人学习参考
