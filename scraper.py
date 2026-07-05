#!/usr/bin/env python3
"""
接力爬虫 — 人机协作的网页图片采集器
====================================

核心模式：自动 → 卡住 → 交给你 → 继续

我能干的：
  - 打开浏览器搜图（Bing/百度/Yandex/DuckDuckGo/Brave/搜狗/360/Google/任意网页）
  - 自动引擎链：一个不行换下一个，直到出图
  - 等待页面加载，滚动触发懒加载
  - 自动提取图片 URL
  - 下载到本地

我搞不定交给你的：
  - 🤖 人机验证（CAPTCHA）→ 跳过，换下一个引擎试
  - 🕳️ 所有引擎都搜不到图 → 弹出浏览器，你手动搜
  - 🔒 403 下载失败 → 你手动打开图片页，我重新取链接
  - 🖱️ 你想自己浏览 → 交互模式，你边看我边取

使用示例：

    # 全自动：Bing → 百度 → Yandex → ... 挨个试
    python scraper.py "富春山居图"

    # 搜 + 下载
    python scraper.py "Michael Jackson" --download

    # 扒任意网页
    python scraper.py --url "https://example.com/gallery"

    # 指定搜索引擎
    python scraper.py "猫" --engine baidu

    # 自定义引擎链
    python scraper.py "乔丹" -e bing,baidu

    # 纯手动：你浏览我提取（循环接力）
    python scraper.py --url "https://example.com" --manual

    # 指定下载目录和图片数量
    python scraper.py "风景" -n 30 --download -o ./wallpapers
"""

import asyncio, json, os, sys, argparse, urllib.request, urllib.parse, re, time, hashlib, concurrent.futures
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright, TimeoutError


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
    """等待用户操作（Windows 兼容）。返回 False 表示浏览器已关闭。"""
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
    """尝试一个搜索引擎。成功返回带标记的图片列表，失败返回 None。"""
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

    # 给每张图打上来源标记
    for img in images:
        img["_engine"] = eng
        img["_license"] = info.get("license", LICENSE_UNKNOWN)

    return images


async def run(query=None, engines=None, url=None, max_count=5,
              download=False, output_dir=".", manual=False, min_size=100, free_only=False):
    """主循环：引擎链 → 自动试 → 全挂 → 交给你"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})

        images = []

        # ----- URL模式：打开指定网页 -----
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

        # ----- 引擎链模式：挨个试，全部收集 -----
        elif query and engines:
            for eng in engines:
                result = await try_engine(page, eng, query, min_size, max_count)
                if result:
                    images.extend(result)
                    print(f"\n✅ [{ENGINES[eng]['name']}] {len(result)} 张图", flush=True)
                else:
                    print(f"   ❌ [{ENGINES[eng]['name']}] 没出图", flush=True)

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="接力爬虫 — 人机协作图片采集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="搜索关键词")
    parser.add_argument("--engine", "-e", default=",".join(FALLBACK_CHAIN),
                        help=f"搜索引擎或链（逗号分隔），默认: {','.join(FALLBACK_CHAIN)}")
    parser.add_argument("--url", "-u", help="目标网页 URL")
    parser.add_argument("--free", action="store_true",
                        help=f"仅用免费摄影站: {', '.join(FREE_SITE_KEYS)}")
    parser.add_argument("--download", "-d", action="store_true", help="下载图片")
    parser.add_argument("--output", "-o", default=".", help="下载目录")
    parser.add_argument("--limit", "-n", type=int, default=5, help="最大图片数")
    parser.add_argument("--min-size", type=int, default=100, help="最小图片宽度")
    parser.add_argument("--manual", "-m", action="store_true",
                        help="手动模式：你浏览我提取")
    args = parser.parse_args()

    if not args.query and not args.url:
        parser.print_help()
        sys.exit(1)

    # 解析引擎链
    engine_ids = [e.strip() for e in args.engine.split(",") if e.strip()]

    # --free 模式：只用免费摄影站
    if args.free:
        engine_ids = FREE_SITE_KEYS.copy()

    valid_engines = [e for e in engine_ids if e in ENGINES]
    if not valid_engines:
        print(f"❌ 无效引擎: {args.engine}，可用: {', '.join(ENGINES.keys())}", flush=True)
        sys.exit(1)

    # 打印许可证摘要
    free_count = sum(1 for e in valid_engines if ENGINES[e].get("license", "").startswith("✅"))
    unknown_count = sum(1 for e in valid_engines if ENGINES[e].get("license", "").startswith("⚠️"))
    print(f"🔍 引擎: {', '.join(ENGINES[e]['name'] for e in valid_engines)}", flush=True)
    if free_count:
        print(f"✅ {free_count} 个免费摄影站（可商用）", flush=True)
    if unknown_count:
        print(f"⚠️ {unknown_count} 个搜索引擎（版权未知，自行核实）", flush=True)

    asyncio.run(run(
        query=args.query, engines=valid_engines, url=args.url,
        max_count=args.limit, download=args.download,
        output_dir=args.output, manual=args.manual, min_size=args.min_size, free_only=args.free,
    ))
