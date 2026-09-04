#!/usr/bin/env python3
"""
接力爬虫 — 人机协作的万能搜索器
================================

核心能力：用真实浏览器绕过反爬，搜图 + 搜文字 + 读网页

我能干的：
  🔍 搜图    — 10+ 引擎链，自动跳过验证码，免费摄影站优先
  🔎 搜文字  — 6 个搜索引擎，提取标题+链接+摘要
  📖 读网页  — 打开任意 URL 提取正文
  🤝 手动模式 — 你浏览我提取

使用示例：

    # 搜图（默认）
    python scraper.py "猫"

    # 搜文字
    python scraper.py --search "B站封面设计技巧"

    # 读网页
    python scraper.py --read "https://example.com/article"

    # 扒任意网页的图
    python scraper.py --url "https://example.com/gallery"

    # 手动模式
    python scraper.py --url "https://example.com" --manual

    # 搜图 + 下载
    python scraper.py "狗" --download -o pics
"""

import asyncio, json, os, sys, argparse, urllib.request, urllib.parse, re, time, hashlib, concurrent.futures
from pathlib import Path

# CloakBrowser — 可选的反检测浏览器
_CLOAK_AVAILABLE = False
try:
    from cloakbrowser import launch as cloak_launch
    _CLOAK_AVAILABLE = True
except ImportError:
    pass

sys.stdout.reconfigure(encoding='utf-8')

# Crawl4AI — 深度网页转 Markdown（可选）
_CRAWL4AI_AVAILABLE = False
try:
    from crawl4ai import AsyncWebCrawler
    _CRAWL4AI_AVAILABLE = True
except ImportError:
    pass

from playwright.async_api import async_playwright, TimeoutError

# ── opencli 浏览器抓取插件（可选）──
_OPENCLI_AVAILABLE = False
try:
    from . import scraper_fetch as opencli_fetch
    _OPENCLI_AVAILABLE = True
except ImportError:
    try:
        import scraper_fetch as opencli_fetch
        _OPENCLI_AVAILABLE = True
    except ImportError:
        pass


# ============================================================
# 搜索引擎 & 免费图库配置
# ============================================================

# 许可证说明
LICENSE_UNKNOWN = "⚠️ 未知 — 搜索引擎来源，版权归属不明，请自行核实能否商用"
LICENSE_UNSPLASH = "✅ Unsplash License — 免费商用，无需署名"
LICENSE_PEXELS = "✅ Pexels License — 免费商用，无需署名"
LICENSE_PIXABAY = "✅ Pixabay License — 免费商用，无需署名"
LICENSE_BURST = "✅ Burst (Shopify) License — 免费商用，无需署名"

ENGINES = {
    # --- 免费摄影站（优先使用）---
    "unsplash": {
        "name": "Unsplash",
        "url": "https://unsplash.com/s/photos/{q}",
        "license": LICENSE_UNSPLASH,
        "extract": "(()=>{const r=[]; document.querySelectorAll('img[src*=\"images.unsplash.com\"]').forEach(img=>{const s=img.src||''; if(s.startsWith('http')&&img.naturalWidth>50) r.push({url:s,title:img.alt||''})}); return r;})()",
    },
    "pexels": {
        "name": "Pexels",
        "url": "https://www.pexels.com/search/{q}/",
        "license": LICENSE_PEXELS,
        "extract": "(()=>{const r=[]; document.querySelectorAll('img[src*=\"pexels.com\"], img[srcset]').forEach(img=>{const s=img.getAttribute('data-src')||img.src||''; if(s.startsWith('http')&&img.naturalWidth>50) r.push({url:s,title:img.alt||''})}); return r;})()",
    },
    "pixabay": {
        "name": "Pixabay",
        "url": "https://pixabay.com/images/search/{q}/",
        "license": LICENSE_PIXABAY,
        "extract": "(()=>{const r=[]; document.querySelectorAll('img[src*=\"pixabay.com\"]').forEach(img=>{const s=img.getAttribute('data-lazy-src')||img.src||''; if(s.startsWith('http')&&img.naturalWidth>50) r.push({url:s,title:img.alt||''})}); return r;})()",
    },
    "burst": {
        "name": "Burst (Shopify)",
        "url": "https://burst.shopify.com/search?q={q}",
        "license": LICENSE_BURST,
        "extract": "(()=>{const r=[]; document.querySelectorAll('img[src*=\"burst.shopify.com\"]').forEach(img=>{const s=img.src||''; if(s.startsWith('http')&&img.naturalWidth>50) r.push({url:s,title:img.alt||img.title||''})}); return r;})()",
    },
    # --- 通用搜索引擎（版权未知）---
    "bing": {
        "name": "Bing Images",
        "url": "https://www.bing.com/images/search?q={q}&form=HDRSC2",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('.iusc').forEach(el => {
                    try {
                        const m = JSON.parse(el.getAttribute('m'));
                        if (m && m.murl) r.push({url: m.murl, title: m.t||'', thumb: m.turl||''});
                    } catch(e) {}
                });
                return r;
            })()
        """,
    },
    "google": {
        "name": "Google Images",
        "url": "https://www.google.com/search?q={q}&tbm=isch",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('img.rg_i, img[data-src]').forEach(img => {
                    const src = img.getAttribute('data-src') || img.src || '';
                    if (src.startsWith('http') && img.naturalWidth > 50)
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
    "baidu": {
        "name": "百度图片",
        "url": "https://image.baidu.com/search/index?tn=baiduimage&word={q}",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('img.main_img').forEach(img => {
                    const src = img.getAttribute('data-imgurl') || img.src || '';
                    if (src.startsWith('http'))
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
    "yandex": {
        "name": "Yandex Images",
        "url": "https://yandex.com/images/search?text={q}",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('img[src*="https://"]').forEach(img => {
                    const src = img.src || '';
                    if (src.startsWith('http') && !src.includes('yandex') && img.naturalWidth > 50)
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
    "ddg": {
        "name": "DuckDuckGo Images",
        "url": "https://duckduckgo.com/?q={q}&iax=images&ia=images",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('.tile--img__img, img[data-src]').forEach(img => {
                    const src = img.getAttribute('data-src') || img.src || '';
                    if (src.startsWith('http'))
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
    "brave": {
        "name": "Brave Image Search",
        "url": "https://search.brave.com/images?q={q}",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('img').forEach(img => {
                    const src = img.src || '';
                    if (src.startsWith('http') && img.naturalWidth > 50)
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
    "sogou": {
        "name": "搜狗图片",
        "url": "https://pic.sogou.com/pics?query={q}",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('img').forEach(img => {
                    const src = img.getAttribute('data-src') || img.src || '';
                    if (src.startsWith('http') && img.naturalWidth > 50)
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
    "so360": {
        "name": "360图片",
        "url": "https://image.so.com/i?q={q}",
        "license": LICENSE_UNKNOWN,
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('img[data-src], img[src]').forEach(img => {
                    const src = img.getAttribute('data-src') || img.src || '';
                    if (src.startsWith('http') && img.naturalWidth > 50)
                        r.push({url: src, title: img.alt||''});
                });
                return r;
            })()
        """,
    },
}

# 默认引擎链：免费摄影站优先，搜索引擎兜底
FALLBACK_CHAIN = ["unsplash", "pexels", "pixabay", "burst", "bing", "baidu", "brave", "ddg", "sogou", "so360"]
FREE_SITE_KEYS = ["unsplash", "pexels", "pixabay", "burst"]

# ============================================================
# 文字搜索引擎配置（--search 模式）
# ============================================================

TEXT_ENGINES = {
    "bing-web": {
        "name": "Bing Web",
        "url": "https://www.bing.com/search?q={q}&form=QBLH",
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('#b_results .b_algo').forEach(el => {
                    const link = el.querySelector('h2 a');
                    const snippet = el.querySelector('.b_caption p, .b_lineclamp2');
                    if (link) r.push({
                        title: (link.innerText || '').trim(),
                        url: link.href || '',
                        snippet: snippet ? (snippet.innerText || '').trim() : ''
                    });
                });
                return r;
            })()
        """,
    },
    "baidu-web": {
        "name": "百度搜索",
        "url": "https://www.baidu.com/s?wd={q}",
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('#content_left .result, #content_left .result-op').forEach(el => {
                    const link = el.querySelector('h3 a');
                    const snippet = el.querySelector('.c-abstract, .c-span-last, .content-right_8Zs40');
                    if (link) r.push({
                        title: (link.innerText || '').trim(),
                        url: link.href || '',
                        snippet: snippet ? (snippet.innerText || '').trim() : ''
                    });
                });
                return r;
            })()
        """,
    },
    "google-web": {
        "name": "Google Web",
        "url": "https://www.google.com/search?q={q}&hl=zh-CN",
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('div.g, div[data-hveid]').forEach(el => {
                    const link = el.querySelector('a[href^="http"]');
                    const snippet = el.querySelector('.VwiC3b, .lEBKkf, span.aCOpRe');
                    if (link && link.href && !link.href.includes('google.com')) r.push({
                        title: (link.innerText || '').trim(),
                        url: link.href,
                        snippet: snippet ? (snippet.innerText || '').trim() : ''
                    });
                });
                return r;
            })()
        """,
    },
    "ddg-web": {
        "name": "DuckDuckGo",
        "url": "https://html.duckduckgo.com/html/?q={q}",
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('.result').forEach(el => {
                    const link = el.querySelector('a.result__a');
                    const snippet = el.querySelector('.result__snippet');
                    if (link) r.push({
                        title: (link.innerText || '').trim(),
                        url: link.href || '',
                        snippet: snippet ? (snippet.innerText || '').trim() : ''
                    });
                });
                return r;
            })()
        """,
    },
    "brave-web": {
        "name": "Brave Search",
        "url": "https://search.brave.com/search?q={q}",
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('.snippet, [data-type="web"]').forEach(el => {
                    const link = el.querySelector('a[href]');
                    const snippet = el.querySelector('.snippet-description, .description');
                    if (link && link.href && !link.href.startsWith('javascript:')) r.push({
                        title: (link.innerText || '').trim(),
                        url: link.href,
                        snippet: snippet ? (snippet.innerText || '').trim() : ''
                    });
                });
                return r;
            })()
        """,
    },
    "sogou-web": {
        "name": "搜狗搜索",
        "url": "https://www.sogou.com/web?query={q}",
        "extract": """
            (() => {
                const r = [];
                document.querySelectorAll('.vrwrap, .result').forEach(el => {
                    const link = el.querySelector('h3 a, .vr-title a');
                    const snippet = el.querySelector('.str-text, .star-wiki, .text-l');
                    if (link) r.push({
                        title: (link.innerText || '').trim(),
                        url: link.href || '',
                        snippet: snippet ? (snippet.innerText || '').trim() : ''
                    });
                });
                return r;
            })()
        """,
    },
}

# 默认文字搜索链
# 2026-08-05 实测: brave-web 快且稳(默认主力); ddg-web 能用但慢(~50s);
# bing-web/google-web 在无头下会卡死(>90s); baidu/sogou 秒回但常遇验证码。
# 慢引擎一律不进默认链; 需要时用 -e ddg-web 等手动指定。
# 每个引擎另有独立超时 TEXT_SEARCH_TIMEOUT, 防止单引擎拖死整轮搜索。
TEXT_FALLBACK_CHAIN = ["ddg-web", "sogou-web", "brave-web", "baidu-web"]
TEXT_SEARCH_TIMEOUT = 60  # 单个文字引擎最长等待(秒), 超时自动放弃(ddg 约50s需留余量)
TIMEOUT_SENTINEL = object()  # 引擎超时哨兵(区别于"无结果")


def detect_captcha(text):
    """检测页面是否被人机验证挡住"""
    keywords = [
        "verify", "captcha", "recaptcha", "challenge", "robot",
        "verify you're human", "not a robot", "验证", "人机验证",
        "安全验证", "请完成安全验证", "unusual traffic",
    ]
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return True
    return False


def detect_blocked(text):
    """检测是否被屏蔽/拦截"""
    keywords = [
        "please click here if you are not redirected",
        "we're sorry", "access denied", "403 forbidden",
        "our systems have detected unusual traffic",
        "this page could not be loaded",
    ]
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return True
    return False


async def wait_for_user_input(page, prompt_msg, check_closed=True):
    """等待用户操作（Windows 兼容）。返回 False 表示浏览器已关闭或应退出手动模式。
    非交互环境（管道/重定向/CI，stdin 为 EOF）下直接跳过，防止无限空转刷屏。"""
    if not sys.stdin.isatty():
        print("   ⏭️ 非交互环境（stdin 非终端），跳过手动模式", flush=True)
        return False
    print(f"\n🟡 {prompt_msg}", flush=True)
    print("   操作完成后在终端按 Enter 继续...", flush=True)
    loop = asyncio.get_event_loop()
    while True:
        # 首先检测浏览器是否还活着
        if check_closed:
            try:
                _ = await page.title()
            except:
                print("   🔴 浏览器已关闭", flush=True)
                return False

        # 用 run_in_executor 等待用户按 Enter（非阻塞事件循环）
        done, pending = await asyncio.wait(
            [loop.run_in_executor(None, sys.stdin.readline)],
            timeout=0.5
        )
        if pending:
            for t in pending:
                t.cancel()  # 清理未完成的等待任务, 防止线程池堆积
            try:
                await asyncio.gather(*pending, return_exceptions=True)  # 收敛已取消任务, 消除 "exception was never retrieved"
            except Exception:
                pass
        if done:
            return True


async def extract_images(page, min_size=100, max_count=50):
    """从页面提取图片（通用方法 + 按尺寸过滤排序）"""
    images = await page.evaluate(f"""() => {{
        const r = [];
        // 优先找大图标签
        const selectors = ['img[data-src]', 'img[src*="http"]', 'img'];
        for (const sel of selectors) {{
            document.querySelectorAll(sel).forEach(img => {{
                const src = img.getAttribute('data-src') || img.getAttribute('data-original') ||
                            img.getAttribute('data-url') || img.src || '';
                if (src && src.startsWith('http') && img.naturalWidth > {min_size}) {{
                    r.push({{
                        url: src,
                        title: img.alt || img.title || '',
                        w: img.naturalWidth || img.width,
                        h: img.naturalHeight || img.height,
                    }});
                }}
            }});
            if (r.length > 0) break;
        }}
        // 去重
        const seen = new Set();
        return r.filter(x => {{ if (seen.has(x.url)) return false; seen.add(x.url); return true; }});
    }}""")
    images.sort(key=lambda x: (x.get("w", 0) or 0) * (x.get("h", 0) or 0), reverse=True)
    return images[:max_count]


def download_images(images, output_dir, max_count=5, max_workers=5):
    """并发下载图片，用 URL 哈希保证文件名唯一"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []

    def dl_one(i, img):
        title = re.sub(r'[<>:"/\\|?*]', '', (img.get("title") or "")[:40]) or f"image_{i+1}"
        url_hash = hashlib.md5(img["url"].encode()).hexdigest()[:6]
        fname = f"{i+1:02d}_{title}_{url_hash}.jpg"
        fpath = out / fname
        try:
            req = urllib.request.Request(img["url"], headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                with open(fpath, "wb") as f:
                    f.write(resp.read())
            print(f"  [DL] ✅ {fname}", flush=True)
            return {"file": str(fpath), "ok": True}
        except Exception as e:
            print(f"  [DL] ❌ {fname}: {str(e)[:50]}", flush=True)
            return {"file": img["url"], "ok": False, "error": str(e)[:50]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(dl_one, i, img) for i, img in enumerate(images[:max_count])]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    return results


def write_source_doc(images, dl_results, output_dir, query, engines_used):
    """生成来源文档 _sources_{时间戳}.json，标注每张图的出处和许可证"""
    out = Path(output_dir)
    entries = []

    # 建立 URL hash → image 元数据的映射
    img_by_hash = {}
    for img in images:
        h = hashlib.md5(img["url"].encode()).hexdigest()[:6]
        img_by_hash[h] = img

    for dl in dl_results:
        if not dl.get("ok"):
            continue
        fname = Path(dl["file"]).name
        # 从文件名中提取 hash（最后6位 .jpg 前）
        hash_in_name = fname.replace(".jpg", "")[-6:]
        img = img_by_hash.get(hash_in_name)
        if not img:
            continue
        eng = img.get("_engine", "?")
        lic = img.get("_license", "?")
        entries.append({
            "filename": fname,
            "source_url": img["url"],
            "source_domain": urllib.parse.urlparse(img["url"]).netloc,
            "engine": ENGINES[eng]["name"] if eng in ENGINES else eng,
            "license": lic,
            "downloaded_ok": True,
        })

    doc = {
        "query": query,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "engines_used": [ENGINES.get(e, {}).get("name", e) for e in engines_used],
        "total_downloaded": len(entries),
        "disclaimer": "来源搜索引擎的图片版权归属未知，请自行核实能否商用；免费摄影站的图片按对应许可证使用。",
        "images": entries,
    }

    ts = time.strftime("%Y%m%d_%H%M%S")
    doc_path = out / f"_sources_{ts}.json"
    try:
        with open(doc_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"\n📄 来源文档: {doc_path}", flush=True)
    except Exception as e:
        print(f"   ⚠️ 来源文档写入失败: {e}", flush=True)


async def try_engine(page, eng, query, min_size, max_count):
    """尝试一个图片搜索引擎。成功返回带标记的图片列表，失败返回 None。"""
    info = ENGINES[eng]
    page_url = info["url"].format(q=urllib.parse.quote(query))
    print(f"\n🔵 [{info['name']}] {query}", flush=True)

    try:
        await page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"   ⚠️ 导航失败: {str(e)[:50]}", flush=True)
        return None

    await page.wait_for_timeout(3000)

    # 检测验证码/拦截
    page_text = await page.inner_text("body") if await page.query_selector("body") else ""
    if detect_captcha(page_text):
        print(f"   🤖 CAPTCHA，跳过", flush=True)
        return None
    if detect_blocked(page_text):
        print(f"   🚫 被拦截，跳过", flush=True)
        return None

    # 滚动加载
    print("   ⏳ 加载中...", flush=True)
    for i in range(5):
        await page.evaluate("window.scrollBy(0, 600)")
        await page.wait_for_timeout(1000)

    # 引擎专用提取
    images = await page.evaluate(info["extract"])

    # 没出图？走通用提取
    if not images:
        print("   ⚠️ 引擎提取没拿到，尝试通用方法...", flush=True)
        images = await extract_images(page, min_size, max_count)

    # 引擎专用提取没带宽高的，补一次尺寸探测：优先读页面里已加载 img 的 naturalWidth，取不到再用 new Image 拉一次
    if images and not images[0].get("w"):
        try:
            sizes = await page.evaluate("""(urls) => Promise.all(urls.map(u => new Promise(res => {
                const el = [...document.images].find(i => (i.src || i.getAttribute('data-src') || '') === u);
                if (el && el.naturalWidth) { res({url: u, w: el.naturalWidth, h: el.naturalHeight}); return; }
                const im = new Image();
                const done = v => res({url: u, w: v ? im.naturalWidth : 0, h: v ? im.naturalHeight : 0});
                im.onload = () => done(true);
                im.onerror = () => done(false);
                setTimeout(() => done(false), 5000);
                im.src = u;
            })))""", [img["url"] for img in images])
            smap = {s["url"]: s for s in sizes}
            for img in images:
                s = smap.get(img["url"])
                if s and s["w"]:
                    img["w"], img["h"] = s["w"], s["h"]
        except Exception as e:
            print(f"   ⚠️ 尺寸探测失败: {str(e)[:50]}", flush=True)

    # 给每张图打上来源标记
    for img in images:
        img["_engine"] = eng
        img["_license"] = info.get("license", LICENSE_UNKNOWN)

    return images


async def try_text_engine(page, eng, query, max_count):
    """尝试一个文字搜索引擎。成功返回 [{title, url, snippet}]，失败返回 None。"""
    info = TEXT_ENGINES[eng]
    page_url = info["url"].format(q=urllib.parse.quote(query))
    print(f"\n🔵 [{info['name']}] {query}", flush=True)

    try:
        await page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"   ⚠️ 导航失败: {str(e)[:50]}", flush=True)
        return None

    await page.wait_for_timeout(3000)

    # 检测验证码/拦截
    page_text = await page.inner_text("body") if await page.query_selector("body") else ""
    if detect_captcha(page_text):
        print(f"   🤖 CAPTCHA，跳过", flush=True)
        return None
    if detect_blocked(page_text):
        print(f"   🚫 被拦截，跳过", flush=True)
        return None

    # 引擎专用提取
    results = await page.evaluate(info["extract"])

    # DDG 的链接是 duckduckgo.com/l/?uddg= 跳转，解码回真实 URL
    for r in (results or []):
        u = r.get("url", "")
        if "duckduckgo.com/l/" in u:
            m = urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("uddg")
            if m:
                r["url"] = m[0]

    # 没出结果？走通用兜底
    if not results:
        print("   ⚠️ 引擎提取没拿到，尝试通用方法...", flush=True)
        results = await extract_search_results(page, max_count)

    return (results or [])[:max_count]


async def extract_search_results(page, max_count=20):
    """通用兜底：提取当前页面中看起来像搜索结果的条目"""
    results = await page.evaluate(f"""() => {{
        const r = [];
        // 所有链接
        document.querySelectorAll('a[href]').forEach(a => {{
            const href = a.href;
            const text = (a.innerText || '').trim();
            if (text.length > 8 && href.startsWith('http') && !href.includes(window.location.host)) {{
                // 找父容器里的摘要
                const parent = a.closest('li, div, section, article');
                const snippet = parent ? (parent.innerText || '').replace(text, '').trim().slice(0, 200) : '';
                r.push({{ title: text.slice(0, 120), url: href, snippet: snippet.slice(0, 200) }});
            }}
        }});
        return r.slice(0, {max_count});
    }}""")
    return results


async def extract_page_content(page):
    """提取当前页面的正文内容"""
    content = await page.evaluate("""() => {
        // 优先语义标签
        const selectors = [
            'article',
            '[role="main"]',
            'main',
            '.post-content',
            '.article-content',
            '.entry-content',
            '#content',
            '.content',
            '.post',
            '.article',
            '#read-content',
            '.markdown-body',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 200) return el.innerText.trim();
        }
        // 兜底：body 文本
        if (document.body) {
            const text = document.body.innerText || '';
            return text.trim().slice(0, 50000);
        }
        return '';
    }""")
    return content


async def run(query=None, engines=None, url=None, max_count=5,
              download=False, output_dir=".", manual=False, min_size=100, free_only=False,
              search=False, read_url=None, browser_choice="edge", headless=True):
    """主循环：搜图 / 搜文字 / 读网页"""

    async with async_playwright() as p:
        # 浏览器选择：edge（真 Edge）vs chromium（Playwright 自带）
        launch_kwargs = dict(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-automation',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-setuid-sandbox',
            ]
        )
        if browser_choice == "edge":
            launch_kwargs["channel"] = "msedge"
            print("🌐 浏览器: Edge（系统安装）", flush=True)
        else:
            print("🌐 浏览器: Chromium（Playwright 自带）", flush=True)
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            permissions=["geolocation"],
            geolocation={"longitude": 121.4737, "latitude": 31.2304},
        )
        # 隐藏自动化痕迹
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            // 覆盖 Chrome 自动化检测
            window.chrome = { runtime: {} };
            // 覆盖权限查询
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (p) => (
                p.name === 'notifications' ? Promise.resolve({state: 'prompt'}) : originalQuery(p)
            );
        """)
        page = await context.new_page()

        # ----- 读网页模式（--read）-----
        if read_url:
            print(f"\n📖 [读网页] {read_url}", flush=True)
            try:
                await page.goto(read_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"   ❌ 打开失败: {str(e)[:80]}", flush=True)
                await browser.close()
                return

            await page.wait_for_timeout(3000)

            if manual:
                return await manual_mode(page, browser, min_size, max_count)

            # 检测验证码/拦截 → 自动切手动模式（循环：你浏览→我提取→你再浏览）
            page_text = await page.inner_text("body") if await page.query_selector("body") else ""
            if detect_captcha(page_text) or detect_blocked(page_text):
                print("\n🟡 遇到验证码/拦截，自动切换手动模式", flush=True)
                print("   浏览器保持打开，你处理验证码/手动浏览到目标内容", flush=True)
                print("   每次按 Enter 我提取当前页，输入 'done' 退出", flush=True)
                while True:
                    ok = await wait_for_user_input(page, "处理完按 Enter 提取内容")
                    if not ok:
                        await browser.close()
                        return
                    content = await extract_page_content(page)
                    if content and len(content) > 100:
                        break
                    print("   ⚠️ 内容太短（可能是验证码页面），继续等你处理", flush=True)

            content = await extract_page_content(page)
            if content:
                lines = content.split('\n')
                title = await page.title()
                print(f"\n📄 标题: {title}", flush=True)
                print(f"📏 字数: {len(content)}", flush=True)
                print(f"{'='*60}", flush=True)
                for line in lines[:200]:
                    print(line, flush=True)
                if len(lines) > 200:
                    print(f"\n... (共 {len(lines)} 行，仅显示前 200 行)", flush=True)
            else:
                print("   ⚠️ 未能提取到正文内容", flush=True)

            await browser.close()
            return

        # ----- 文字搜索模式（--search）-----
        if search:
            if not query:
                print("❌ 文字搜索需要提供 query", flush=True)
                await browser.close()
                return

            text_engines = engines if engines else TEXT_FALLBACK_CHAIN
            text_engines = [e for e in text_engines if e in TEXT_ENGINES]
            if not text_engines:
                print(f"❌ 无效文字引擎: {engines}，可用: {', '.join(TEXT_ENGINES.keys())}", flush=True)
                await browser.close()
                return

            all_results = []

            async def search_one_text(ctx, eng, q, limit):
                """单个文字搜索引擎（独立页面，并发执行）"""
                p = await ctx.new_page()
                try:
                    return eng, await try_text_engine(p, eng, q, limit)
                finally:
                    await p.close()

            tasks = [search_one_text(context, eng, query, max_count) for eng in text_engines]
            gathered = await asyncio.gather(*tasks)

            # 并发发起所有引擎, 谁先出结果谁先得; 出够结果就提前收网, 不等慢引擎
            pending = {asyncio.ensure_future(run_with_timeout(eng, TEXT_SEARCH_TIMEOUT))
                       for eng in text_engines}
            done = set()
            reported = set()
            while pending:
                # 等最早返回的那一个
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for fut in done:
                    # 被我们主动取消的引擎, result 会是 CancelledError, 直接跳过
                    if fut.cancelled():
                        continue
                    eng, result = fut.result()
                    reported.add(eng)
                    if result is TIMEOUT_SENTINEL:
                        print(f"   ⏱️ [{TEXT_ENGINES[eng]['name']}] 超时放弃", flush=True)
                    elif not result:
                        print(f"   ❌ [{TEXT_ENGINES[eng]['name']}] 无结果", flush=True)
                    else:
                        all_results.extend(result)
                        print(f"\n✅ [{TEXT_ENGINES[eng]['name']}] {len(result)} 条结果", flush=True)
                # 已拿到足够结果 → 提前收网, 取消还在跑的引擎
                if len(all_results) >= max_count and pending:
                    for fut in pending:
                        fut.cancel()
                    try:
                        await asyncio.gather(*pending, return_exceptions=True)  # 收敛已取消任务, 消除 ERR_ABORTED 刷屏
                    except Exception:
                        pass
                    print(f"   ⏭️ 已拿到 {len(all_results)} 条(≥{max_count}), 提前结束, 跳过 {len(pending)} 个未完成引擎", flush=True)
                    pending = set()
                    break
                # 记下已处理过的引擎, 凡是被取消的会在 reported 缺失时于下方统一提示
            # 从未完成/被取消的引擎, 记一个超时
            for eng in text_engines:
                if eng not in reported:
                    print(f"   ⏱️ [{TEXT_ENGINES[eng]['name']}] 取消/未完成", flush=True)

            # 所有引擎全挂了 → 手动模式兜底
            if not all_results:
                print(f"\n🟡 全部 {len(text_engines)} 个搜索引擎都挂了（验证码/拦截/无结果）", flush=True)
                manual_results = await manual_text_extract(page, browser, max_count)
                all_results = manual_results or []
            else:
                # 如果自动引擎出了部分结果，问问要不要手动补充
                print(f"\n💡 提示: 想手动补充搜索？用 --manual 再跑一次", flush=True)

            # 去重
            seen = set()
            deduped = []
            for r in all_results:
                if r.get("url") and r["url"] not in seen:
                    seen.add(r["url"])
                    deduped.append(r)

            # 展示
            if deduped:
                print(f"\n{'='*60}", flush=True)
                print(f"📎 共 {len(deduped)} 条结果", flush=True)
                print(f"{'='*60}", flush=True)
                for i, r in enumerate(deduped[:max_count], 1):
                    print(f"\n[{i}] {r.get('title', '')}", flush=True)
                    print(f"    🔗 {r.get('url', '')}", flush=True)
                    if r.get('snippet'):
                        print(f"    💬 {r['snippet'][:150]}", flush=True)
            else:
                print(f"\n{'='*60}", flush=True)
                print("❌ 所有引擎都挂了，也没提取到手动搜索结果", flush=True)
                print(f"{'='*60}", flush=True)

            await browser.close()
            return deduped[:max_count]

        # ----- 图片搜索模式（默认）-----
        # [原有逻辑保持不变]
        images = []
        if url:
            print(f"\n🔵 [导航] 打开网页: {url}", flush=True)
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            if manual:
                return await manual_mode(page, browser, min_size, max_count)

            await page.wait_for_timeout(3000)
            for i in range(5):
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(1000)
            images = await extract_images(page, min_size, max_count)

        # ----- 引擎链模式：全部并发 -----
        elif query and engines:
            async def search_one_image(ctx, eng, q, min_sz, max_cnt):
                p = await ctx.new_page()
                try:
                    return eng, await try_engine(p, eng, q, min_sz, max_cnt)
                finally:
                    await p.close()

            tasks = [search_one_image(context, eng, query, min_size, max_count) for eng in engines]
            gathered = await asyncio.gather(*tasks)

            for eng, result in gathered:
                name = ENGINES[eng]['name']
                if result:
                    images.extend(result)
                    print(f"\n✅ [{name}] {len(result)} 张图", flush=True)
                else:
                    print(f"   ❌ [{name}] 没出图", flush=True)

            # 去重（按URL）
            seen = set()
            deduped = []
            for img in images:
                if img["url"] not in seen:
                    seen.add(img["url"])
                    deduped.append(img)

            # 多样化：标题前20字相似的只留2张，确保不全是同一来源
            title_groups = {}
            diversified = []
            for img in deduped:
                key = re.sub(r'[^一-鿿\w]', '', (img.get("title") or "")[:20]).strip() or "_untitled"
                group = title_groups.get(key, [])
                if len(group) < 2:
                    group.append(img)
                    title_groups[key] = group
                    diversified.append(img)
            images = diversified
            print(f"\n📸 去重后 {len(deduped)} 张 → 多样化筛选 {len(images)} 张", flush=True)

        else:
            print("需要 --query 或 --url", flush=True)
            await browser.close()
            return

        # ----- 全挂了？交给你手动（仅当指定了 --manual）-----
        if not images:
            if manual:
                return await manual_mode(page, browser, min_size, max_count)
            print("\n❌ 没有找到图片", flush=True)
            await browser.close()
            return

        # ----- 展示 & 下载 -----
        show_count = min(len(images), 20)
        print(f"\n📸 共 {len(images)} 张图片 (显示前{show_count}张)", flush=True)
        for i, img in enumerate(images[:show_count]):
            w = img.get("w", "?")
            h = img.get("h", "?")
            t = str(img.get("title", "") or "")[:60]
            print(f"  [{i+1}] [{w}x{h}] {t}", flush=True)
            print(f"       {img['url'][:130]}", flush=True)

        if download:
            print(f"\n📥 下载到 {output_dir}/ ...", flush=True)
            dl_results = download_images(images, output_dir, max_count)
            ok_count = sum(1 for r in dl_results if r.get("ok"))
            fail_count = sum(1 for r in dl_results if not r.get("ok"))
            print(f"\n📥 下载完成: {ok_count} 成功, {fail_count} 失败", flush=True)

            # 生成来源文档
            write_source_doc(images, dl_results, output_dir, query, engines)

            if fail_count > 0:
                print("\n🔒 有些图下载失败（403/404），可能防盗链", flush=True)
                print("   你可以手动在浏览器里打开这些页面", flush=True)

        # ----- 完成，自动退出 -----
        print(f"\n{'='*50}", flush=True)
        print("✅ 完成！", flush=True)
        print(f"{'='*50}", flush=True)

        await browser.close()


async def manual_mode(page, browser, min_size=100, max_count=50):
    """手动模式：你浏览我提取（循环接力）"""
    print("\n🟢 [手动模式] 浏览器归你了", flush=True)
    print("   你去浏览/搜索，操作完后按 Enter，我提取当前页面的图", flush=True)
    print("   输入 'done' 退出，直接 Enter 继续提取", flush=True)
    while True:
        ok = await wait_for_user_input(page, "准备好了？按 Enter 我提取图片，输入 'done' 退出")
        if not ok:
            break
        images = await extract_images(page, min_size, max_count)
        if images:
            print(f"\n📸 当前页找到 {len(images)} 张图片:", flush=True)
            for i, img in enumerate(images[:10]):
                print(f"  [{i+1}] [{img.get('w','?')}x{img.get('h','?')}] {str(img.get('title',''))[:50]}", flush=True)
            print(f"  ...共 {len(images)} 张", flush=True)
        else:
            print("  当前页没有找到大图，换个页面试试？", flush=True)
    await browser.close()
    return []


async def manual_text_extract(page, browser, max_count=20):
    """手动文字搜索：自动引擎全部挂掉后的兜底。浏览器保持打开，用户自己搜，AI提取结果。"""
    print("\n🟡 [手动文字搜索] 所有搜索引擎都挂了，交给你了", flush=True)
    print("   ┌─────────────────────────────────────────────┐", flush=True)
    print("   │ 1. 浏览器里已经打开了页面                    │", flush=True)
    print("   │ 2. 你自己搜/翻页/处理验证码                  │", flush=True)
    print("   │ 3. 搜到结果后按 Enter，我提取标题+链接+摘要  │", flush=True)
    print("   │ 4. 输入 'done' 退出                          │", flush=True)
    print("   └─────────────────────────────────────────────┘", flush=True)
    all_results = []
    seen_urls = set()
    while True:
        ok = await wait_for_user_input(page, "准备好了？按 Enter 提取，输入 'done' 退出")
        if not ok:
            break
        # 先试通用提取
        results = await extract_search_results(page, max_count)
        if not results:
            # 再逐引擎专用提取逻辑
            for eng_key in TEXT_ENGINES:
                info = TEXT_ENGINES[eng_key]
                try:
                    results = await page.evaluate(info["extract"])
                    if results:
                        break
                except:
                    continue

        if results:
            # 去重
            new_count = 0
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
                    new_count += 1
            print(f"\n✅ 提取到 {len(results)} 条（新增 {new_count} 条，累计 {len(all_results)} 条）", flush=True)
            for i, r in enumerate(results[:max_count], 1):
                print(f"\n[{i}] {r.get('title', '')[:80]}", flush=True)
                print(f"    🔗 {r.get('url', '')[:120]}", flush=True)
                if r.get('snippet'):
                    print(f"    💬 {r['snippet'][:200]}", flush=True)
        else:
            print("   ⚠️ 当前页没提取到搜索结果", flush=True)
            print("   提示：确保页面显示的是搜索结果列表，然后重试", flush=True)

    if all_results:
        print(f"\n{'='*60}", flush=True)
        print(f"📎 手动搜索共 {len(all_results)} 条结果", flush=True)
        print(f"{'='*60}", flush=True)
    return all_results


def ddg_lite_search(query, limit=10):
    """纯HTTP搜索，不用浏览器。爬 DuckDuckGo Lite HTML 版"""
    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ❌ DDG Lite: {e}")
        return []
    # 解析 result__a（标题+URL）和 result__snippet（摘要）
    titles = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>', html
    )
    snippets = re.findall(
        r'<div[^>]+class="result__snippet"[^>]*>\s*(.*?)\s*</div>', html, re.DOTALL
    )
    # 清理 snippet 中的 HTML 标签
    results = []
    for i, (url_raw, title) in enumerate(titles[:limit]):
        snippet = snippets[i].strip() if i < len(snippets) else ""
        snippet = re.sub(r"<[^>]+>", "", snippet)  # strip HTML tags
        results.append({
            "title": title.strip(),
            "url": urllib.parse.unquote(url_raw),
            "snippet": snippet,
            "engine": "DDG Lite",
        })
    return results


def baidu_lite_search(query, limit=10):
    """纯HTTP搜索百度简单HTML版（中文查询 lite 直连主力）"""
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query) + "&rn=" + str(min(max(limit, 10), 20))
    # 完整 cookie 组 + Referer，否则百度直接弹"百度安全验证"页
    bid = hashlib.md5((query + str(time.time())).encode("utf-8")).hexdigest()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.baidu.com/",
        "Cookie": (
            f"BAIDUID={bid}:FG=1; BIDUPSID={bid}; PSTM={int(time.time())}; "
            "BD_CK_SAM=1; PSINO=1; delPer=0; HMACS=1"
        ),
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ❌ Baidu Lite: {e}")
        return []
    # 每个结果块: <h3 ...><a href="..." ...>标题</a></h3>（百度返回 /link?url= 跳转链）
    items = re.findall(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
    results = []
    for href, title in items[:limit]:
        title = re.sub(r"<[^>]+>", "", title).strip()
        if not title or not href:
            continue
        if href.startswith("/link?url="):
            href = "https://www.baidu.com" + href
        results.append({
            "title": title,
            "url": href,
            "snippet": "",
            "engine": "Baidu Lite",
        })
    return results


def _tinyfish_api_key():
    """TinyFish key：优先环境变量，其次 tinyfish CLI 配置 ~/.tinyfish/config.json"""
    key = os.environ.get("TINYFISH_API_KEY")
    if key:
        return key
    try:
        cfg = os.path.join(os.path.expanduser("~"), ".tinyfish", "config.json")
        with open(cfg, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("api_key") or ""
    except Exception:
        return ""


def tinyfish_search(query, limit=10):
    """TinyFish Search API（key 从环境变量或 tinyfish CLI 配置读取，不可用时静默返回空）"""
    key = _tinyfish_api_key()
    if not key:
        print("  ⚠️ TinyFish: 未找到 API key（TINYFISH_API_KEY / ~/.tinyfish/config.json），跳过", flush=True)
        return []
    url = "https://api.search.tinyfish.ai?query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "X-API-Key": key,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  ❌ TinyFish: {str(e)[:60]}", flush=True)
        return []
    results = []
    for r in (data.get("results") or [])[:limit]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "engine": "TinyFish",
        })
    return results


_searxng_app = None  # lazy-init Flask app for in-process search

def _find_searxng_src():
    """自动发现 SearXNG 源码目录：优先环境变量 SEARXNG_SRC，
    其次项目父目录下的 searxng-src（兄弟目录），最后 ~/.searxng-src。"""
    env = os.environ.get("SEARXNG_SRC")
    if env and os.path.isdir(env):
        return env
    project_root = os.path.dirname(os.path.abspath(__file__))
    sibling = os.path.join(os.path.dirname(project_root), "searxng-src")
    if os.path.isdir(sibling):
        return sibling
    home_src = os.path.join(os.path.expanduser("~"), "searxng-src")
    if os.path.isdir(home_src):
        return home_src
    return None

def _find_searxng_settings(searxng_src):
    """在 SearXNG 源码目录下查找 settings 配置目录。"""
    for name in ("searxng-settings", "searxng/settings"):
        p = os.path.join(searxng_src, name)
        if os.path.isdir(p):
            return p
    return None

def searxng_search(query, limit=10):
    """本机 SearXNG 元搜索（in-process Flask test_client，无需启动 HTTP 服务。
    依赖：SearXNG 源码在 SEARXNG_SRC 环境变量或项目兄弟目录 searxng-src。
    未安装或初始化失败时静默返回空。"""
    global _searxng_app
    if _searxng_app is None:
        try:
            searxng_src = _find_searxng_src()
            if not searxng_src:
                _searxng_app = False
                return []
            if searxng_src not in sys.path:
                sys.path.insert(0, searxng_src)
            settings_dir = _find_searxng_settings(searxng_src)
            if settings_dir:
                os.environ.setdefault("SEARXNG_SETTINGS_PATH", settings_dir)
            import searx as _searx
            _searx.init_settings()
            from searx.webapp import app as _app
            _searxng_app = _app
        except Exception:
            _searxng_app = False  # mark as failed, don't retry
            return []
    if not _searxng_app:
        return []
    try:
        with _searxng_app.test_client() as client:
            resp = client.get("/search?q=" + urllib.parse.quote(query)
                              + "&format=json")
            if resp.status_code != 200:
                return []
            data = json.loads(resp.data)
    except Exception:
        return []
    results = []
    for r in (data.get("results") or [])[:limit]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
            "engine": "SearXNG/" + (r.get("engine", "") or "meta"),
        })
    return results


# 聚合页/噪声域：结果 URL 命中即丢弃
_NOISE_URL_PAT = re.compile(
    r"(?:^|\.)image\.baidu\.com$|(?:^|\.)baijiahao\.baidu\.com$"
    r"|(?:^|\.)m\.baidu\.com$|(?:^|\.)b2b\.baidu\.com$"
)


def _is_noise_url(url):
    try:
        host = urllib.parse.urlsplit(url or "").netloc.lower()
    except Exception:
        return False
    return bool(_NOISE_URL_PAT.search(host))


def _norm_url_key(url):
    """URL 归一去重键：域名(去www) + 路径"""
    try:
        pu = urllib.parse.urlsplit(url or "")
        host = pu.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host + pu.path.rstrip("/")
    except Exception:
        return url or ""


def full_auto_text_search(query, limit, headless=True):
    """AI 裸调默认流水线（--search 且未显式指定 -e 时）：
    ① 多源并发直连(baidu+ddg+tinyfish+searxng) → ② 浏览器引擎链 → ③ cloak 兜底 → ④ tinyfish → ⑤ 手动(仅交互终端)
    总时长护栏 ~120s，超时直接返回已合并结果。"""
    deadline = time.monotonic() + 120
    merged = []
    seen = set()

    def merge(results):
        added = 0
        for r in results or []:
            key = _norm_url_key(r.get("url", ""))
            if key and key not in seen:
                seen.add(key)
                merged.append(r)
                added += 1
        return added

    def show(tag):
        if not merged:
            print("❌ 无结果", flush=True)
            return
        print(f"\n{'='*60}", flush=True)
        print(f"📎 共 {len(merged)} 条结果（{tag}）", flush=True)
        print(f"{'='*60}", flush=True)
        for i, r in enumerate(merged[:limit], 1):
            print(f"\n[{i}] {r.get('title', '')}", flush=True)
            print(f"    🔗 {r.get('url', '')}", flush=True)
            if r.get('snippet'):
                print(f"    💬 {r['snippet'][:200]}", flush=True)

    def time_left():
        return deadline - time.monotonic()

    # ── 第 1 跳: 多源并发直连（baidu_lite+ddg_lite+tinyfish+searxng，都等齐合并）──
    print(f"① 多源直连: {' + '.join(n for n, _ in MULTI_SOURCE_ENGINES)} 并发（目标 {limit} 条）...", flush=True)
    try:
        ms_results, ms_counts = multi_source_search(query, limit, verbose=False)
    except Exception as e:
        ms_results, ms_counts = [], {}
        print(f"   ❌ 多源直连异常: {str(e)[:60]}", flush=True)
    for name, _ in MULTI_SOURCE_ENGINES:
        if ms_counts.get(name):
            print(f"   ✅ [{name}] {ms_counts[name]} 条", flush=True)
    merge(ms_results)
    if len(merged) >= limit:
        show("多源直连")
        return
    if merged:
        print(f"   ⚠️ 多源直连不足（{len(merged)} 条），继续降级", flush=True)

    # ── 第 2 跳: 浏览器引擎链（原 edge 路径）──
    if time_left() <= 5:
        show("超时护栏提前返回")
        return
    print(f"② 浏览器链: {','.join(TEXT_FALLBACK_CHAIN)} ...", flush=True)
    try:
        browser_results = asyncio.run(run(
            query=query, engines=TEXT_FALLBACK_CHAIN, max_count=limit,
            search=True, browser_choice="edge", headless=headless))
        merge(browser_results)
    except Exception as e:
        print(f"   ❌ 浏览器链异常: {str(e)[:80]}", flush=True)
    if len(merged) >= limit:
        show("浏览器链")
        return

    # ── 第 3 跳: cloak 兜底 ──
    if _CLOAK_AVAILABLE and time_left() > 5:
        print(f"③ 浏览器链不足（共 {len(merged)} 条），启动 cloak 兜底...", flush=True)
        try:
            merge(cloak_text_search(query, limit, headless=headless))
        except Exception as e:
            print(f"   ❌ cloak 异常: {str(e)[:80]}", flush=True)
        if len(merged) >= limit:
            show("cloak 兜底")
            return
    else:
        print("③ cloak 未安装或超时将到，跳过 cloak 兜底", flush=True)

    # ── 第 4 跳: tinyfish API ──
    if _tinyfish_api_key() and time_left() > 5:
        print(f"④ 仍不足（共 {len(merged)} 条），尝试 TinyFish API...", flush=True)
        try:
            merge(tinyfish_search(query, limit))
        except Exception as e:
            print(f"   ❌ TinyFish 异常: {str(e)[:60]}", flush=True)
        if len(merged) >= limit:
            show("TinyFish")
            return
    else:
        print("④ 未设置 TINYFISH_API_KEY，跳过 TinyFish", flush=True)

    # ── 第 5 跳: 手动模式（仅交互终端；浏览器链内部 zero 结果时已内置该兜底，
    #    wait_for_user_input 对非 tty 自动跳过，故这里无需重复实现）──
    if not merged and sys.stdin.isatty():
        print("⑤ 全链路无结果，可在终端交互环境用 --manual 重试", flush=True)

    show("全自动流水线")


# 默认多源清单（全语言同套源；searxng/tinyfish 不可用时各自静默缺席）
MULTI_SOURCE_ENGINES = [
    ("baidu", baidu_lite_search),
    ("ddg", ddg_lite_search),
    ("tinyfish", tinyfish_search),
    ("searxng", searxng_search),
]


def multi_source_search(query, limit, timeout=35, verbose=True):
    """多源并发都等齐后合并去重，返回 (merged_results, counts)。
    单源失败不影响其他源；全空返回空列表由上层处理。"""
    merged = []
    seen = set()
    counts = {}

    def merge(results):
        added = 0
        for r in results or []:
            u = r.get("url", "")
            if _is_noise_url(u):
                continue
            key = _norm_url_key(u)
            if key and key not in seen:
                seen.add(key)
                merged.append(r)
                added += 1
        return added

    engines = MULTI_SOURCE_ENGINES
    all_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(engines)) as ex:
        futs = {ex.submit(fn, query, limit): name for name, fn in engines}
        try:
            for fut in concurrent.futures.as_completed(futs, timeout=timeout):
                name = futs[fut]
                try:
                    rs = fut.result()
                    all_results[name] = rs
                    counts[name] = len(rs)
                except Exception as e:
                    counts[name] = 0
                    if verbose:
                        print(f"   ❌ [{name}] {str(e)[:60]}", flush=True)
        except concurrent.futures.TimeoutError:
            for fut in futs:
                fut.cancel()
    for name, _ in engines:
        rs = all_results.get(name)
        if rs:
            merge(rs)
    if verbose:
        parts = "、".join(f"{n} {counts[n]}" for n, _ in engines if counts.get(n))
        print(f"🔍 {len(engines)}源合并: 共{len(merged)}条（{parts}）", flush=True)
    return merged, counts


def simple_dual_source_search(query, limit):
    """默认简单搜索（--search 且未显式 -e、无 --deep 时）：多源并发合并。
    源 = baidu_lite + ddg_lite + tinyfish（tinyfish 不可用时静默缺席）。"""
    merged, counts = multi_source_search(query, limit)
    if not merged:
        print("❌ 无结果", flush=True)
        return
    print(f"\n{'='*60}", flush=True)
    print(f"📎 共 {len(merged)} 条结果", flush=True)
    print(f"{'='*60}", flush=True)
    for i, r in enumerate(merged[:limit], 1):
        print(f"\n[{i}] {r.get('title', '')}", flush=True)
        print(f"    🔗 {r.get('url', '')}", flush=True)
        if r.get('snippet'):
            print(f"    💬 {r['snippet'][:200]}", flush=True)


async def read_multiple_pages(urls, browser_choice="edge", timeout=60, headless=True):
    """并行读取多个网页（headless，不弹浏览器窗口）"""
    async with async_playwright() as p:
        launch_kwargs = dict(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled',
                  '--disable-automation', '--no-sandbox',
                  '--disable-setuid-sandbox'],
        )
        if browser_choice == "edge":
            launch_kwargs["channel"] = "msedge"
            print("🌐 浏览器: Edge（headless 并行）", flush=True)
        else:
            print("🌐 浏览器: Chromium（headless 并行）", flush=True)
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            window.chrome = { runtime: {} };
        """)

        async def read_one(url):
            page = await context.new_page()
            try:
                print(f"📖 [{url[:80]}]", flush=True)
                await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                page_text = await page.inner_text("body") if await page.query_selector("body") else ""
                if detect_captcha(page_text) or detect_blocked(page_text):
                    print(f"   🟡 被拦截（验证码/403）", flush=True)
                    return {"url": url, "title": "", "content": "", "blocked": True}

                content = await extract_page_content(page)
                title = await page.title()
                print(f"   ✅ {title or url[:40]} ({len(content)}字)", flush=True)
                return {"url": url, "title": title, "content": content}
            except Exception as e:
                print(f"   ❌ {str(e)[:60]}", flush=True)
                return {"url": url, "title": "", "content": "", "error": str(e)}
            finally:
                await page.close()

        tasks = [read_one(url) for url in urls]
        results = await asyncio.gather(*tasks)
        await browser.close()

        print(f"\n{'='*60}", flush=True)
        print(f"📎 共读取 {len(results)} 个网页", flush=True)
        print(f"{'='*60}", flush=True)
        for i, r in enumerate(results, 1):
            if r.get('blocked'):
                print(f"  [{i}] 🟡 被拦截 — {r['url']}", flush=True)
            elif r.get('error'):
                print(f"  [{i}] ❌ {r['error']} — {r['url']}", flush=True)
            else:
                t = (r.get('title') or '')[:50]
                c = len(r.get('content') or '')
                print(f"  [{i}] ✅ {t} ({c}字)", flush=True)
                print(f"      {r['url']}")

        return results


# ── Crawl4AI 模式（深度网页 → Markdown） ─────────────────────────────

async def crawl_extract(urls, headless=True, output_dir="."):
    """使用 Crawl4AI 深度提取网页内容为结构化 Markdown"""
    if not _CRAWL4AI_AVAILABLE:
        print("❌ Crawl4AI 未安装: pip install crawl4ai", flush=True)
        return

    print("🕷️  Crawl4AI 深度提取模式（浏览器渲染 + LLM 友好输出）", flush=True)

    async with AsyncWebCrawler(verbose=False) as crawler:
        for url in urls:
            print(f"\n📖 [{url[:80]}]", flush=True)
            try:
                result = await crawler.arun(
                    url=url,
                    bypass_cache=True,
                )
                if result.success:
                    md = result.markdown or ""
                    title = url
                    # Try to extract title from markdown
                    first_line = md.split('\n')[0] if md else ''
                    if first_line.startswith('# '):
                        title = first_line[2:].strip()
                    print(f"   ✅ {title[:60]} ({len(md)}字)", flush=True)

                    # Display
                    print(f"{'='*60}", flush=True)
                    for line in md.split('\n')[:150]:
                        print(line, flush=True)
                    lines = md.split('\n')
                    if len(lines) > 150:
                        print(f"\n... (共 {len(lines)} 行，仅显示前 150 行)", flush=True)

                    # Save if output dir specified
                    if output_dir != ".":
                        safe = re.sub(r'[^\w]', '_', url.split('//')[-1].split('/')[0]) or "page"
                        fpath = Path(output_dir) / f"crawl_{safe}.md"
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(md)
                        print(f"💾 已保存: {fpath}", flush=True)
                else:
                    err = result.error_message or "unknown error"
                    print(f"   ❌ {err[:80]}", flush=True)
            except Exception as e:
                print(f"   ❌ 异常: {str(e)[:100]}", flush=True)


# ── CloakBrowser 模式（反检测） ────────────────────────────────────────

def _cloak_detect_blocked(text):
    keywords = ["sorry", "please verify", "captcha", "access denied", "403 forbidden",
                "enable javascript", "your request has been blocked", "robot",
                "cf-browser-verification", "just a moment", "attention required"]
    return any(k in text.lower() for k in keywords)


def cloak_read_pages(urls, timeout=60, headless=True):
    """同步版读网页 — 使用 CloakBrowser，能过 Cloudflare 等反爬"""
    if not _CLOAK_AVAILABLE:
        print("❌ CloakBrowser 未安装: pip install cloakbrowser", flush=True)
        return [{"url": u, "title": "", "content": "", "error": "CloakBrowser not installed"} for u in urls]

    print("🛡️  CloakBrowser 模式（反检测）", flush=True)
    browser = cloak_launch(headless=headless, humanize=True)

    results = []
    for url in urls:
        page = browser.new_page()
        try:
            print(f"📖 [{url[:80]}]", flush=True)
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            body_text = page.inner_text("body") if page.query_selector("body") else ""
            if _cloak_detect_blocked(body_text):
                # 可能是误判，先看 URL 有没有被重定向到验证页
                if page.url != url and "captcha" in page.url.lower() or "challenge" in page.url.lower():
                    print(f"   🟡 被拦截（重定向到验证页）", flush=True)
                    results.append({"url": url, "title": "", "content": "", "blocked": True})
                    continue
            # 页面正常加载
            content = page.inner_text("body")[:50000] if page.query_selector("body") else ""
            title = page.title()
            print(f"   ✅ {title or url[:40]} ({len(content)}字)", flush=True)
            results.append({"url": url, "title": title, "content": content})

        except Exception as e:
            print(f"   ❌ {str(e)[:60]}", flush=True)
            results.append({"url": url, "title": "", "content": "", "error": str(e)})
        finally:
            page.close()

    browser.close()

    print(f"\n{'='*60}", flush=True)
    print(f"📎 共读取 {len(results)} 个网页（CloakBrowser）", flush=True)
    print(f"{'='*60}", flush=True)
    for i, r in enumerate(results, 1):
        if r.get('blocked'):
            print(f"  [{i}] 🟡 被拦截 — {r['url']}", flush=True)
        elif r.get('error'):
            print(f"  [{i}] ❌ {r['error']} — {r['url']}", flush=True)
        else:
            t = (r.get('title') or '')[:50]
            c = len(r.get('content') or '')
            print(f"  [{i}] ✅ {t} ({c}字)", flush=True)
            print(f"      {r['url']}")
    return results


def cloak_text_search(query, limit=10, headless=True):
    """同步版文字搜索 — 使用 CloakBrowser，JS 提取搜索结果"""
    if not _CLOAK_AVAILABLE:
        print("❌ CloakBrowser 未安装: pip install cloakbrowser", flush=True)
        return []

    print("🛡️  CloakBrowser 文字搜索（反检测）", flush=True)
    browser = cloak_launch(headless=headless, humanize=True)
    page = browser.new_page()

    bing_js = """
    () => {
        const items = [];
        const algos = document.querySelectorAll("li.b_algo, .b_algo");
        algos.forEach(el => {
            const h2 = el.querySelector("h2");
            const a = h2 ? h2.querySelector("a") : null;
            if (!a) return;
            const title = a.innerText.trim();
            // Prefer the actual href. Only use cite if href is a Bing redirect.
            let url = a.href;
            if (!url || url.includes("bing.com/ck/") || url.includes("bing.com/url?")) {
                const cite = el.querySelector("cite, .b_attribution");
                url = cite ? cite.innerText.trim() : "";
                if (url && !url.startsWith("http")) url = "https://" + url;
            }
            url = url.split(" ")[0].split("\\n")[0];
            if (title && url && !url.includes("bing.com/")) items.push({title, url});
        });
        return items;
    }
    """
    brave_js = """
    () => {
        const items = [];
        const seen = new Set();
        // Brave puts results in .result-content or .snippet containers
        const containers = document.querySelectorAll(".result-content, [class*='result']");
        containers.forEach(container => {
            const link = container.querySelector("a[href]");
            if (!link) return;
            const href = link.href;
            if (!href || !href.startsWith("http") || href.includes("brave.com")) return;
            const title = container.querySelector("h2, h3, .heading, [class*='title']");
            const text = title ? title.innerText.trim() : link.innerText.trim();
            if (text.length < 5) return;
            const key = href.split("?")[0];
            if (!seen.has(key)) { seen.add(key); items.push({title: text.slice(0,100), url: href}); }
        });
        // Fallback: look for links with meaningful text
        if (items.length < 3) {
            const links = document.querySelectorAll("a[href]");
            links.forEach(a => {
                const href = a.href;
                if (!href || !href.startsWith("http") || href.includes("brave.com")) return;
                const text = a.innerText.trim();
                if (text.length < 15) return;
                const key = href.split("?")[0];
                if (!seen.has(key)) { seen.add(key); items.push({title: text.slice(0,100), url: href}); }
            });
        }
        return items;
    }
    """

    engines = [
        ("Bing", f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count={limit}", bing_js),
        ("Brave", f"https://search.brave.com/search?q={urllib.parse.quote(query)}", brave_js),
    ]

    all_results = []
    for name, url, js_code in engines:
        try:
            print(f"  🔍 {name}...", flush=True)
            # wait_until="load"：规避 cloakbrowser 0.4.10 下 Bing 触发 context destroyed 的问题
            page.goto(url, timeout=30000, wait_until="load")
            page.wait_for_timeout(2000)
            results = page.evaluate(js_code)
            for r in results:
                r["engine"] = name
                all_results.append(r)
            print(f"     → {len(results)} 结果", flush=True)

        except Exception as e:
            print(f"     ❌ {name}: {str(e)[:40]}", flush=True)

    page.close()
    browser.close()

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        key = r.get("url", "").split("?")[0]
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"\n{'='*60}", flush=True)
    print(f"✅ 共 {len(unique)} 条结果（CloakBrowser）", flush=True)
    print(f"{'='*60}", flush=True)
    for i, r in enumerate(unique[:limit], 1):
        print(f"  [{i}] {r['title'][:60]}", flush=True)
        print(f"      {r['url']}", flush=True)

    return unique[:limit]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="接力爬虫 — 人机协作万能搜索器（搜图 / 搜文字 / 读网页）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="搜索关键词")
    parser.add_argument("--engine", "-e", default="",
                        help=f"图片搜索引擎链（逗号分隔），默认: {','.join(FALLBACK_CHAIN)}")
    parser.add_argument("--url", "-u", help="图片搜索：目标网页 URL")
    parser.add_argument("--search", action="store_true",
                        help="文字搜索模式（默认是搜图）")
    parser.add_argument("--read", metavar="URL", nargs='+',
                        help="读网页模式：打开一个或多个 URL 提取正文")
    parser.add_argument("--crawl", metavar="URL", nargs='+',
                        help="爬虫模式（Crawl4AI）：浏览器渲染 + 深度提取为结构化 Markdown，JS 重页面首选")
    parser.add_argument("--free", action="store_true",
                        help=f"仅用免费摄影站: {', '.join(FREE_SITE_KEYS)}")
    parser.add_argument("--download", "-d", action="store_true", help="下载图片")
    parser.add_argument("--output", "-o", default=".", help="下载目录")
    parser.add_argument("--limit", "-n", type=int, default=5, help="最大结果数")
    parser.add_argument("--timeout", type=int, default=30, help="网页打开超时秒数（--read 模式，默认 30）")
    parser.add_argument("--min-size", type=int, default=100, help="最小图片宽度（仅搜图模式）")
    parser.add_argument("--deep", action="store_true",
                        help="增强模式：多级降级流水线（lite→浏览器链→cloak→tinyfish→手动）")
    parser.add_argument("--backend", default="edge",
                        choices=["edge", "chromium", "lite", "cloak", "manual", "opencli"],
                        help="后端: edge(默认)/chromium=Playwright, lite=纯HTTP, cloak=反检测, manual=手动浏览, opencli=系统Edge浏览器(可保持会话)")
    parser.add_argument("--show", action="store_true",
                        help="显示浏览器窗口（默认 headless 不显示）")
    # ── opencli 抓取模式参数 ──
    parser.add_argument("--fetch", choices=["xueqiu", "bilibili"],
                        help="抓取模式: xueqiu(雪球) / bilibili(B站)（与 --backend opencli 配合）")
    parser.add_argument("--user-id", type=int,
                        help="雪球用户 ID（配合 --fetch xueqiu）")
    parser.add_argument("--mid", type=int,
                        help="B 站用户 mid（配合 --fetch bilibili）")
    parser.add_argument("--audio", action="store_true",
                        help="下载 B 站音频（配合 --fetch bilibili）")
    parser.add_argument("--series", action="store_true",
                        help="按合集分类抓取 B 站视频（配合 --fetch bilibili）")
    parser.add_argument("--quality", default="9",
                        help="B 站音频质量 0-9，默认 9（约 65kbps，讲课足够）")
    parser.add_argument("--pages", type=int, default=99,
                        help="抓取最大页数（默认 99）")
    args = parser.parse_args()

    headless = not args.show

    # ── opencli 浏览器后端 ──
    if args.backend == "opencli":
        if not _OPENCLI_AVAILABLE:
            print("❌ opencli 未安装。安装: npm install -g opencli", flush=True)
            sys.exit(1)

        if args.fetch == "xueqiu":
            if not args.user_id:
                print("❌ 雪球抓取需要 --user-id", flush=True)
                sys.exit(1)
            posts = opencli_fetch.xueqiu_posts(args.user_id, args.pages)
            print(f"\n📊 共 {len(posts)} 条帖子:", flush=True)
            print(f"{'='*60}", flush=True)
            for i, p in enumerate(posts[:20], 1):
                text = (p.get('text', '') or '')[:200]
                created = p.get('created_at', '')
                print(f"\n[{i}] {created}", flush=True)
                print(f"    {text}", flush=True)
            if len(posts) > 20:
                print(f"\n... 还有 {len(posts) - 20} 条", flush=True)
            # 保存到文件
            ts = time.strftime("%Y%m%d_%H%M%S")
            fpath = f"xueqiu_{args.user_id}_{ts}.json"
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(posts, f, ensure_ascii=False, indent=2)
            print(f"\n💾 已保存: {fpath}", flush=True)
            sys.exit(0)

        elif args.fetch == "bilibili":
            if not args.mid:
                print("❌ B 站抓取需要 --mid", flush=True)
                sys.exit(1)
            if args.series:
                series = opencli_fetch.bilibili_series(args.mid)
                print(f"\n共 {len(series)} 个合集", flush=True)
            elif args.audio:
                opencli_fetch.bilibili_audio(
                    args.mid, args.output or ".", args.quality
                )
            else:
                videos = opencli_fetch.bilibili_videos(args.mid)
                print(f"\n共 {len(videos)} 个视频:", flush=True)
                import re as _re
                for v in videos[:20]:
                    t = (v.get('title', '') or '')[:60]
                    print(f"  {v['bv']}  {t}", flush=True)
                if len(videos) > 20:
                    print(f"  ... 还有 {len(videos) - 20} 个", flush=True)
            sys.exit(0)

        elif args.read:
            for url in args.read:
                # 非交互环境（AI agent 调用）自动默认不滚动，避免 input() 抛 EOFError
                if sys.stdin.isatty():
                    scroll = input(f"是否滚动页面 {url}? (y/N): ").strip().lower() == 'y'
                else:
                    scroll = False
                result = opencli_fetch.read_page(url, scroll=scroll)
                if result:
                    if result.get('blocked'):
                        print(f"  🤖 页面被拦截（WAF/验证码）", flush=True)
                        print(f"  文本预览: {result.get('content', '')[:200]}", flush=True)
                    else:
                        content = result.get('content', '')
                        title = result.get('title', '')
                        print(f"\n📄 {title} ({len(content)}字)", flush=True)
                        print(f"{'='*60}", flush=True)
                        for line in content.split('\n')[:100]:
                            print(line, flush=True)
            sys.exit(0)

        else:
            print("❌ opencli 模式需要 --read URL 或 --fetch xueqiu/bilibili", flush=True)
            sys.exit(1)

    # ── CloakBrowser 模式 ──
    if args.backend == "cloak":
        if not args.query and not args.read:
            print("❌ --backend cloak 需要 --search 关键词 或 --read URL", flush=True)
            sys.exit(1)
        if args.read:
            cloak_read_pages(args.read, timeout=args.timeout, headless=headless)
        elif args.search:
            cloak_text_search(args.query, args.limit, headless=headless)
        sys.exit(0)

    # ── Manual 模式：你浏览我提取 ──
    if args.backend == "manual":
        if not args.read:
            print("❌ --backend manual 仅支持 --read URL", flush=True)
            sys.exit(1)
        asyncio.run(run(
            read_url=args.read[0], max_count=args.limit, manual=True,
            browser_choice="edge", headless=headless,
        ))
        sys.exit(0)

    # ── Crawl4AI 爬虫模式 ──
    if args.crawl:
        asyncio.run(crawl_extract(args.crawl, headless=headless, output_dir=args.output))
        sys.exit(0)

    # ── 读网页模式 ──
    if args.read:
        bc = args.backend if args.backend in ("edge", "chromium") else "edge"
        if len(args.read) == 1:
            asyncio.run(run(
                read_url=args.read[0], max_count=args.limit, manual=False,
                browser_choice=bc, headless=headless,
            ))
        else:
            asyncio.run(read_multiple_pages(args.read, bc, timeout=args.timeout, headless=headless))
        sys.exit(0)

    # ── 文字搜索模式 ──
    if args.search:
        if not args.query:
            print("❌ 文字搜索需要提供关键词", flush=True)
            sys.exit(1)
        if args.backend == "lite":
            print("🔵 [DDG Lite] 纯HTTP搜索（无浏览器）", flush=True)
            results = ddg_lite_search(args.query, args.limit)
            if results:
                print(f"\n✅ 共 {len(results)} 条结果", flush=True)
                print(f"{'='*60}", flush=True)
                for i, r in enumerate(results, 1):
                    print(f"\n[{i}] {r['title']}", flush=True)
                    print(f"    🔗 {r['url']}", flush=True)
                    if r.get('snippet'):
                        print(f"    💬 {r['snippet'][:200]}", flush=True)
            else:
                print("❌ 无结果", flush=True)
            sys.exit(0)
        if args.backend == "edge" and not args.engine:
            if args.deep:
                # 增强模式：多级降级链 lite 直连 → 浏览器链 → cloak → tinyfish → 手动
                print("🚀 [增强模式] 降级流水线启动", flush=True)
                full_auto_text_search(args.query, args.limit, headless=headless)
            else:
                # 默认：简单双源合并
                simple_dual_source_search(args.query, args.limit)
            sys.exit(0)
        text_engines = [e.strip() for e in args.engine.split(",") if e.strip()] if args.engine else TEXT_FALLBACK_CHAIN
        bc = args.backend if args.backend in ("edge", "chromium") else "edge"
        asyncio.run(run(
            query=args.query, engines=text_engines, max_count=args.limit,
            search=True, browser_choice=bc, headless=headless,
        ))
        sys.exit(0)

    # ── 图片搜索模式（默认） ──
    if args.backend == "lite":
        print("❌ --backend lite 仅支持文字搜索（配合 --search）", flush=True)
        sys.exit(1)
    if not args.query and not args.url:
        parser.print_help()
        sys.exit(1)

    engine_ids = [e.strip() for e in args.engine.split(",") if e.strip()] if args.engine else FALLBACK_CHAIN.copy()
    if args.free:
        engine_ids = FREE_SITE_KEYS.copy()

    valid_engines = [e for e in engine_ids if e in ENGINES]
    if not valid_engines:
        print(f"❌ 无效引擎: {args.engine}，可用: {', '.join(ENGINES.keys())}", flush=True)
        sys.exit(1)

    free_count = sum(1 for e in valid_engines if ENGINES[e].get("license", "").startswith("✅"))
    unknown_count = sum(1 for e in valid_engines if ENGINES[e].get("license", "").startswith("⚠️"))
    print(f"🔍 引擎: {', '.join(ENGINES[e]['name'] for e in valid_engines)}", flush=True)
    if free_count:
        print(f"✅ {free_count} 个免费摄影站（可商用）", flush=True)
    if unknown_count:
        print(f"⚠️ {unknown_count} 个搜索引擎（版权未知，自行核实）", flush=True)

    bc = args.backend if args.backend in ("edge", "chromium") else "edge"
    asyncio.run(run(
        query=args.query, engines=valid_engines, url=args.url,
        max_count=args.limit, download=args.download,
        output_dir=args.output, manual=False, min_size=args.min_size, free_only=args.free,
        browser_choice=bc, headless=headless,
    ))
