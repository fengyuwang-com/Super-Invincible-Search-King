#!/usr/bin/env python3
"""
Bing Image Search & Download Tool
==================================
Uses Playwright (headless=False) to search Bing Images, bypassing anti-bot
detection by running in non-headless mode (visible browser window).

Usage:
    python bing_image_search.py "搜索关键词" [--download] [--output DIR]

Examples:
    python bing_image_search.py "富春山居图 黄公望"
    python bing_image_search.py "cute cat" --download --output ./pics
"""

import asyncio, json, os, sys, argparse, urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright


async def search_images(query: str, max_results: int = 10, download: bool = False, output_dir: str = "."):
    """
    Search Bing Images using Playwright browser.

    Why this works:
    - Runs with headless=False (visible browser) → looks like a real user
    - Bing's anti-bot measures are calibrated against headless/scripted
      browsers. A headed browser matches real user fingerprints:
        * WebGL renderer is exposed
        * navigator.webdriver is false
        * Chrome extensions/plugins are detectable
        * Screen resolution is real
    - Google/Bing/百度 all use JS to render images; simple HTTP requests
      (curl/requests) only get the empty shell page.
    - Playwright scrolls to trigger lazy-loading of image thumbnails.
    - Full-size image URLs are extracted from the page's JSON data (murl
      attributes in .iusc elements).
    """

    async with async_playwright() as p:
        # headless=False is the KEY to bypassing anti-bot
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})

        encoded = urllib.parse.quote(query)
        await page.goto(
            f'https://www.bing.com/images/search?q={encoded}&form=HDRSC2',
            timeout=30000
        )
        print(f"[INFO] 页面标题: {await page.title()}", flush=True)

        # Wait for initial render
        await page.wait_for_timeout(3000)

        # Scroll to trigger lazy image loading
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1000)

        # Extract full-size image URLs from Bing's in-page JSON data
        img_data = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('.iusc').forEach(el => {
                try {
                    const m = JSON.parse(el.getAttribute('m'));
                    if (m && m.murl && results.length < 15) {
                        results.push({
                            url: m.murl,
                            title: m.t || '',
                            thumb: m.turl || '',
                            w: m.w || 0,
                            h: m.h || 0
                        });
                    }
                } catch(e) {}
            });
            return results;
        }""")

        print(f"[INFO] 找到 {len(img_data)} 张图片", flush=True)

        if not img_data:
            print("[ERROR] 未找到图片，可能页面结构已变更", flush=True)
            await browser.close()
            return []

        # Display and optionally download
        results = []
        for i, img in enumerate(img_data[:max_results]):
            title = img.get('title', '') or f'image_{i+1}'
            url = img.get('url', '')
            print(f"[IMG {i+1}] {title[:60]}", flush=True)
            print(f"       {url[:150]}", flush=True)
            if img.get('w'):
                print(f"       尺寸: {img['w']}x{img['h']}", flush=True)

            results.append({"title": title, "url": url, "index": i + 1})

        if download and results:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            import urllib.request
            for r in results:
                safe_name = "".join(c for c in r['title'][:30] if c.isalnum() or c in ' _-')
                ext = '.jpg'
                filename = f"{r['index']:02d}_{safe_name}{ext}"
                filepath = output_path / filename

                try:
                    urllib.request.urlretrieve(r['url'], filepath)
                    print(f"[DL] 下载成功: {filepath}", flush=True)
                except Exception as e:
                    print(f"[DL] 下载失败 {r['url'][:50]}: {e}", flush=True)

        print("[DONE] 关闭浏览器窗口结束程序", flush=True)

        # Keep alive until user closes browser
        while True:
            try:
                await asyncio.sleep(1)
            except:
                break

        await browser.close()
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Bing Image Search & Download")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--download", action="store_true", help="下载图片到本地")
    parser.add_argument("--output", "-o", default=".", help="下载目录 (默认当前目录)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="最大结果数 (默认10)")
    args = parser.parse_args()

    asyncio.run(search_images(args.query, args.limit, args.download, args.output))
