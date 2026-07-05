#!/usr/bin/env python3
"""
接力爬虫 — 人机协作的网页图片采集器
====================================

核心模式：自动 → 卡住 → 交给你 → 继续

我能干的：
  - 打开浏览器搜图（Bing/Google/百度/任意网页）
  - 等待页面加载，滚动触发懒加载
  - 自动提取图片 URL
  - 下载到本地

我搞不定交给你的：
  - 🤖 人机验证（CAPTCHA）→ 弹出浏览器，你解决，按回车我继续
  - 🕳️ 搜不到图（空白页/零结果）→ 你手动搜，完事告诉我
  - 🔒 403 下载失败 → 你手动打开图片页，我重新取链接
  - 🖱️ 你想自己浏览 → 交互模式，你边看我边取

使用示例：

    # 全自动：Bing 搜图
    python scraper.py "富春山居图"

    # 搜 + 下载
    python scraper.py "Michael Jackson" --download

    # 扒任意网页
    python scraper.py --url "https://example.com/gallery"

    # 指定搜索引擎
    python scraper.py "猫" --engine baidu

    # 纯手动：你浏览我提取（循环接力）
    python scraper.py --url "https://example.com" --manual

    # 指定下载目录和图片数量
    python scraper.py "风景" -n 30 --download -o ./wallpapers
"""

import asyncio, json, os, sys, argparse, urllib.request, urllib.parse, re, time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright, TimeoutError


# ============================================================
# 搜索引擎配置
# ============================================================

ENGINES = {
    "bing": {
        "name": "Bing Images",
        "url": "https://www.bing.com/images/search?q={q}&form=HDRSC2",
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
}


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
    """等待用户操作。返回 False 表示浏览器已关闭。"""
    print(f"\n🟡 {prompt_msg}", flush=True)
    print("   操作完成后按 Enter 继续...", flush=True)
    while True:
        try:
            # 检测浏览器是否还活着
            if check_closed:
                _ = await page.title()
        except:
            print("   🔴 浏览器已关闭", flush=True)
            return False

        # 检查是否有输入（非阻塞）
        import select
        if sys.stdin in select.select([sys.stdin], [], [], 0.5)[0]:
            sys.stdin.readline()
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


def download_images(images, output_dir, max_count=15):
    """下载图片，返回成功/失败列表"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for i, img in enumerate(images[:max_count]):
        title = re.sub(r'[<>:"/\\|?*]', '', (img.get("title") or "")[:40]) or f"image_{i+1}"
        fname = f"{i+1:02d}_{title}.jpg"
        fpath = out / fname
        try:
            req = urllib.request.Request(img["url"], headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(fpath, "wb") as f:
                    f.write(resp.read())
            print(f"  [DL] ✅ {fname}", flush=True)
            results.append({"file": str(fpath), "ok": True})
        except Exception as e:
            print(f"  [DL] ❌ {fname}: {str(e)[:50]}", flush=True)
            results.append({"file": img["url"], "ok": False, "error": str(e)[:50]})
    return results


async def run(query=None, engine="bing", url=None, max_count=15,
              download=False, output_dir=".", manual=False, min_size=100):
    """主循环：自动 → 卡住 → 交给你 → 继续"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})

        # ----- 阶段1：导航 -----
        if url:
            print(f"\n🔵 [导航] 打开网页: {url}", flush=True)
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        elif query and engine in ENGINES:
            info = ENGINES[engine]
            page_url = info["url"].format(q=urllib.parse.quote(query))
            print(f"\n🔵 [导航] {info['name']}: {query}", flush=True)
            await page.goto(page_url, timeout=60000, wait_until="domcontentloaded")
        else:
            print("需要 --query 或 --url", flush=True)
            await browser.close()
            return

        # ----- 阶段2：自动尝试 -----
        images = []
        await page.wait_for_timeout(3000)

        # 检查是否被拦截
        page_text = await page.inner_text("body") if await page.query_selector("body") else ""
        if detect_captcha(page_text):
            await wait_for_user_input(page, f"🤖 人机验证！请在浏览器中完成验证")
        elif detect_blocked(page_text):
            await wait_for_user_input(page, f"🚫 被拦截了！请在浏览器中处理")

        # 如果是手动模式，直接交给你
        if manual:
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
            return

        # ----- 自动模式：滚动加载 + 引擎提取 -----
        print("   ⏳ 加载中...", flush=True)

        for i in range(5):
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1000)

        # 引擎专用提取
        if engine in ENGINES:
            images = await page.evaluate(ENGINES[engine]["extract"])

        # 如果引擎提取失败，走通用方法
        if not images:
            print("   ⚠️ 引擎提取没拿到结果，尝试通用方法...", flush=True)
            images = await extract_images(page, min_size, max_count)

        # ----- 阶段3：卡住了？交给你 -----
        if not images:
            print("\n🕳️ 没找到图片！可能是:", flush=True)
            print("   1. 页面加载慢 → 等会儿再试", flush=True)
            print("   2. 需要登录 → 你手动登录", flush=True)
            print("   3. 搜索词不对 → 你重新搜", flush=True)
            await wait_for_user_input(page, "浏览器交给你了，找到图后按 Enter 我来提取")
            images = await extract_images(page, min_size, max_count)

        # ----- 阶段4：展示 & 下载 -----
        if images:
            print(f"\n📸 共找到 {len(images)} 张图片", flush=True)
            for i, img in enumerate(images[:max_count]):
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

                # 有失败的？交给你
                if fail_count > 0:
                    print("\n🔒 有些图下载失败（403/404），可能防盗链", flush=True)
                    print("   你可以手动在浏览器里打开这些页面", flush=True)
        else:
            print("\n😅 最终还是没找到图片", flush=True)

        # ----- 阶段5：保持浏览器打开，等你关闭 -----
        print(f"\n{'='*50}", flush=True)
        print("✅ 完成！关闭浏览器窗口退出", flush=True)
        print(f"{'='*50}", flush=True)

        while True:
            try:
                await asyncio.sleep(1)
            except:
                break

        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="接力爬虫 — 人机协作图片采集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="搜索关键词")
    parser.add_argument("--engine", "-e", choices=list(ENGINES.keys()),
                        default="bing", help="搜索引擎")
    parser.add_argument("--url", "-u", help="目标网页 URL")
    parser.add_argument("--download", "-d", action="store_true", help="下载图片")
    parser.add_argument("--output", "-o", default=".", help="下载目录")
    parser.add_argument("--limit", "-n", type=int, default=15, help="最大图片数")
    parser.add_argument("--min-size", type=int, default=100, help="最小图片宽度")
    parser.add_argument("--manual", "-m", action="store_true",
                        help="手动模式：你浏览我提取")
    args = parser.parse_args()

    if not args.query and not args.url:
        parser.print_help()
        sys.exit(1)

    asyncio.run(run(
        query=args.query, engine=args.engine, url=args.url,
        max_count=args.limit, download=args.download,
        output_dir=args.output, manual=args.manual, min_size=args.min_size,
    ))
