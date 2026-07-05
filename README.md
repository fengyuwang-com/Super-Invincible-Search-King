# Bing Image Finder

绕过反爬的图片搜索工具——用 Playwright 有头浏览器搜 Bing Images，找到正确的图片并下载到本地。

## 解决的问题

普通方式搜图（curl / requests）经常：
- ❌ 搜到的图不对题
- ❌ 返回空白/占位图
- ❌ 根本搜不到

因为 Google/Bing/百度的图片都靠 **JavaScript 动态加载**，简单 HTTP 请求只拿到空壳页面。

## 原理

用 **Playwright 在非无头模式**（`headless=False`）下启动真实 Chrome 浏览器：
- 浏览器指纹与真实用户无异（WebGL、navigator.webdriver、分辨率等）
- JavaScript 完整渲染页面
- 从 Bing 页面内部 JSON 数据（`murl`）提取原始大图 URL
- 不会被搜索引擎拦截

## 安装

```bash
pip install playwright
playwright install chromium
```

## 使用

```bash
# 搜索关键词，弹出浏览器窗口
python bing_image_search.py "富春山居图"

# 搜索并下载图片
python bing_image_search.py "山水画" --download --output ./pics

# 控制结果数量
python bing_image_search.py "cute cat" -n 5 --download
```

## 项目结构

```
image-finder/
├── bing_image_search.py    # 主脚本
├── SKILL.md                # Claude Code skill
├── README.md               # 本文件
└── requirements.txt        # 依赖
```

## License

MIT
