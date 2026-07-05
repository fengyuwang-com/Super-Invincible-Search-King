#!/usr/bin/env python3
"""
Visual Web Scraper — 有头浏览器图片采集工具
=============================================
用 Playwright 有头浏览器打开任意网站，采集图片。
支持搜索引擎（Bing/Google/Baidu）和任意网页。

核心思路：headless=False 启动真实浏览器 → 不被反爬识别 →
用户能看到浏览器窗口 → 可以手动辅助操作。

Usage:
    # 搜索引擎搜图
    python scraper.py "富春山居图" --engine bing
    python scraper.py "富春山居图" --engine google
    python scraper.py "富春山居图" --engine baidu

    # 扒任意网页的图
    python scraper.py --url "https://example.com/gallery"

    # 下载图片
    python scraper.py "cat" --engine bing --download --output ./pics

    # 交互模式（保持浏览器打开，你可以手动操作）
    python scraper.py --url "https://example.com" --interactive
"""

import asyncio, json, os, sys, argparse, urllib.parse, urllib.request, re
from pathlib import Path
from urllib.parse import urlparse, urljoin

sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright


# ============================================================
# 搜索引擎配置 — 每种引擎的搜索URL和图片提取逻辑
# ============================================================

ENGINES = {
    "bing": {
        "name": "Bing Images",
        "search_url": "https://www.bing.com/images/search?q={query}&form=HDRSC2",
        "wait_selector": ".iusc",
        "extract": """
            (() => {
                const results = [];
                document.querySelectorAll('.iusc').forEach(el => {
                    try {
                        const m = JSON.parse(el.getAttribute('m'));
                        if (m && m.murl) {
                            results.push({
                                url: m.murl,
                                title: m.t || '',
                                thumb: m.turl || '',
                                w: m.w || 0,
                                h: m.h || 0,
                                source: 'bing'
                            });
                        }
                    } catch(e) {}
                });
                return results;
            })()
        """,
    },
    "google": {
        "name": "Google Images",
        "search_url": "https://www.google.com/search?q={query}&tbm=isch",
        "wait_selector": "img",
        "extract": """
            (() => {
                const results = [];
                // Google stores image data in script tags or data attributes
                // Method 1: Try direct image elements (after clicking)
                document.querySelectorAll('img.rg_i, img[data-src], img[src*="http"]').forEach(img => {
                    const src = img.getAttribute('data-src') || img.src || '';
                    if (src && src.startsWith('http') && img.naturalWidth > 50) {
                        results.push({
                            url: src,
                            title: img.alt || '',
                            w: img.naturalWidth,
                            h: img.naturalHeight,
                            source: 'google'
                        });
                    }
                });
                return results;
            })()
        """,
    },
    "baidu": {
        "name": "百度图片",
        "search_url": "https://image.baidu.com/search/index?tn=baiduimage&word={query}",
        "wait_selector": "img",
        "extract": """
            (() => {
                const results = [];
                document.querySelectorAll('img.main_img, img[src*="http"]').forEach(img => {
                    const src = img.getAttribute('data-imgurl') || img.getAttribute('src') || '';
                    if (src && src.startsWith('http') && img.naturalWidth > 50) {
                        results.push({
                            url: src,
                            title: img.getAttribute('alt') || '',
                            w: img.naturalWidth,
                            h: img.naturalHeight,
                            source: 'baidu'
                        });
                    }
                });
                return results;
            })()
        """,
    },
}


async def scrape_page_images(page, min_width=100):
    """从当前页面提取所有图片（通用方法，适合任意网站）"""
    images = await page.evaluate(f"""() => {{
        const results = [];
        document.querySelectorAll('img').forEach(img => {{
            const src = img.getAttribute('data-src') || img.getAttribute('data-original') ||
                        img.getAttribute('src') || '';
            if (src && src.startsWith('http') && img.naturalWidth > {min_width}) {{
                results.push({{
                    url: src,
                    title: img.alt || img.title || '',
                    w: img.naturalWidth || img.width,
                    h: img.naturalHeight || img.height,
                }});
            }}
        }});
        // Deduplicate by URL
        const seen = new Set();
        return results.filter(r => {{
            if (seen.has(r.url)) return false;
            seen.add(r.url);
            return true;
        }});
    }}""")
    return images


async def run_scraper(
    query: str = None,
    engine: str = "bing",
    url: str = None,
    max_results: int = 15,
    download: bool = False,
    output_dir: str = ".",
    interactive: bool = False,
    min_width: int = 100,
):
    """
    核心函数：打开浏览器 → 访问目标 → 提取图片。
    全程 headless=False，用户可以看到浏览器窗口。
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})

        # ----- 导航到目标页面 -----
        if url:
            print(f"[NAV] 打开网页: {url}", flush=True)
            await page.goto(url, timeout=60000, wait_until="networkidle")
        elif query and engine in ENGINES:
            info = ENGINES[engine]
            search_url = info["search_url"].format(query=urllib.parse.quote(query))
            print(f"[NAV] {info['name']}: {query}", flush=True)
            await page.goto(search_url, timeout=30000)
        else:
            print("[ERR] 需要 --query 或 --url", flush=True)
            await browser.close()
            return []

        await page.wait_for_timeout(3000)

        # ----- 交互模式：用户手动操作 -----
        if interactive:
            print("\n=== 交互模式 ===", flush=True)
            print("浏览器已打开，你可以手动滚动、点击、浏览。", flush=True)
            print("操作完后按 Enter 键，我来提取当前页面的图片。", flush=True)
            input("按 Enter 继续...")
            print("正在提取图片...", flush=True)
            images = await scrape_page_images(page, min_width)
        else:
            # ----- 自动模式：搜索引擎图片提取 -----
            if engine in ENGINES:
                info = ENGINES[engine]

                # 等待内容加载
                try:
                    await page.wait_for_selector(info["wait_selector"], timeout=10000)
                except:
                    pass

                # 滚动触发懒加载
                for i in range(5):
                    await page.evaluate("window.scrollBy(0, 600)")
                    await page.wait_for_timeout(1000)

                # 提取图片
                images = await page.evaluate(info["extract"])
            else:
                # 指定了 URL 但没有指定引擎 → 通用提取
                images = await scrape_page_images(page, min_width)

            # 如果搜索引擎没找到，降级到通用提取
            if not images:
                print("[WARN] 引擎专用提取失败，尝试通用提取...", flush=True)
                for i in range(3):
                    await page.evaluate("window.scrollBy(0, 600)")
                    await page.wait_for_timeout(1000)
                images = await scrape_page_images(page, min_width)

        # ----- 展示结果 -----
        print(f"\n[RES] 找到 {len(images)} 张图片", flush=True)

        # 按尺寸排序（大图优先）
        images.sort(key=lambda x: (x.get("w", 0) or 0) * (x.get("h", 0) or 0), reverse=True)

        results = []
        for i, img in enumerate(images[:max_results]):
            title = (img.get("title") or "").strip() or f"image_{i+1}"
            url_val = img.get("url", "")
            w = img.get("w", "?")
            h = img.get("h", "?")
            print(f"\n  [{i+1}] [{w}x{h}] {title[:60]}", flush=True)
            print(f"       {url_val[:150]}", flush=True)
            results.append({"index": i + 1, "title": title, "url": url_val, "w": w, "h": h})

        # ----- 下载 -----
        if download and results:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            for r in results:
                safe = re.sub(r'[<>:"/\\|?*]', "", r["title"])[:40]
                fname = f"{r['index']:02d}_{safe or 'image'}.jpg"
                fpath = out_path / fname
                try:
                    urllib.request.urlretrieve(r["url"], fpath)
                    print(f"\n  [DL] ✓ {fname}", flush=True)
                except Exception as e:
                    print(f"\n  [DL] ✗ {fname}: {str(e)[:50]}", flush=True)

        print(f"\n[DONE] 共 {len(results)} 张图片", flush=True)
        print("[DONE] 关闭浏览器窗口退出", flush=True)

        # 保持打开直到用户关闭
        while True:
            try:
                await asyncio.sleep(1)
            except:
                break

        await browser.close()
        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visual Web Scraper — 有头浏览器图片采集工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "富春山居图"                     # Bing 搜图（默认）
  %(prog)s "cute cat" --engine google       # Google 搜图
  %(prog)s "山水画" --engine baidu          # 百度搜图
  %(prog)s --url "https://example.com"      # 扒任意网页
  %(prog)s "cat" --download -o ./pics       # 搜索 + 下载
  %(prog)s --url "https://example.com" --interactive  # 交互模式
        """,
    )
    parser.add_argument("query", nargs="?", help="搜索关键词")
    parser.add_argument("--engine", "-e", choices=list(ENGINES.keys()) + ["auto"],
                        default="bing", help="搜索引擎 (默认: bing)")
    parser.add_argument("--url", "-u", help="目标网页URL（扒任意网站的图）")
    parser.add_argument("--download", "-d", action="store_true", help="下载图片到本地")
    parser.add_argument("--output", "-o", default=".", help="下载目录 (默认当前目录)")
    parser.add_argument("--limit", "-n", type=int, default=15, help="最大结果数")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="交互模式：打开浏览器让你手动操作，然后我提取图片")
    parser.add_argument("--min-width", type=int, default=100,
                        help="最小图片宽度 (像素, 默认100, 用来过滤图标)")
    args = parser.parse_args()

    if not args.query and not args.url:
        parser.print_help()
        sys.exit(1)

    asyncio.run(run_scraper(
        query=args.query,
        engine=args.engine,
        url=args.url,
        max_results=args.limit,
        download=args.download,
        output_dir=args.output,
        interactive=args.interactive,
        min_width=args.min_width,
    ))
