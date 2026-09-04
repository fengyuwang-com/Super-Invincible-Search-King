---
name: search-king
description: >
  MUST USE when user needs ANY search — images, text, or webpage content.
  Multi-source concurrent merge: baidu + ddg + tinyfish + searxng (Google CSE).
  Zero API keys, zero Docker, works out-of-the-box.
triggers:
  - search: 搜索/搜图/搜文字/搜网页/查资料/找资源/调研/研究/查询/情报/报告/找信息/搜集/采集
  - image: 配图/图片/找图/搜图/照片/插图/image/picture/photo
  - text: 文字/搜索结果/文章/内容/正文/title/link/snippet
  - fail: 搜不到/找不到/没结果/captcha/被墙/403/反爬
  - action: 接力/手动/协作/你浏览我提取
metadata:
  type: skill
  platforms: windows
---

# Search King

位置：`scraper.py`（相对于本 SKILL.md 所在目录）

## 三种模式

### 🔍 搜文字（默认 AI 搜索）

```bash
python scraper.py --search "关键词"
```

**4 源并发合并**：`baidu_lite` + `ddg_lite` + `tinyfish` + `searxng`（含 Google CSE）。
所有引擎同时跑，全部等齐后合并去重。超时 35s。单源失败不影响其他源。

### 🔎 搜图

```bash
python scraper.py "关键词"
```

12 引擎链：Unsplash → Pexels → Pixabay → Burst → Bing → Baidu → Brave → DDG → Yandex → Sogou → 360 → Google。

### 📖 读网页

```bash
python scraper.py --read URL1 URL2 URL3
```

多 URL 并行、CloakBrowser 反检测、验证码自动切手动。

## 后端

| 后端 | 用途 | 依赖 |
|------|------|------|
| `--backend edge`（默认） | 系统 Edge | 无 |
| `--backend chromium` | Playwright Chromium | `playwright install chromium` |
| `--backend cloak` | CloakBrowser 反检测 | `pip install cloakbrowser` |
| `--backend lite` | 纯 HTTP（仅文字搜索） | 无 |
| `--backend opencli` | 真实 Edge 浏览器 | `npm install -g opencli` |
| `--backend manual` | 你浏览我提取 | 无 |

## 增强模式

```bash
python scraper.py --search "关键词" --deep
```

5 跳降级流水线：多源直连 → 浏览器引擎链 → CloakBrowser → TinyFish → 手动。

## 使用示例

```bash
# 搜文字（推荐，AI 用这个）
python scraper.py --search "AI 怎么接搜索引擎"

# 搜图
python scraper.py "风景" --download -o pics

# 读网页
python scraper.py --read "https://example.com"

# 反检测
python scraper.py --search "AI" --backend cloak

# 指定引擎
python scraper.py --search "AI" -e baidu-web,ddg-web

# B 站视频
python scraper.py --backend opencli --fetch bilibili --mid 123 --series
```

## 接力规则

| 状况 | 行为 |
|------|------|
| 引擎出结果 | 自动提取 |
| 人机验证/拦截 | 跳过，换下一个引擎 |
| 所有引擎全挂 | `--deep` 模式自动降级；默认模式提示 |
| 读网页遇验证码 | 切手动模式，等用户处理 |
