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

**4 源并发合并**：`baidu_lite` + `ddg_lite` + `tinyfish` + `searxng`（含 Google CSE、Brave）。
所有引擎同时跑，全部等齐后合并去重。超时 35s。单源失败不影响其他源。

输出首行会打印各源贡献数，例如：
```
🔍 4源合并: 共8条（baidu 5、ddg 5、searxng 5）
```
**没有这一行 = 聚合没生效**，说明你落进了单源分支，见下方「⚠️ 常见误区」。

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

## ⚠️ 常见误区（踩过的坑）

### 误区 1：`--backend lite` 不是「聚合的快速版」

| 命令 | 实际行为 |
|------|---------|
| `--search "关键词"` | ✅ 4 源聚合（含 SearXNG/Google CSE/Brave） |
| `--search "关键词" --backend lite` | ⚠️ **只走 DDG 单源**（纯 HTTP，无浏览器） |
| `--search "关键词" --backend edge` | ✅ 同默认，4 源聚合 |
| `--search "关键词" -e baidu-web,ddg-web` | ⚠️ 只用你指定的引擎，不走聚合 |

源码依据：`scraper.py:1923` 的 `--backend lite` 分支直接调 `ddg_lite_search()`；
聚合入口在 `scraper.py:1937`（`--backend edge` 且未传 `-e` 时调 `simple_dual_source_search()`）。
所以**想要聚合就别传 `--backend`、别传 `-e`**。

### 误区 2：SearXNG 没装好会静默降级

`searxng_search()` 初始化失败时**不报错、静默返回空**（源码 `scraper.py:1241` 的
`except Exception: _searxng_app = False`），于是聚合看起来正常、实则少一路源。
判断方法就是看开头那行 `🔍 N源合并` 里有没有 `searxng`。

## SearXNG 配置（聚合搜索的前提）

SearXNG 是 in-process 调用的（无需启动 HTTP 服务），但需要三样东西就位：

### 1. 源码目录（按优先级自动发现）

| 顺序 | 位置 | 说明 |
|------|------|------|
| 1 | `$SEARXNG_SRC` 环境变量 | 显式指定 |
| 2 | `C:\FengProj\searxng-src` | **本项目实际使用**（Search-King 的兄弟目录） |
| 3 | `~/searxng-src` | 家目录 |

克隆方式：
```bash
git clone --depth 1 https://github.com/searxng/searxng.git C:/FengProj/searxng-src
```

### 2. settings 目录

`_find_searxng_settings()` 只在**源码目录下**找这两处：

```
C:\FengProj\searxng-src\searxng-settings\settings.yml   ← 实际使用
C:\FengProj\searxng-src\searxng\settings\
```

注意它**不会**去找 `Search-King\searxng\settings-win.yml`（那是给
`start_searxng.bat` 独立启动用的）。所以要把配置拷一份到上面那个路径。

### 3. Windows 上的三个必需修补

原生 SearXNG 在 Windows 跑不起来，需要：

**a. 装依赖**
```bash
python -m pip install -r C:/FengProj/searxng-src/requirements.txt
```

**b. `pwd` shim**（Windows 没有 `pwd` 模块，`searx/valkeydb.py:22` 会 ImportError）
已创建：`C:\FengProj\searxng-src\pwd.py`

**c. settings.yml 的 `secret_key` 不能是占位符**
`searx/webapp.py:1358` 检测到 `ultrasecretkey` 会 `sys.exit(1)`，
进程静默退出（**不报错，看不到 traceback**）。必须写一个真实值。

### 一键自检

```bash
cd C:/FengProj/Search-King && python scraper.py --search "test"
```
看到 `🔍 4源合并: ... searxng N` 即为正常。

## 后端

| 后端 | 用途 | 依赖 |
|------|------|------|
| （不传，默认聚合） | **4 源并发合并，推荐** | SearXNG 配置见上 |
| `--backend edge` | 系统 Edge；未传 `-e` 时同样走聚合 | 无 |
| `--backend chromium` | Playwright Chromium | `playwright install chromium` |
| `--backend cloak` | CloakBrowser 反检测 | `pip install cloakbrowser` |
| `--backend lite` | 纯 HTTP **单源 DDG** | 无 |
| `--backend opencli` | 真实 Edge 浏览器 | `npm install -g opencli` |
| `--backend manual` | 你浏览我提取 | 无 |

## 增强模式

```bash
python scraper.py --search "关键词" --deep
```

5 跳降级流水线：多源直连 → 浏览器引擎链 → CloakBrowser → TinyFish → 手动。

## 使用示例

```bash
# 搜文字（推荐，AI 用这个 —— 4 源聚合）
python scraper.py --search "AI 怎么接搜索引擎"

# 搜图
python scraper.py "风景" --download -o pics

# 读网页
python scraper.py --read "https://example.com"

# 反检测
python scraper.py --search "AI" --backend cloak

# 指定引擎（注意：这样就不走聚合了）
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
