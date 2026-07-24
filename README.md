# 🏆 Search King

> Playwright 驱动的全能搜索器 — 搜图 · 搜文字 · 读网页 · 深度爬取 · 反爬网站抓取。
> CAPTCHA 自动跳过，引擎链自动回退，真人浏览模式兜底。

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-powered-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

---

## 正交参数

参数按职责正交组合，互不干扰：

| 维度 | 参数 | 说明 |
|------|------|------|
| 🎯 **行为** | `--search "x"` | 文字搜索 |
| | `--read URL [URL2 ...]` | 读网页（支持多个并行） |
| | `--crawl URL [URL2 ...]` | 深度爬取 → Markdown |
| | `--fetch xueqiu/bilibili` | 特定平台抓取（需 `--backend opencli`） |
| | `(无，直接输关键词)` | 默认：搜图 |
| 🧠 **后端** | `--backend edge`（默认） | 系统 Edge 浏览器 |
| | `--backend chromium` | Playwright 内置 Chromium |
| | `--backend cloak` | CloakBrowser 反检测（过 Cloudflare） |
| | `--backend lite` | 纯 HTTP（仅文字搜索） |
| | `--backend opencli` | 真实 Edge 浏览器（保持会话，抗 WAF） |
| | `--backend manual` | 你浏览我提取 |
| ⚙️ **修饰** | `--free` | 仅免费摄影站 |
| | `--download` / `-d` | 下载图片 |
| | `--engine` / `-e` | 指定引擎 |
| | `--limit` / `-n` | 结果数 |
| | `--output` / `-o` | 输出目录 |
| | `--show` | 显示浏览器窗口 |

**组合规则：** 行为和后端自由搭配，修饰器全局通用。

---

## 用法速查

| 你想... | 执行 |
|--------|------|
| 🖼️ 搜图 | `python scraper.py "猫"` |
| 🖼️ 搜图+免费+下载 | `python scraper.py "猫" --free --download -o pics` |
| 🔎 搜文字 | `python scraper.py --search "AI 2026"` |
| 🔎 搜文字 + 无浏览器 | `python scraper.py --search "AI" --backend lite` |
| 🔎 搜文字 + 反检测 | `python scraper.py --search "AI" --backend cloak` |
| 📖 读网页 | `python scraper.py --read https://example.com` |
| 📖 读多个网页 | `python scraper.py --read URL1 URL2 URL3` |
| 📖 反检测读网页 | `python scraper.py --read URL --backend cloak` |
| 🕷️ 深度爬取 | `python scraper.py --crawl https://example.com` |
| 🤝 手动模式 | `python scraper.py --read URL --backend manual` |

### opencli 真实浏览器抓取（抗 WAF）

| 你想... | 执行 |
|--------|------|
| 📱 雪球帖子 | `python scraper.py --backend opencli --fetch xueqiu --user-id 123` |
| 🎬 B 站视频列表 | `python scraper.py --backend opencli --fetch bilibili --mid 123` |
| 🎬 B 站合集分类 | `python scraper.py --backend opencli --fetch bilibili --mid 123 --series` |
| 🎵 B 站音频下载 | `python scraper.py --backend opencli --fetch bilibili --mid 123 --audio` |
| 📖 绕过 WAF 读网页 | `python scraper.py --backend opencli --read https://example.com` |

---

## 引擎

### 图片（12 个）

| Key | 引擎 | 许可证 | 地区 |
|-----|------|--------|------|
| `unsplash` | **Unsplash** | ✅ 免费商用 | 🌍 |
| `pexels` | **Pexels** | ✅ 免费商用 | 🌍 |
| `pixabay` | **Pixabay** | ✅ 免费商用 | 🌍 |
| `burst` | **Burst (Shopify)** | ✅ 免费商用 | 🌍 |
| `bing` | Bing Images | ⚠️ 未知 | 🌍 |
| `baidu` | 百度图片 | ⚠️ 未知 | 🇨🇳 |
| `brave` | Brave Search | ⚠️ 未知 | 🌍 |
| `ddg` | DuckDuckGo | ⚠️ 未知 | 🌍 |
| `yandex` | Yandex Images | ⚠️ 未知 | 🇷🇺 |
| `sogou` | 搜狗图片 | ⚠️ 未知 | 🇨🇳 |
| `so360` | 360 图片 | ⚠️ 未知 | 🇨🇳 |
| `google` | Google Images | ⚠️ 未知（易拦截） | 🌍 |

### 文字（6 个）

| Key | 引擎 | URL |
|-----|------|-----|
| `bing-web` | Bing Web Search | `bing.com/search` |
| `baidu-web` | 百度搜索 | `baidu.com/s` |
| `google-web` | Google Web | `google.com/search` |
| `ddg-web` | DuckDuckGo | `duckduckgo.com` |
| `brave-web` | Brave Search | `search.brave.com` |
| `sogou-web` | 搜狗搜索 | `sogou.com/web` |

---

## 工作流

```
用户输入
  ├── --read URL → 读网页 → 提取正文
  ├── --search   → 文字引擎链（全挂→手动模式兜底）
  ├── --crawl    → Crawl4AI 深度提取 → Markdown
  ├── --backend opencli → 真实浏览器绕过 WAF
  └── (默认)     → 图片引擎链 → 去重 → 展示/下载 → 来源文档
```

全部模式遇到验证码/拦截 → 自动跳过换下一个 → 全挂切手动。

---

## 安装

```bash
git clone https://github.com/fengyuwang-com/Super-Invincible-Search-King.git
cd Super-Invincible-Search-King

# 核心依赖（搜图/搜文字/读网页）
pip install playwright
playwright install chromium

# 可选扩展
pip install crawl4ai        # --crawl 深度爬取
pip install cloakbrowser    # --backend cloak 反检测
npm install -g opencli      # --backend opencli WAF 绕过
pip install yt-dlp          # B 站音频下载
```

---

## 许可证

GNU General Public License v3.0
