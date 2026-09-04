# FENGMEM — Search-King 项目记忆

## 2026-08-28 — 第 1 轮
- 用户要求:
  1. 确认 Search-King 是否最新版
  2. 研究文字搜索为何现在"一个引擎都读不到" — 是不是 VPN IP 问题
  3. 评估上次的 perf 改动是否引入 bug
  4. Cloak 后端会不会更好
  5. 先修 Search-King, 再用 Tiny Fish 给它"添光"
  6. 默认链按查询语言自适应; 先深挖 IP 封锁证据再修
- AI 行动:
  - 有头搜索 "tiny fish" (Edge) → 找到 GitHub 上的 tinyfish-io/tinyfish-mcp-server (MCP server, 让 AI 连网做网页自动化)
  - 实测各文字引擎(openai): baidu/sogou ✅5条, brave/bing/ddg ❌0条
  - curl 裸请求 Brave 直出验证码页 → 坐实 VPN 出口 IP 被国外引擎封锁(非工具bug/非指纹)
  - 读 perf 提交(543111d)差异 → 发现并发提前收网只 cancel() 不 await, 留 Future exception never retrieved / ERR_ABORTED bug
  - 读 cloak_text_search(1268行) → 独立实现固定 Bing+Brave, 实测 0/0, 不比 edge 好
  - git: 本地落后远端2提交(5fc6803 opencli兼容, a8d1e72 加官网), 领先2(perf改动); 远端2提交与文字搜索无关
- 产出: 本轮仅诊断, 未改代码
- 关键决策:
  - Search-King 本体没坏, 卡点是 VPN IP 被国外引擎标记; 国内引擎正常
  - 上次 perf 改动确有取消协程 bug 需修
  - Cloak 后端无效(同样走被封国外引擎)
  - 阶段一: 修取消bug + 默认链按查询语言自适应 + IP封锁友好提示
  - 阶段二: 接 tinyfish-io/tinyfish-mcp-server (需先解决IP封锁, 否则TinyFish也走同一被封出口)
- 待深挖: IP封锁到底覆盖哪些国外引擎(curl 逐测 url/curl), 决定阶段一修复细节

## 2026-08-28 — 第 2 轮 (IP封锁深挖)
- 用户要求: 先深挖 VPN IP 封锁证据, 再决定修复; 默认链按查询语言自适应
- AI 行动: curl 裸请求逐测 6 引擎直连状态
- 产出: 封锁地图(未改代码)
- 关键决策/封锁证据:
  - ✅ 可用(直连无封锁关键词): 百度200 搜狗200 DuckDuckGo(/html)200
  - ⚠️ 被拦(需验证): Bing 200+challenge, Google 200+challenge(302跳转)
  - 🚫 限流429: Brave captcha
  - 关键: DDG 经典 /html 端点直连返 12 个 result__a 真实链接, 但 Search King 现用新版 ?q&ia=web 端点+article[data-testid] 选择器 → 无头下抽0 (端点/选择器不匹配, 非IP封)
  - 结论: 封锁非"国外引擎一刀切"; Brave/Bing/Google 标记了本IP, DDG/百度/搜狗可用
- 阶段一修复方向(已定):
  1. 修并发取消bug: asyncio.wait 收网时 cancel() 后需 await 收敛, 加 cancel guard 消除 ERR_ABORTED/Future exception never retrieved
  2. 默认链按语言自适应: 中文→[baidu,sogou,ddg_html]; 英文→[ddg_html,baidu,sogou] (弃用被封的 brave/bing/google 作默认主力)
  3. ddg-web 改用 /html 经典端点 + result__a/.result__snippet 选择器(匹配实测可用的直连)
  4. IP封锁友好提示: 引擎全挂时若 curl 直连也验证码/429 → 提示"VPN出口IP被标记, 建议换节点"

## 2026-08-29 — 第 3 轮 (TinyFish 调研 + 反爬方案)
- 用户要求: 反爬怎么做? tinyfish怎么连?
- AI 行动: WebFetch 读 tinyfish-io/tinyfish-mcp-server README
- 产出: 见本轮回复; todo.md 已建
- 关键决策/纠正: TinyFish 是云端执行(automation 跑在 agent.tinyfish.ai), 本地包仅回环代理 127.0.0.1:3711 → 不走本机 VPN 出口, 上轮"TinyFish也走同一被封出口"判断有误, 反而可作被封IP的绕行通道

## 2026-08-29 — 第 4 轮 (全量反爬测试+调研)
- 用户要求: 测试所有搜索/所有方式 + 搜反爬资料 + 完整报告
- AI 行动: 并行派 2 个后台 general-purpose 子 Agent (全后端实测 / 反爬联网调研)
- 产出: 待两 Agent 回来后汇总报告

## 2026-08-29 — 第 5 轮 (完整报告产出)
- 用户要求: 测试所有搜索+反爬调研+完整报告 (承接第4轮)
- AI 行动: 2个后台子Agent完成实测与调研 (调研Agent首次因并发限额失败, 实测完成后重派成功)
- 产出: REPORT-反爬测试与调研-2026-08-29.md (全引擎实测矩阵 + 封锁机制调研 + 落地建议)
- 关键发现: lite(纯HTTP)最快最稳6s; cloak唯一20条; 百度国内出口也全CAPTCHA(指向headless指纹而非IP); 根因是TLS/CDP指纹; 建议Patchright替换Playwright(零成本drop-in) + Serper API(~$0.3/千次)补Google; Bing官方API已退役(2025-08-11)

## 2026-08-29 — 第 6 轮 (重构计划启动)
- 用户要求: 全面重构提高获取能力 — 出计划
- AI 行动: 后台派 Explore 子代理摸清 scraper.py 架构(函数清单/引擎实现/并发模型/已知bug位置)
- 产出: 待架构摘要回来后出重构计划

## 2026-08-29 — 第 7 轮 (重构计划定稿)
- 用户要求: 全面重构提高获取能力 计划
- AI 行动: Explore 子代理摸清架构(2221行,run()巨函数,选择器内联JS,4条read路径,--limit双语义bug根因:1500行) → 定稿计划
- 产出: REFACTOR-PLAN.md (阶段0止血/1正骨拆包/2强肌Patchright+调度/3造血API通路, M1-M4派单批次)
- 关键决策: CLI参数面100%兼容; 健康度注册表取代写死默认链; cloak 5s超时根因是--limit误传timeout非写死

## 2026-08-29 — 第 8 轮 (M1 开工)
- 用户要求: tinyfish没干进去 还有其他后端 → 确认阶段3含tinyfish/serper/brave/searxng; 开工
- AI 行动: 后台派 M1 子Agent 执行阶段0五项止血修复(位置精确到行)
- 产出: 待M1完成验收; key依赖提醒用户注册 TINYFISH/SERPER/BRAVE API_KEY

## 2026-08-29 — 第 9 轮 (砍key, 全开源免费)
- 用户要求: 不要搞key, 要求开源免费
- AI 行动: 改 REFACTOR-PLAN.md 阶段3 + todo.md — 砍除 Serper/Brave API/TinyFish(全需key), 换成 SearXNG自托管 + Mojeek/Startpage/Wikipedia 免费直连 + 修opencli shell拼接
- 关键决策: 项目零key零账号依赖; M1(阶段0修复)不受影响继续后台跑

## 2026-08-29 — 第 10 轮 (TinyFish 免费确认, 恢复)
- 用户要求: tinyfish也是免费, 测试能不能用, 能免费就用
- AI 行动: curl 实测 agent.tinyfish.ai/mcp — 401但返回标准OAuth资源元数据(clerk.tinyfish.ai, PKCE); WebSearch 查实 Search(30次/分)+Fetch(150URL/分)官方免费无需信用卡, Agent/Browser按步计费
- 关键决策: TinyFish恢复进阶段3, 用OAuth授权流(非静态key)+只用免费search/fetch工具; Serper/Brave API维持砍除

## 2026-08-29 — 第 11 轮 (TinyFish 实测通过)
- 用户要求: 登录tinyfish实测搜索"AI怎么去接搜索引擎"; 提供 API key (sk-tinyfish-...)
- AI 行动: npm镜像装 @tiny-fish/cli + tinyfish auth set; 查docs得 Search API: GET https://api.search.tinyfish.ai?query=... , X-API-Key 头, 免费不耗钱包
- 产出: 实测✅ 10条高质量中文结果(IBM/Brave/Google Cloud/知乎/GitHub/博查/阿里云), 含 date/recency/domain_type(news/research_paper)/purpose 参数
- 关键决策: TinyFish Search API 确认可用且免费, 正式列进阶段3接入计划(--backend tinyfish / -e tinyfish 通路, key存env不走OAuth也行)

## 2026-08-29 — 第 12 轮 (浏览器默认可用专项研究)
- 用户要求: 主攻浏览器后端怎么默认能work (已有edge/chromium/lite/cloak/manual/opencli多backend)
- AI 行动: 后台派子Agent — 读代码对比edge与cloak启动/指纹差异 + 实测各后端CAPTCHA率 + 调研CloakBrowser/Patchright/headful
- 产出: 已完成 — tinyfish key 兜底读 ~/.tinyfish/config.json；multi_source_search() 4源并发(baidu+ddg+tinyfish+searxng)+噪声过滤(image.baidu.com等)；--deep 第①跳同步；SearXNG Docker 容器起在 127.0.0.1:8899(8888被ts-nav占)，镜像 docker.1ms.run 加速，bing/qwant 可用 google/ddg/baidu 被墙或验证码
- 关键决策: Mojeek 返回 Captcha 页、Startpage 被 Anubis 拦截 → 均不接入；baidu_lite 当前被百度安全验证拦(既有问题)→默认实际为 ddg+tinyfish+searxng 三源

## 2026-08-29 — 第 13 轮 (浏览器默认可用研究报告)
- AI 行动: 子Agent完成实验+调研
- 关键发现/修正: 默认链主力已是brave-web, edge无头本轮中英文都能出结果,"默认全线被拦"结论过时; 真窟窿=baidu/sogou高CAPTCHA + 英文落sogou拿跳转链接 + cloak的Bing脚本在0.4.10有bug(context destroyed); cloakbrowser本机0.4.10落后官网0.5.9; patchright本机已装1.61.2(Crawl4AI带进来的)且支持msedge channel
- 推荐方案: ①默认链改[brave,ddg,sogou,baidu] ②playwright→patchright drop-in+删浅指纹init_script(一行import) ③cloakbrowser升级0.5.9+修Bing脚本+edge全挂自动转cloak兜底; 不建议headful默认/cloak当默认

## 2026-08-29 — 第 14 轮 (M1.5 默认降级链开工)
- 用户要求: brave是配角(结果不准); 搞清默认现状/手动配置项/降级机制 — 核心痛点"AI拿它搜不出来"
- 诊断确认: 默认=edge+[brave,sogou,baidu]; 跨后端降级不存在, 非交互全挂=0条返回; lite/cloak要手动指定; tinyfish未接入
- AI 行动: 派 M1.5 后台子Agent — 实现默认全自动降级: ①lite直连(baidu_lite新增+ddg_lite并发先到先得) ②浏览器链[ddg,sogou,brave,baidu] ③cloak兜底(修Bing容错) ④tinyfish(env key) ⑤手动模式仅tty; 结果<所需数量才降级并合并去重; 总deadline 120s
- 关键决策: 用户显式 -e/--backend 时不隐形降级

## 2026-08-29 — 第 15 轮 (Agent-Reach 调研)
- 用户要求: agent reach 资料还在我们项目里吗? 它好像还能搜出来
- 诊断: 不在——项目计划/todo/记忆均无此名; 它是独立开源项目 Panniantong/agent-reach (MIT), 与TinyFish无关
- 关键发现: 它是"路由+体检层"(channels清单+按序探测+doctor诊断), 证实我们降级链/健康度注册表思路; 内含两条零key免费通路值得吸收: Exa搜索(MCP免费) + Jina Reader(r.jina.ai免费Markdown)
- 决策: Exa + Jina Reader 加入阶段3免费通路清单

## 2026-08-29 — 子代理执行
- 用户要求: 实现 --search 全自动降级链
- AI 行动: 改 scraper.py（TEXT_FALLBACK_CHAIN、新增 baidu_lite_search/tinyfish_search/_norm_url_key/full_auto_text_search、cloak Bing goto 修、dispatch 接入、run 返回结果）
- 产出: 验收 1-6 全过，日志 accept_log.txt
- 关键决策: baidu_lite 加随机 BAIDUID cookie 绕安全验证；hop5 手动复用 run() 内置 tty 兜底

## 2026-08-29 — 第 16 轮 (M1.5 完成, 默认即工作达成)
- AI 行动: M1.5 子Agent完成5跳全自动降级链, 验收7项全过(未commit)
- 验收: 裸调--search 中文6条10.1s/英文5条7.8s/冷门6条4.5s 全在第①跳Lite直连出结果; 实战检验: 重跑时DDG SSL断连→浏览器链→Brave兜住6条, 降级按设计工作
- 改动: baidu_lite_search(随机BAIDUID cookie)/tinyfish_search/_norm_url_key去重/full_auto_text_search(120s deadline); 默认链[ddg,sogou,brave,baidu]; cloak goto wait_until=load修Bing
- 遗留: 百度lite拿的是/link?url=跳转链(可加302解析真链); 显式-e/--backend不降级

## 2026-08-29 — 第 17 轮 (M1.6 默认简化)
- 用户反馈: ①结果可信度差,要接正经搜索引擎 ②为什么只有一个引擎(先到先得把另一个取消了) ③不要这样改——默认简单,增强复杂,保持正交,由语音指示让AI选
- AI 行动: 派 M1.6 子Agent — 默认=baidu+ddg双源都等齐合并去重; 五跳流水线改为 --deep 显式增强开关; 正交保持(-e/--backend不变)
- 引擎可用状态: ✅baidu_lite(随机BAIDUID)/ddg /html/sogou/brave(配角)/tinyfish(key); ❌bing/google直连

## 2026-08-29 — 第 18 轮 (M1.6 完成)
- AI 行动: M1.6 子Agent完成, 验收5项全过(未commit)
- 落地: 默认=simple_dual_source_search(baidu+ddg都等齐合并去重, 中/英文区分); 增强五跳流水线改为 --deep 显式开关; baidu_lite被百度安全验证拦过一次→改完整cookie组+Referer恢复
- 遗留: baidu_lite混入image.baidu.com噪声条目待过滤; --deep不与显式-e/backend组合(按设计)

## 2026-08-29 — 第 19 轮 (多正经源扩充)
- 用户反馈: 不满意 baidu+ddg 质量, 要更多正经搜索引擎
- AI 行动: 派子Agent — ①tinyfish进默认合并(key从env/CLI配置取,不硬编码) ②实测Mojeek直连可否解析 ③本机部署SearXNG(能间接拿Google/Bing) ④Startpage试测 ⑤默认升级多源并发合并+过滤image.baidu.com噪声
- 产出: 已完成 — tinyfish key 兜底读 ~/.tinyfish/config.json；multi_source_search() 4源并发(baidu+ddg+tinyfish+searxng)+噪声过滤(image.baidu.com等)；--deep 第①跳同步；SearXNG Docker 容器起在 127.0.0.1:8899(8888被ts-nav占)，镜像 docker.1ms.run 加速，bing/qwant 可用 google/ddg/baidu 被墙或验证码
- 关键决策: Mojeek 返回 Captcha 页、Startpage 被 Anubis 拦截 → 均不接入；baidu_lite 当前被百度安全验证拦(既有问题)→默认实际为 ddg+tinyfish+searxng 三源

## 2026-08-29 — 第 20 轮 (去Docker化)
- 用户要求: 不要Docker
- AI 行动: 派子Agent — 首选SearXNG原生pip跑(零Docker), 跑不通则砍searxng源+实测Qwant直连/cn.bing/Wikipedia等零Docker引擎顶上; Docker容器rm -f
- 产出: 待报告

## 2026-08-29 18:35 — 去 Docker 化（子 Agent 执行）
- 用户要求: 默认搜索去掉 Docker 依赖（SearXNG 原生跑）
- AI 行动: PyPI searxng 是假包→从 ghfast clone 官方源码到 C:\FengProj\searxng-src，pip --no-build-isolation -e 装上（需先装 msgspec）；修 searx/valkeydb.py 的 Unix-only import pwd；先 docker rm -f searxng（注意 docker context 是 desktop-linux，DOCKER_HOST 被 podman 管道占用）再腾出 8899；SEARXNG_SETTINGS_PATH=settings-win.yml + python -m searx.webapp 启动成功，bing/google cse/qwant 出结果
- 产出: start_searxng.bat（日常启动入口）；scraper.py :1206 注释去 Docker 化；todo.md/FENGMEM.md 已记录
- 关键决策: 走路线1（原生 Python）成功，未砍源未加替代引擎；未 commit

## 2026-09-04 18:35 — 第 21 轮 (SearXNG in-process 集成)
- 用户要求: SearXNG 不用 Docker，要能作为默认搜索源之一
- AI 行动: SearXNG Flask HTTP server 在 Windows 上返回 500（middleware 链问题，test_client 正常但 real server 不行）；改用 in-process Flask test_client 方式——`searxng_search()` 直接调用 `app.test_client().get()` 无需启动 HTTP 服务；重写 `searxng_search()` 加 lazy-init + `sys.path.insert` searxng-src；配置 `C:\FengProj\searxng-src\searxng-settings\settings.yml`（`use_default_settings: true` + formats json + port 8899）；将 `("searxng", searxng_search)` 加回 `MULTI_SOURCE_ENGINES`
- 产出: 默认搜索 4 源合并（baidu+ddg+tinyfish+searxng），实测 16 条去重结果；Google CSE 引入权威来源；`--backend lite` 降级链正常
- 关键决策: 不用 HTTP server 而用 test_client 绕过 Windows middleware 500；searxng 作为第 4 源静默缺席机制不变
- 未 commit
