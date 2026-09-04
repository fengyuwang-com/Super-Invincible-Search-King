# Search King

> 多源并发聚合搜索引擎 — 搜图 · 搜文字 · 读网页 · 深度爬取。
> 零 API Key、零 Docker、开箱即用。

> **官网：** https://fengyuwang.com/zh-cn/search-king.html

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

## 快速开始

```bash
pip install playwright crawl4ai
playwright install chromium

# 搜文字（4 源并发合并）
python scraper.py --search "AI 怎么接搜索引擎"

# 搜图
python scraper.py "风景"

# 读网页
python scraper.py --read https://example.com
```

## 正交参数

| 维度 | 参数 | 说明 |
|------|------|------|
| 🎯 行为 | `--search "x"` | 文字搜索（4 源并发合并） |
| | `--read URL` | 读网页（支持多 URL 并行） |
| | `--crawl URL` | 深度爬取 → Markdown |
| | `--fetch xueqiu/bilibili` | 特定平台抓取（需 `--backend opencli`） |
| | 无参数 | 搜图 |
| 🧠 后端 | `--backend edge`（默认） | 系统 Edge 浏览器 |
| | `--backend chromium` | Playwright Chromium |
| | `--backend cloak` | CloakBrowser 反检测 |
| | `--backend lite` | 纯 HTTP（仅文字搜索） |
| | `--backend opencli` | 真实 Edge（保持会话） |
| | `--backend manual` | 你浏览我提取 |
| ⚙️ 修饰 | `--deep` | 增强模式（5 跳降级流水线） |
| | `--free` | 仅免费摄影站 |
| | `--download` / `-d` | 下载图片 |
| | `-e engine` | 指定引擎 |
| | `-n 10` | 结果数 |

## 默认文字搜索架构

`--search` 默认调用 `multi_source_search()`，**4 源并发、全部等齐、合并去重**：

```
                    ┌─ baidu_lite_search()  ──┐
query ──→ 并发 ──→ ├─ ddg_lite_search()    ──┤──→ 合并去重 → 输出
                    ├─ tinyfish_search()    ──┤
                    └─ searxng_search()     ──┘   (Google CSE 等)
```

- **百度**：纯 HTTP + 随机 Cookie，中文结果
- **DDG**：`html.duckduckgo.com/html/`，中英文通用
- **TinyFish**：云端 REST API（免费 Search 档）
- **SearXNG**：in-process Flask test_client，聚合 Google CSE / Bing / Wikipedia 等

所有源失败时静默跳过，不阻塞其他源。超时 35s。

### `--deep` 增强模式

显式 `--deep` 走 5 跳降级流水线（多源直连 → 浏览器引擎链 → CloakBrowser → TinyFish → 手动）。

## 图片搜索

12 个引擎：Unsplash / Pexels / Pixabay / Burst（免费商用）→ Bing / Baidu / Brave / DDG / Yandex / Sogou / 360 / Google（通用）。

## 读网页

```bash
python scraper.py --read URL1 URL2 URL3         # 多 URL 并行
python scraper.py --read URL --backend cloak     # 反检测模式
python scraper.py --read URL --backend lite      # 纯 HTTP
```

## 安装

```bash
git clone https://github.com/fengyuwang-com/Super-Invincible-Search-King.git
cd Super-Invincible-Search-King

# 核心
pip install playwright
playwright install chromium

# 可选
pip install crawl4ai       # --crawl 深度爬取
pip install cloakbrowser   # --backend cloak
pip install searxng        # SearXNG 元搜索（in-process）
npm install -g opencli     # --backend opencli
pip install yt-dlp         # B 站音频
```

## 许可证

GNU General Public License v3.0
