# 🏆 Super Invincible Search King

**超级无敌人机协作万能搜索大王**

> Playwright 驱动的实体浏览器搜索器 — 搜图 · 搜文字 · 读网页。CAPTCHA 自动跳过，引擎链自动回退，真人浏览模式兜底。

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-powered-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

三种模式，一个脚本：

| 模式 | 命令 | 用途 |
|------|------|------|
| 🔍 **搜图** | `imgking "猫"` | 12 个图片引擎自动链，免费摄影站优先 |
| 🔎 **搜文字** | `imgking --search "AI 2026"` | 6 个搜索引擎，标题+链接+摘要 |
| 📖 **读网页** | `imgking --read https://...` | 打开任意网页提取正文 |
| 🤝 **手动模式** | `imgking --url https://... --manual` | 你浏览我提取 |

```bash
# 🔍 搜图 — 免费摄影站 → 通用搜索兜底
imgking "golden retriever" --free --download -o pics

# 🔎 搜文字 — 6 引擎链
imgking --search "B站封面设计 高点击" --limit 10

# 📖 读网页 — 正文提取
imgking --read "https://example.com/article"
```

---

## ✨ 能力

| 能力 | 说明 |
|------|------|
| **搜图引擎** | Unsplash, Pexels, Pixabay, Burst, Bing, Baidu, Google, Yandex, DuckDuckGo, Brave, Sogou, 360 |
| **文字搜索引擎** | Bing Web, Baidu Web, Google Web, DuckDuckGo Web, Brave Web, Sogou Web |
| **读网页** | 打开任意 URL 提取正文（标题 + 正文字数 + 内容） |
| **许可证感知** | 免费摄影站标记 ✅，通用搜索引擎标记 ⚠️ |
| **来源文档** | `--download` 自动生成 `_sources_{timestamp}.json`，含 URL、引擎、许可证 |
| **去重** | URL 去重 + 标题相似度过滤 |
| **并发下载** | 5 线程并行下载 |
| **自动回退** | CAPTCHA / 被墙 / 403 → 自动跳过换下一个引擎 |
| **手动模式** | `--manual` 弹浏览器给你操作，按回车后提取 |

## 🚀 使用

```bash
# 搜图（默认）
imgking "golden retriever"

# 仅免费摄影站（可商用）
imgking "golden retriever" --free --download -o photos

# 指定引擎
imgking "猫" -e unsplash,pixabay

# 文字搜索
imgking --search "latest AI news 2026" -n 10

# 读网页
imgking --read "https://example.com/article"

# 扒任意网页图片
imgking --url "https://example.com/gallery" --download

# 手动模式
imgking --url "https://pixiv.net" --manual
```

## 🔧 引擎

### 图片引擎

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
| `google` | Google Images | ⚠️ 未知 (易拦截) | 🌍 |

### 文字搜索引擎

| Key | 引擎 | URL |
|-----|------|-----|
| `bing-web` | Bing Web Search | `bing.com/search` |
| `baidu-web` | 百度搜索 | `baidu.com/s` |
| `google-web` | Google Web | `google.com/search` |
| `ddg-web` | DuckDuckGo | `duckduckgo.com` |
| `brave-web` | Brave Search | `search.brave.com` |
| `sogou-web` | 搜狗搜索 | `sogou.com/web` |

## 📦 安装

### 前置依赖
- Python 3.8+
- Playwright + Chromium

```bash
# 1. 克隆
git clone https://github.com/fengyuwang-com/Super-Invincible-Search-King.git
cd Super-Invincible-Search-King

# 2. 安装依赖
pip install playwright
playwright install chromium

# 3. 配置 imgking 快捷命令（可选）
mkdir -p ~/bin
echo '#!/usr/bin/env bash
exec python "$(dirname "$0")/../Super-Invincible-Search-King/scraper.py" "$@"' > ~/bin/imgking
chmod +x ~/bin/imgking

# 4. 试试
imgking "cat" --free -n 3
```

> **`~/bin` 不在 PATH 里？** 加 `export PATH="$HOME/bin:$PATH"` 到 `~/.bashrc` 或 `~/.zshrc`。

## ⚙️ 工作流

```
用户输入
  ├── --read URL → 打开网页 → 提取正文 → 打印
  ├── --search   → 文字引擎链 → 提取标题+链接+摘要 → 打印
  └── (默认)     → 图片引擎链 → CAPTCHA? → 跳过 → 下一个
                                     ↓
                               搜到图片? → URL去重 → 下载 → 来源文档
```

## 🤝 贡献

PR 欢迎！方向：
- 更多免费摄影站
- AI 去重（CLIP embedding）
- 结果预览 / GUI 选择器

## 📜 许可证

GNU General Public License v3.0
