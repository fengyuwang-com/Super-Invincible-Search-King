#!/usr/bin/env python3
"""
opencli 浏览器抓取模块 — 可选扩展插件，给 Search-King 提供真实浏览器抓取能力。
通过 opencli 调用系统的 Edge 浏览器（保持真实用户会话），绕过 Playwright 难以处理的 WAF/反爬。

依赖: opencli（可选），yt-dlp（可选，仅音频下载需要）
"""

import subprocess, json, time, sys, os, re, random

# ── 可用性检测 ──

def check_opencli():
    """检测 opencli 是否可用"""
    try:
        result = subprocess.run(["opencli", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_ytdlp():
    """检测 yt-dlp 是否可用"""
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ── 浏览器控制 ──

def browser_eval(session, js):
    """在 opencli 浏览器中执行 JS，返回 stdout"""
    cmd = f'opencli browser {session} eval {json.dumps(js)}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout


def browser_nav(session, url):
    """让 opencli 浏览器导航到 URL"""
    cmd = f'opencli browser {session} open {json.dumps(url)}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    return result.returncode == 0


def get_session(session="king_fetch"):
    """获取现有 opencli 浏览器会话，没有则创建"""
    cmd = f'opencli browser {session} eval "location.href"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    if result.returncode == 0 and result.stdout.strip():
        return session
    # 会话不存在，尝试创建（通过 open --new）
    cmd = f'opencli browser --new {session} 2>&1'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    if result.returncode == 0:
        return session
    return None


# ── 雪球抓取 ──

def xueqiu_posts(user_id, max_pages=99, session="king_fetch"):
    """
    抓取雪球用户时间线全部帖子，支持分页。
    遇到 WAF 反爬时会在控制台提示，等待用户手动处理验证码后继续。

    返回: [{id, text, created_at, type}, ...]
    """
    if not check_opencli():
        print("❌ opencli 未安装。安装: npm install -g opencli")
        return []

    sess = get_session(session)
    if not sess:
        print("❌ 无法创建 opencli 浏览器会话")
        return []

    all_posts = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        api_url = f"https://xueqiu.com/v4/statuses/user_timeline.json?user_id={user_id}&page={page}"

        print(f"\n📄 第 {page} 页...", end=" ", flush=True)

        # 用浏览器直接打开 API URL（比 eval fetch 更稳定，不触发 XHR 检测）
        browser_nav(sess, api_url)
        time.sleep(2)

        # 提取页面内容（API 返回 JSON 或 WAF 页面）
        js = """
        (function() {
            var text = document.body.innerText;
            // 检查是不是 WAF 页面
            if (text.includes('验证') || text.includes('captcha') || text.includes('captcha')) {
                return JSON.stringify({waf: true, text: text.substring(0, 500)});
            }
            // 尝试解析 JSON
            try {
                var data = JSON.parse(text);
                return JSON.stringify({waf: false, data: data});
            } catch(e) {
                // 可能是 WAF 的 HTML 页面
                return JSON.stringify({waf: true, text: text.substring(0, 500)});
            }
        })()
        """
        out = browser_eval(sess, js)

        # 解析结果
        result = None
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('{"waf"') or line.startswith('{"data"'):
                try:
                    result = json.loads(line)
                except json.JSONDecodeError:
                    pass
                break

        if result and result.get('waf'):
            print(f"🤖 遇到 WAF 人机验证！", flush=True)
            print(f"   页面: {result.get('text', '')[:100]}", flush=True)
            print(f"   请在浏览器中完成验证，完成后按 Enter 继续...", flush=True)
            input()
            # 重新加载当前页
            browser_nav(sess, api_url)
            time.sleep(3)
            out = browser_eval(sess, js)
            for line in out.split('\n'):
                if line.startswith('{"waf"') or line.startswith('{"data"'):
                    try:
                        result = json.loads(line)
                    except:
                        pass
                    break

        if result and not result.get('waf'):
            data = result.get('data', {})
            posts = data.get('posts', []) if isinstance(data, dict) else \
                    (data if isinstance(data, list) else [])
            if not posts:
                print("无更多帖子")
                break

            # 去重
            new_posts = [p for p in posts if p.get('id') not in seen_ids]
            for p in posts:
                seen_ids.add(p.get('id'))
            all_posts.extend(new_posts)
            print(f"+{len(new_posts)} 条（累计 {len(all_posts)}）", flush=True)

            # 检查是否最后一页
            if len(posts) < 20:
                print("已到末尾")
                break
        else:
            print(f"⚠️ 解析失败，可能是 WAF 拦截", flush=True)
            print(f"   输入 'r' 重试，Enter 跳过，'done' 退出: ", end="", flush=True)
            choice = input().strip().lower()
            if choice == 'done':
                break
            elif choice == 'r':
                continue
            else:
                break

        # 页间延迟，避免触发反爬
        time.sleep(2 + random.random() * 3)

    print(f"\n✅ 雪球抓取完成: 共 {len(all_posts)} 条帖子")
    return all_posts


# ── B 站抓取 ──

def bilibili_videos(mid, max_pages=12, session="king_fetch"):
    """
    抓取 B 站用户空间全部视频列表。
    通过分页按钮抓取每页 BV ID + 标题。

    返回: [{bv, title}, ...]
    """
    if not check_opencli():
        print("❌ opencli 未安装。安装: npm install -g opencli")
        return []

    sess = get_session(session)
    if not sess:
        print("❌ 无法创建 opencli 浏览器会话")
        return []

    space_url = f"https://space.bilibili.com/{mid}/video"
    print(f"📺 打开 B 站空间: {space_url}", flush=True)
    browser_nav(sess, space_url)
    time.sleep(5)

    all_videos = {}
    total_videos = 0

    for page in range(1, max_pages + 1):
        print(f"\n📄 第 {page} 页...", end=" ", flush=True)

        if page > 1:
            js = f"""
            (function() {{
                var btns = document.querySelectorAll('.vui_pagenation--btn-num');
                for (var i = 0; i < btns.length; i++) {{
                    if (btns[i].textContent.trim() === '{page}') {{
                        btns[i].click();
                        return true;
                    }}
                }}
                var moreBtn = document.querySelector('.vui_pagenation--btn-mor');
                if (moreBtn) {{
                    moreBtn.click();
                    setTimeout(function() {{
                        var btns2 = document.querySelectorAll('.vui_pagenation--btn-num');
                        for (var j = 0; j < btns2.length; j++) {{
                            if (btns2[j].textContent.trim() === '{page}') {{
                                btns2[j].click();
                            }}
                        }}
                    }}, 500);
                    return true;
                }}
                return false;
            }})()
            """
            out = browser_eval(sess, js)
            time.sleep(3)

        js = """
        (function() {
            var links = document.querySelectorAll('a[href*="/video/BV"]');
            var seen = {};
            links.forEach(function(a) {
                var href = a.getAttribute('href');
                var match = href.match(/BV[A-Za-z0-9]+/);
                var title = a.textContent.trim();
                if (match) {
                    if (!seen[match[0]]) seen[match[0]] = '';
                    if (title && title.length > 2) seen[match[0]] = title.substring(0, 100);
                }
            });
            return JSON.stringify(seen);
        })()
        """
        out = browser_eval(sess, js)

        page_videos = {}
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('{') and '}' in line:
                try:
                    page_videos = json.loads(line)
                except:
                    pass

        if not page_videos:
            print("无更多视频")
            break

        new_count = 0
        for bv, title in page_videos.items():
            if bv not in all_videos:
                all_videos[bv] = title
                new_count += 1
        print(f"+{new_count} 新（累计 {len(all_videos)}）", flush=True)

    print(f"\n✅ B 站抓取完成: 共 {len(all_videos)} 个视频")
    return [{"bv": bv, "title": title} for bv, title in sorted(all_videos.items())]


def bilibili_audio(mid, output_dir=None, quality="9", session="king_fetch"):
    """
    抓取 B 站用户全部视频并下载音频。
    quality: 0(最高)~9(最低)，讲课内容推荐 9（约 65kbps，足够清晰）
    """
    if not check_ytdlp():
        print("❌ yt-dlp 未安装。安装: pip install yt-dlp")
        return []

    videos = bilibili_videos(mid, session=session)
    if not videos:
        print("❌ 没有视频可下载")
        return []

    if not output_dir:
        output_dir = os.path.join(os.getcwd(), f"bilibili_audio_{mid}")

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🎵 下载 {len(videos)} 个视频音频到 {output_dir}")
    print(f"   质量: V{quality}（0=最高 ~245kbps, 9=最低 ~65kbps）")
    print(f"   并行: 8 线程")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    success = 0
    failed = 0
    done = 0
    total = len(videos)

    def download_one(video):
        nonlocal success, failed, done
        bv = video['bv']
        title = video.get('title', '')
        url = f"https://www.bilibili.com/video/{bv}"
        out_path = os.path.join(output_dir, f"{bv}.mp3")

        if os.path.exists(out_path):
            done += 1
            success += 1
            return f"SKIP {bv}"

        try:
            result = subprocess.run([
                'yt-dlp', '-x', '--audio-format', 'mp3', '--audio-quality', quality,
                '-o', os.path.join(output_dir, '%(id)s.%(ext)s'),
                url
            ], capture_output=True, text=True, timeout=600)

            done += 1
            if result.returncode == 0:
                success += 1
                # 重命名以包含标题
                safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:60]
                if safe_title:
                    plain = os.path.join(output_dir, f"{bv}.mp3")
                    named = os.path.join(output_dir, f"{bv}_{safe_title}.mp3")
                    if os.path.exists(plain) and not os.path.exists(named):
                        os.rename(plain, named)
                pct = done / total * 100
                return f"[{done}/{total} {pct:.0f}%] OK {bv} {title[:40]}"
            else:
                failed += 1
                return f"[{done}/{total}] FAIL {bv}"
        except Exception as e:
            done += 1
            failed += 1
            return f"[{done}/{total}] ERROR {bv}: {e}"

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_one, v): v for v in videos}
        for f in as_completed(futures):
            print(f"  {f.result()}", flush=True)
            time.sleep(0.5)  # 稍微错开并发日志

    print(f"\n✅ 音频下载完成: {success} OK, {failed} FAIL")
    return videos


# ── 通用页面抓取 ──

def read_page(url, session="king_fetch", scroll=False):
    """
    用 opencli 浏览器打开 URL 并提取正文。
    适合 Playwright 搞不定的反爬网站（WAF、Cloudflare 等）。
    scroll: 自动滚动到底部（针对懒加载页面）

    返回: {title, url, content, screenshot_base64?}
    """
    if not check_opencli():
        print("❌ opencli 未安装。安装: npm install -g opencli")
        return None

    sess = get_session(session)
    if not sess:
        print("❌ 无法创建 opencli 浏览器会话")
        return None

    print(f"📖 [opencli] {url}", flush=True)
    browser_nav(sess, url)
    time.sleep(3)

    if scroll:
        print("   ⏳ 滚动加载...", flush=True)
        for _ in range(5):
            browser_eval(sess, "window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)

    js = """
    (function() {
        var title = document.title;
        var text = document.body.innerText || '';
        // 检测是否被拦截
        var blocked = text.includes('验证') || text.includes('captcha') ||
                      text.toLowerCase().includes('access denied') ||
                      text.toLowerCase().includes('please verify');
        return JSON.stringify({
            title: title,
            content: text.substring(0, 50000),
            blocked: blocked,
            url: location.href
        });
    })()
    """
    out = browser_eval(sess, js)

    for line in out.split('\n'):
        line = line.strip()
        if line.startswith('{') and '"title"' in line:
            try:
                return json.loads(line)
            except:
                pass

    return {"title": "", "content": "", "blocked": True, "url": url}


# ── 命令行入口（独立使用）──

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="opencli 浏览器抓取工具")
    parser.add_argument("--xueqiu", type=int, help="雪球用户 ID")
    parser.add_argument("--bilibili", type=int, help="B 站用户 mid")
    parser.add_argument("--read", help="通用页面抓取")
    parser.add_argument("--scroll", action="store_true", help="页面滚动（配合 --read）")
    parser.add_argument("--pages", type=int, default=99, help="最大页数（雪球）")
    parser.add_argument("--audio", action="store_true", help="下载 B 站音频")
    parser.add_argument("--output", "-o", help="音频输出目录")
    parser.add_argument("--quality", default="9", help="音频质量 0-9")
    parser.add_argument("--session", default="king_fetch", help="opencli 浏览器会话名")
    args = parser.parse_args()

    if args.xueqiu:
        xueqiu_posts(args.xueqiu, args.pages, args.session)
    elif args.bilibili:
        if args.audio:
            bilibili_audio(args.bilibili, args.output, args.quality, args.session)
        else:
            videos = bilibili_videos(args.bilibili, session=args.session)
            print(f"\n共 {len(videos)} 个视频:")
            for v in videos:
                print(f"  {v['bv']}  {v.get('title', '')[:60]}")
    elif args.read:
        result = read_page(args.read, args.session, args.scroll)
        if result:
            print(f"标题: {result.get('title', '')}")
            print(f"被拦截: {result.get('blocked', False)}")
            content = result.get('content', '')
            if content:
                lines = content.split('\n')
                for line in lines[:100]:
                    print(line)
    else:
        parser.print_help()
