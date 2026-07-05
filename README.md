# 🏆 Super Invincible Human-AI Collaborative Image Search King

**超级无敌人机协作AI搜图大王**

> 10+ search engines · 4 free-to-use stock photography sites · Concurrent downloads · License-aware source docs · One-pass diversity dedup

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-powered-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A Playwright-based relay image scraper that chains 10+ image sources, handles CAPTCHAs gracefully, downloads concurrently with license tracking, and generates provenance documents — **all in ~5 seconds**.

```bash
# 🔍 Free stock photos first (Unsplash → Pexels → Pixabay → Burst)
imgking "dog" --free --download -o pics -n 10

# 🌐 All engines including search index fallback
imgking "风景" --download -o pics -n 20

# 🎯 Pick your engines
imgking "猫" -e unsplash,pixabay,baidu --download -o cat-pics
```

---

## ✨ Features

| Capability | Description |
|-----------|-------------|
| **10+ Engines** | Unsplash, Pexels, Pixabay, Burst, Bing, Google, Baidu, Yandex, DuckDuckGo, Brave, Sogou, 360 |
| **License-Aware** | ✅ Free-to-use sites tagged with license; ⚠️ Search engines marked as "verify before use" |
| **Source Docs** | Every download generates `_sources_{timestamp}.json` with URL, domain, engine, and license per image |
| **Smart Dedup** | URL dedup + title similarity filter (max 2 per similar title group) for visual diversity |
| **Concurrent DL** | 5-thread parallel downloads — one slow URL won't block the rest |
| **Auto-Fallback** | CAPTCHA? Blocked? Skips silently and tries the next engine |
| **Manual Mode** | `--manual` opens browser for you to browse; press Enter and I extract |
| **5 Second Ready** | Optimized for speed — default 5 images in ~5 seconds |

## 🚀 Usage

```bash
# Default chain: free sites first, search engines as fallback
imgking "golden retriever"

# Free-only mode (safe to use commercially)
imgking "golden retriever" --free --download -o photos

# All engines, 30 images
imgking "山水" --download -o wallpapers -n 30

# Single engine
imgking "puppy" -e unsplash --download

# Crawl any webpage
imgking --url "https://example.com/gallery" --download -o gallery

# Manual interactive mode
imgking --url "https://pixiv.net" --manual
```

## 🔧 Engines & Licensing

| Key | Engine | License | Region |
|-----|--------|---------|--------|
| `unsplash` | **Unsplash** | ✅ Free for commercial use | 🌍 |
| `pexels` | **Pexels** | ✅ Free for commercial use | 🌍 |
| `pixabay` | **Pixabay** | ✅ Free for commercial use | 🌍 |
| `burst` | **Burst (Shopify)** | ✅ Free for commercial use | 🌍 |
| `bing` | Bing Images | ⚠️ Unknown — verify rights | 🌍 |
| `baidu` | Baidu Images | ⚠️ Unknown — verify rights | 🇨🇳 |
| `brave` | Brave Search | ⚠️ Unknown — verify rights | 🌍 |
| `ddg` | DuckDuckGo | ⚠️ Unknown — verify rights | 🌍 |
| `yandex` | Yandex Images | ⚠️ Unknown — verify rights | 🇷🇺 |
| `sogou` | Sogou Images | ⚠️ Unknown — verify rights | 🇨🇳 |
| `so360` | 360 Images | ⚠️ Unknown — verify rights | 🇨🇳 |
| `google` | Google Images | ⚠️ Unknown — verify rights (easily blocked) | 🌍 |

Custom engine chain:
```bash
imgking "猫" -e unsplash,pixabay,baidu,brave
```

### 📄 Source Document Example

```json
{
  "query": "golden retriever",
  "generated_at": "2026-07-06T03:34:15+0800",
  "engines_used": ["Unsplash", "Pexels", "Pixabay"],
  "images": [
    {
      "filename": "01_golden_retriever_abc123.jpg",
      "source_url": "https://images.unsplash.com/photo-xxx",
      "source_domain": "images.unsplash.com",
      "engine": "Unsplash",
      "license": "✅ Unsplash License — free for commercial use, no attribution required"
    }
  ]
}
```

## ⚙️ How It Works

```
User Input → Engine Chain → Try Engine 1 → CAPTCHA? → Skip → Try Engine 2
                                                              ↓
                                                        Found images?
                                                              ↓
                                              ┌──────────────────┐
                                              │  URL dedup        │
                                              │  Title diversity  │
                                              │  (max 2 per group)│
                                              └────────┬─────────┘
                                                       ↓
                                              ┌──────────────────┐
                                              │  Parallel DL (5x) │
                                              │  Source docs gen  │
                                              └──────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.8+
- [Playwright](https://playwright.dev/) with Chromium

### 30-Second Install

**Linux / macOS:**
```bash
# 1. Clone and install
git clone https://github.com/fengyuwang-com/Super-Invincible-Image-Search-King.git
cd Super-Invincible-Image-Search-King
pip install playwright
playwright install chromium

# 2. One-liner: make `imgking` available anywhere
mkdir -p ~/bin
echo '#!/usr/bin/env bash
exec python "$(dirname "$0")/../Super-Invincible-Image-Search-King/scraper.py" "$@"' > ~/bin/imgking
chmod +x ~/bin/imgking

# 3. Done! Try it:
imgking "cat" --free -n 3
```

**Windows (Git Bash):**
```bash
# 1. Clone and install
git clone https://github.com/fengyuwang-com/Super-Invincible-Image-Search-King.git
cd Super-Invincible-Image-Search-King
pip install playwright
playwright install chromium

# 2. Make `imgking` available anywhere
mkdir -p ~/bin
echo '#!/usr/bin/env bash
exec python /c/Users/$USER/Super-Invincible-Image-Search-King/scraper.py "$@"' > ~/bin/imgking

# 3. Done! Try it:
imgking "cat" --free -n 3
```

> 💡 **`~/bin` not in PATH?** Add `export PATH="$HOME/bin:$PATH"` to your `~/.bashrc` or `~/.zshrc`.

### Quick re-install (if you already have the repo)
```bash
git pull && pip install --upgrade playwright
```

### Verify it works
```bash
imgking "puppy" --free --download -o my-first-pics
ls my-first-pics/  # you should see images + _sources_*.json
```

## 🤝 Contributing

PRs welcome! Ideas:
- Add more free photo sites (freepik, vecteezy, etc.)
- AI-based image dedup (CLIP embeddings)
- GUI selector (click to pick which images to download)

## 📜 License

MIT — go wild.
