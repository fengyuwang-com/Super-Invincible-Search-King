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

# 超级无敌万能搜索大王 — 人机协作全能搜索器

位置：`C:\FengProj\Search-King\scraper.py`

## 三种模式

### 🔍 搜图模式（默认）

`python scraper.py "关键词" [选项]`

自动链：`unsplash -> pexels -> pixabay -> burst -> bing -> baidu -> brave -> ddg -> sogou -> so360`

免费摄影站优先（可商用），通用搜索兜底（版权未知）。

### 🔎 文字搜索模式

`python scraper.py --search "关键词" [选项]`

自动链：`bing-web -> baidu-web -> google-web -> ddg-web -> brave-web -> sogou-web`

**全挂了 → 自动切手动模式**：浏览器保持打开，你自己搜，搜完按 Enter 我提取结果。

### 📖 读网页模式

`python scraper.py --read "https://example.com/article"`

自动提取正文，显示标题+字数+内容（前200行）。

**遇到验证码 → 自动切手动模式**：浏览器保持打开，你处理完验证码后按 Enter，我提取内容。

### 🕷️ 抓取模式（opencli 浏览器）

`python scraper.py --backend opencli --fetch <site> [选项]`

用 opencli 控制真实 Edge 浏览器，绕过 WAF/反爬。

**雪球用户帖子：**
```bash
python scraper.py --backend opencli --fetch xueqiu --user-id 3300065034
```
遇 WAF 会提示你手动处理验证码，处理后按 Enter 继续。

**B站视频列表：**
```bash
python scraper.py --backend opencli --fetch bilibili --mid 473168952
```
自动翻页（最多12页），提取全部 BV ID + 标题。

**B站视频按合集分类：**
```bash
python scraper.py --backend opencli --fetch bilibili --mid 473168952 --series
```
自动遍历全部合集/系列，每个系列内保留顺序，支持翻页（>30集）。
输出 JSON `bilibili_series_<mid>.json`，结构：
```
[{name: "合集·千刀千法", count: 15, url: "...",
  videos: [{bv: "BV19zkHBWErC", title: "..."}]}]
```

**B站全部音频下载：**
```bash
python scraper.py --backend opencli --fetch bilibili --mid 473168952 --audio
```
用 yt-dlp 并行下载全部视频音频，低质量（~65kbps，讲课足够），标题自动写入文件名。
文件保存到 `bilibili_audio_<mid>/`。

**通用页面读取（反爬网站）：**
```bash
python scraper.py --backend opencli --read "https://xueqiu.com/u/3300065034"
```
遇到 Cloudflare/WAF 自动提示手动处理。

依赖：`npm install -g opencli`（可选），`pip install yt-dlp`（仅音频下载需要）。opencli 未装时友好提示安装方法，不崩溃。

### 🌐 浏览器选择

`--browser edge`（默认）用你系统安装的 Edge，隐身效果更好
`--browser chromium` 用 Playwright 自带的 Chromium

Edge 对百度/搜狗/DuckDuckGo 直接出结果（Google/Brave 仍可能触发验证码）。
Chromium 是备选，某些时候效果反而更好。

### 🤝 手动模式

`python scraper.py --url "https://example.com" --manual`

你浏览我提取。浏览器弹出来你自己逛，逛完按回车，AI 提取内容。

## 核心理念

人机协作：自动引擎能搞定就自动搞定，搞不定就交给你手动，你搞定了我帮你提取。

## 使用示例

```bash
# 搜文字（全引擎链自动，全挂了切手动）
python C:\FengProj\Search-King\scraper.py --search "中概股 KWEB 2026"

# 读网页（遇到验证码自动切手动）
python C:\FengProj\Search-King\scraper.py --read "https://zhuanlan.zhihu.com/p/123"

# 搜图 + 下载
python C:\FengProj\Search-King\scraper.py "风景" --download -o pics

# 手动模式
python C:\FengProj\Search-King\scraper.py --url "https://example.com" --manual

# 雪球抓取（opencli 真实浏览器绕过 WAF）
python C:\FengProj\Search-King\scraper.py --backend opencli --fetch xueqiu --user-id 3300065034

# B站视频列表抓取
python C:\FengProj\Search-King\scraper.py --backend opencli --fetch bilibili --mid 473168952

# B站全部音频下载（低质量，讲课足够）
python C:\FengProj\Search-King\scraper.py --backend opencli --fetch bilibili --mid 473168952 --audio

# B站按合集分类（含全部视频顺序）
python C:\FengProj\Search-King\scraper.py --backend opencli --fetch bilibili --mid 473168952 --series
```

## 接力规则

| 状况 | 我做什么 | 你做什么 |
|------|---------|---------|
| OK 引擎出结果 | 自动提取 | 等结果 |
| 人机验证/拦截 | 跳过，换下一个引擎 | 等结果 |
| **所有引擎全挂** | **切手动模式，浏览器保持打开** | **自己搜 → 按 Enter 我提取** |
| **读网页遇验证码** | **切手动模式，等你处理** | **处理验证码 → 按 Enter 我提取** |
| 手动模式 (-m) | 等你浏览完按回车 | 自己逛 -> 回车 |
| 下载失败 | 提示防盗链 | 手动打开链接 |
