---
name: super-invincible-search-king
description: >
  MUST USE when user needs ANY search — images, text, or webpage content.
  Auto-extracts images across 12 engines (free photography + general search),
  text search across 6 engines with title/link/snippet, or reads any URL's
  body content. Playwright-driven, CAPTCHA-resistant with human-in-the-loop fallback.
triggers:
  - search: 搜索/搜图/搜文字/搜网页/查资料/找资源/调研/研究/查询/情报/报告/找信息/搜集/扒/采集
  - image: 配图/图片/图/找图/搜图/照片/插图/插画/image/picture/photo/illustration
  - text: 文字/信息/搜索结果/文章/内容/正文/摘要/title/link/snippet/article/content
  - fail: 搜不到/找不到/图不对/空白/没找到/没有图/扒图/采集/人机验证/captcha/被墙/403/反爬
  - action: 接力/手动/协作/交互/你浏览我提取/帮我看看/来源/版权/出处/商用
  - engine: 引擎链/fallback/自动换/换一个/换引擎/这个不行/免费/摄影/cc0/unsplash
metadata:
  type: skill
  platforms: windows
---

# 超级万能搜索大王

位置：`C:\FengProj\Search-King\scraper.py`

## 三种模式

### 🔍 搜图（默认）

`python scraper.py "关键词" [选项]`

自动链：`unsplash ➝ pexels ➝ pixabay ➝ burst ➝ bing ➝ baidu ➝ brave ➝ ddg ➝ sogou ➝ so360`

免费摄影站优先（可商用），通用搜索兜底（版权未知）。

### 🔎 文字搜索

`python scraper.py --search "关键词" [选项]`

自动链：`bing-web ➝ baidu-web ➝ google-web ➝ ddg-web ➝ brave-web ➝ sogou-web`

**全挂了 → 自动切手动模式**：浏览器保持打开，用户自己搜，搜完按 Enter 提取结果。

### 📖 读网页

`python scraper.py --read URL [URL2 URL3 ...]`

支持多个 URL 并行读取、CloakBrowser 反检测模式。

**遇到验证码 → 自动切手动模式**：浏览器保持打开，你处理完验证码后按 Enter 提取。

## 可选后端

| 后端 | 用途 | 依赖 |
|------|------|------|
| `--backend edge`（默认） | 系统 Edge，隐身效果更好 |
| `--backend chromium` | Playwright 内置 Chromium |
| `--backend cloak` | CloakBrowser 反检测，过 Cloudflare | `pip install cloakbrowser` |
| `--backend lite` | 纯 HTTP，无浏览器（仅文字搜索） |
| `--backend opencli` | 真实 Edge 浏览器，抗 WAF | `npm install -g opencli` |
| `--backend manual` | 你浏览我提取，循环接力 |

## 深度爬取（Crawl4AI）

`python scraper.py --crawl URL [URL2 ...]`

Crawl4AI 引擎，自动处理 JS 异步加载，输出结构化 Markdown。配合 `--output` 自动保存到文件。

> 高强度反爬网站被拦截时，退回到 `--backend cloak` 或 `--backend opencli`。

## 浏览器选择

`--backend edge`（默认）对百度/搜狗/DuckDuckGo 直接出结果。  
`--backend chromium` 是备选，某些场景效果更好。

## 使用示例

```bash
# 搜文字（全自动，全挂切手动）
python scraper.py --search "中概股 KWEB 2026"

# 读网页（遇验证码自动切手动）
python scraper.py --read "https://zhuanlan.zhihu.com/p/123"

# 搜图 + 下载
python scraper.py "风景" --download -o pics

# 手动模式
python scraper.py --read "https://example.com" --backend manual

# CloakBrowser 反检测
python scraper.py --search "AI" --backend cloak

# 雪球帖子
python scraper.py --backend opencli --fetch xueqiu --user-id 3300065034

# B站视频 + 音频
python scraper.py --backend opencli --fetch bilibili --mid 473168952
python scraper.py --backend opencli --fetch bilibili --mid 473168952 --audio
python scraper.py --backend opencli --fetch bilibili --mid 473168952 --series
```

## 接力规则

| 状况 | 我做什么 | 你做什么 |
|------|---------|---------|
| OK 引擎出结果 | 自动提取 | 等结果 |
| 人机验证/拦截 | 跳过，换下一个引擎 | 等结果 |
| **所有引擎全挂** | **切手动模式，浏览器保持打开** | **自己搜 → 按 Enter 我提取** |
| **读网页遇验证码** | **切手动模式，等你处理** | **处理验证码 → 按 Enter 提取** |
| 手动模式 | 等你浏览完按回车 | 自己逛 → 回车 |
| 下载失败 | 提示防盗链 | 手动打开链接 |
