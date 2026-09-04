# Search King todo

## 队列

### 阶段一：修 Search King 本体（已定方案，待实施）
- [x] ① 修并发取消 bug：asyncio.wait 收网处 cancel() 后补 await 收敛 + try/except guard，消 ERR_ABORTED / Future exception never retrieved（2026-08-29 阶段0完成）
- [x] ② 默认链自适应 → 由 M1.5 全自动降级流水线替代落地（见"已完成"）（2026-08-29）
- [x] ③ ddg-web 后端改用 DDG 经典 /html 端点 + result__a / .result__snippet 选择器，并解码 uddg 跳转链接（2026-08-29 阶段0完成）
- [ ] ④ IP 封锁友好提示：引擎全挂时后台 curl 直连自检，验证码/429 → 提示换 VPN 节点；选择器失效 → 提示页面结构变了
- [ ] ⑤ 同步远端落后 2 个提交（opencli 兼容）后提交阶段一

### 新增（来自 2026-08-29 实测报告，见 REPORT-反爬测试与调研-2026-08-29.md）
- [x] 默认后端切 lite 直连链 → M1.5 落地：默认第一跳即 Lite 直连（2026-08-29）
- [x] 修 cloak --read 硬编码 5s goto 超时：新增 --timeout 参数（默认30s），--limit 回归纯结果数语义；read_multiple_pages 同类误传一并修（2026-08-29 阶段0）
- [x] 修 ddg-web 中文假结果（DDG 自家广告混入）——由 ③ 端点替换一并解决（2026-08-29 阶段0）
- [x] 修图片搜索尺寸 [?x?]：try_engine 补通用尺寸探测（优先读已加载 img，兜底 new Image）（2026-08-29 阶段0）
- [x] 非交互环境跳过手动模式兜底：wait_for_user_input stdin 非 tty / EOF 立即返回 False 并提示（2026-08-29 阶段0）
- [ ] 评估 Patchright 替换 Playwright（drop-in，解决 CDP/TLS 指纹，救百度软拦）
- [ ] ~~Serper/Brave API~~（需 key，砍除）；~~TinyFish~~ → **实测免费，恢复**：Search/Fetch 官方免费档（30次/分搜索、150URL/分抓取），OAuth PKCE 授权免静态 key，只用免费工具跳过付费 run_web_automation
- [x] SearXNG 自托管聚合源（in-process test_client 集成，无需 HTTP 服务；Google CSE 正常出结果）（2026-09-04）
- [ ] TEXT_ENGINES 扩充免费小引擎直连：Mojeek / Startpage lite / Wikipedia opensearch API（纯 HTTP 零 key）
- [ ] 修 scraper_fetch shell 拼接 opencli 命令（JS 含引号即断）改参数数组

- [x] TinyFish 接入：tinyfish_search() 已落地（REST API + TINYFISH_API_KEY env，key 已实测✅），作为降级链第④跳；MCP/OAuth 方案不再需要（2026-08-29）
- [x] TinyFish 进默认合并：key 兜底从 ~/.tinyfish/config.json 读（_tinyfish_api_key()，不硬编码），默认多源之一（2026-08-29）
- [x] ~~SearXNG 自托管聚合源：Docker 容器起在 127.0.0.1:8899~~ → 已改为 in-process test_client（无需 HTTP 服务，2026-09-04）
- [x] Mojeek 直连实测：curl 200 但返回 Captcha 页（换 UA/cookie 均拦），不接入（2026-08-29）
- [x] Startpage 直连实测：被 Anubis proof-of-work challenge 拦，不接入不硬刚（2026-08-29）
- [x] 默认 --search 升级 4 源并发合并：multi_source_search()（baidu+ddg+tinyfish+searxng 都等齐 35s 上限、_norm_url_key 去重、噪声域过滤），输出头 `🔍 4源合并: 共X条（...）`；simple_dual_source_search 改为其展示壳；--deep 第①跳同步用多源函数；中英文同一套源（2026-08-29）
- [x] baidu_lite 噪声过滤：_NOISE_URL_PAT/_is_noise_url() 过滤 image.baidu.com/baijiahao/m.baidu.com/b2b.baidu.com（2026-08-29）

## 已完成
- [x] IP 封锁地图：✅百度/搜狗/DDG(/html)；⚠️Bing/Google(challenge)；🚫Brave(429 captcha)（2026-08-28）
- [x] 定位 ddg-web 抽 0 原因：端点+选择器错配，非 IP 封（2026-08-28）
- [x] 定位并发取消 bug 为上次 perf 改动引入（cancel 后未 await）（2026-08-28）

- [x] --search 全自动降级链落地（2026-08-29）：lite 并发直连(baidu_lite+ddg_lite，中文双引擎/英文 ddg)→浏览器链["ddg-web","sogou-web","brave-web","baidu-web"]→cloak 兜底(Bing goto wait_until=load 修 context destroyed)→tinyfish_search(TINYFISH_API_KEY)→手动(仅tty)；总 deadline 120s；显式 -e/--backend lite/cloak 不降级；run() search 分支返回 deduped 供合并。验收 7 项全过（中文/英文/冷门/lite/显式-e/连跑稳定性），baidu_lite 需随机 BAIDUID cookie 否则安全验证页。

### 新增（2026-08-29 用户反馈调整 M1.5 搜索流水线）
- [x] 默认 --search 改简单双源合并：simple_dual_source_search()（中文 baidu_lite+ddg_lite 并发等齐合并去重；英文 ddg 单源），单引擎失败不影响另一个；输出头 `🔍 百度+DDG 双源合并: N 条（baidu X 条、ddg Y 条）`（2026-08-29）
- [x] 增强模式显式开关 --deep：argparse 新增 --deep，仅 --deep 走原 full_auto_text_search 五跳流水线（代码原样保留）；dispatch 改为 --deep 分支（2026-08-29）
- [x] 修 baidu_lite 百度安全验证拦截：随机单 BAIDUID 已失效，补全 cookie 组（BIDUPSID/PSTM/BD_CK_SAM/PSINO/delPer/HMACS）+ Referer: https://www.baidu.com/ 后恢复（2026-08-29）
- [x] 验收 5 项全过：中文双源(baidu 5+ddg 5→合并7)、英文(ddg 5)、--deep 五跳、-e sogou-web 不变、--backend lite 不变（2026-08-29）
- [ ] baidu_lite 当前被"百度安全验证"整页拦截（2026-08-29 下午复测：补 cookie 组也 0 条），多源合并下静默缺席不影响其他源；后续可试 Patchright 救百度

### 去除 Docker 依赖（2026-08-29 用户要求）
- [x] SearXNG 原生 Python 运行替代 Docker：从 ghfast.top 镜像 clone searxng 源码到 C:\FengProj\searxng-src，`pip install --no-build-isolation -e .`（清华 TUNA）；修 searx/valkeydb.py 的 Unix-only `import pwd`（Windows 兼容补丁）；PyPI 上的 "searxng" 包是假货(MCP wrapper)勿装。启动：start_searxng.bat（SEARXNG_SETTINGS_PATH=searxng/settings-win.yml，127.0.0.1:8899）。Docker 容器 searxng 已 `docker rm -f`。验收：中文/英文多源合并 4源（searxng 5条，bing+google cse+qwant）、-e sogou-web 不变、无 searxng 容器（2026-08-29）
- [x] SearXNG 改为 in-process 集成（2026-09-04）：Flask HTTP server 在 Windows 返回 500（middleware 链问题），改用 `app.test_client().get()` 直接调用，无需启动 HTTP 服务；配置 `searxng-settings/settings.yml`（`use_default_settings: true` + formats json）；searxng_search() lazy-init + sys.path.insert；实测 Google CSE 出结果，4源合并 16 条去重
- [x] 清理硬编码路径：scraper.py 用 `os.path` 相对推导 searxng-src（优先 SEARXNG_SRC 环境变量 → 兄弟目录 → ~/searxng-src）；start_searxng.bat 用 `%~dp0`；searxng settings 去掉硬编码 secret_key（2026-09-04）
- [x] 清理项目文件夹：删除 bilibili/series/opencli 临时文件；.gitignore 补全 temp/debug 模式（2026-09-04）
- [x] 更新文档为 AI 可读：README.md / SKILL.md 重写反映 4 源合并架构；requirements.txt 加 searxng+waitress（2026-09-04）
