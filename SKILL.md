---
name: relay-scraper
description: >
  MUST USE when user needs images from any website. Auto-extracts images;
  on CAPTCHA/block/no-results → hands browser to user, waits for them
  to help, then continues.
triggers:
  - image: 配图/图片/图/找图/搜图/照片/插图/插画/image/picture/photo/illustration
  - fail: 搜不到/找不到/图不对/空白/没找到/没有图/扒图/采集/人机验证/captcha/被墙/403
  - action: 接力/手动/协作/交互/你浏览我提取/帮我看看
metadata:
  type: skill
  platforms: windows
---

# 接力爬虫 — 人机协作图片采集

## 核心理念

```
你(用户)         我(AI)          浏览器
 │                │               │
 │  "搜猫图"      │               │
 │ ─────────────→ │               │
 │                │──打开Google──→│
 │                │  滚动/提取     │
 │                │←───空结果─────│
 │                │  🤖 人机验证   │
 │  ← 交给你 ──── │               │
 │──解决验证码──→ │               │
 │                │──继续提取────→│
 │                │←───15张图────│
 │ ← 展示结果 ─── │               │
```

**我能干的：** 打开浏览器 → 导航 → 等待 → 滚动 → 提取 → 下载
**留给你的：** 人机验证 / 登录 / 被墙 / 搜不到 / 防盗链

## 接力规则

| 状况 | 我做什么 | 你做什么 |
|------|---------|---------|
| ✅ 正常搜到图 | 自动提取 + 下载 | 关浏览器 |
| 🤖 人机验证 | 弹出窗口等你解决 | 点点点过验证 |
| 🚫 被拦截/403 | 交给你处理 | 换方式访问 |
| 🕳️ 没有结果 | 你手动搜一下 | 搜完按回车 |
| 🖱️ 手动模式 (-m) | 等你浏览完按回车 | 自己逛 → 回车 |
| 🔒 下载失败 | 提示防盗链 | 手动打开链接 |

## 使用

```bash
# Bing 搜图（自动，默认）
python scraper.py "Michael Jackson"

# Google 搜图（遇到验证码会等你）
python scraper.py "猫" -e google

# 百度搜图
python scraper.py "山水画" -e baidu

# 扒任意网页的图
python scraper.py --url "https://example.com"

# 手动模式：你浏览我提取（循环接力）
python scraper.py --url "https://pixiv.net" --manual

# 搜 + 下载
python scraper.py "wallpaper" --download -o ./pics

# 自定义数量
python scraper.py "风景" -n 50 --download
```

## 安装

```bash
pip install playwright
playwright install chromium
```
