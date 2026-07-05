---
name: bing-image-finder
description: >
  MUST USE when the user needs to search for images / find images to go with text /
  download pictures from the internet. Especially useful when simple web scraping
  fails (returns empty/wrong results).
triggers:
  - image: 配图/图片/图/找图/搜图/照片/插图/插画/image/picture/photo/illustration
  - search: 搜不到/找不到/图不对/空白/没找到/没有图
  - tool: bing/必应/playwright/浏览器
metadata:
  type: skill
  platforms: windows
---

# Bing Image Finder — 绕过反爬的图片搜索技巧

## 背景问题

普通方式搜图（curl / requests / Jina Reader）经常失败：
- Google/Bing/百度 的图片搜索**依赖 JavaScript 动态加载**
- 简单 HTTP 请求只拿到空壳页面，没有图片数据
- 返回的图片经常"不对题"或"空白"

## 解决方案

**Playwright + 有头浏览器模式**（`headless=False`）

### 为什么能绕过反爬？

| 反爬手段 | 有头浏览器 | 无头浏览器 | curl/wget |
|---------|-----------|-----------|-----------|
| WebGL fingerprint | ✅ 真实 GPU | ⚠️ 模拟 | ❌ |
| navigator.webdriver | ✅ false | ⚠️ 可检测 | ❌ |
| JavaScript 渲染 | ✅ 完整 | ✅ 完整 | ❌ 空壳 |
| 屏幕分辨率 | ✅ 真实 | ❌ 默认800x600 | ❌ |
| TLS 指纹 | ✅ Chrome 原生 | ✅ Chrome 原生 | ⚠️ Python/curl |

**关键点：** 搜索引擎的反爬策略主要针对无头浏览器和脚本请求。非无头模式（`headless=False`）下，浏览器指纹与真实用户无异，不会被拦截。

## 如何使用

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 搜索图片

```bash
# 搜索并显示结果
python bing_image_search.py "富春山居图 黄公望"

# 搜索并自动下载图片
python bing_image_search.py "cute cat" --download --output ./pics

# 限制结果数量
python bing_image_search.py "山水画" -n 5 --download
```

### 3. 脚本做了什么

1. 打开 Bing Images 搜索页面（有头浏览器，用户能看到窗口）
2. 等待页面加载，滚动触发懒加载
3. 从页面 JSON 数据（`.iusc` 元素的 `m` 属性）提取**原始大图 URL**
4. 显示结果，可选下载到本地
5. 浏览器窗口保持打开，用户关闭后退出

### 图片 URL 从哪来？

Bing 搜索结果中，每个图片项有一个 `<div class="iusc" m="{"murl":"原始大图URL", "turl":"缩略图URL", "t":"标题"}">`。

`.iusc` = **I**mage **U**RL **S**tructured **C**ontainer，是 Bing 存储原始图片 URL 的标准方式。

脚本通过 `JSON.parse(el.getAttribute('m'))` 拿到完整图片链接，而不是使用缩略图。

## 示例输出

```
[INFO] 页面标题: 富春山居图 黄公望 - 搜索 图片
[INFO] 找到 15 张图片
[IMG 1] 黄公望富春山居图_360百科
       https://p1.ssl.qhmsg.com/t01c3b52137dbda32bd.jpg
[IMG 2] 中国十大传世名画之《富春山居图》合璧版
       http://n.sinaimg.cn/sinacn12/96/w2048h2048/20180412/7afa-fyzeyqa9634352.jpg
[DONE] 关闭浏览器窗口结束程序
```

## 注意事项

- 脚本默认以 `headless=False` 运行（即弹出浏览器窗口）——这是有意为之，**不要改为 `headless=True`**，否则会被 Bing 检测并拦截
- 需要用户手动关闭浏览器窗口来结束程序
- 搜索中文关键词时 Bing 结果比 Google 更准确（Google 可能被墙）
- 图片版权归属原作者，仅供个人学习参考
