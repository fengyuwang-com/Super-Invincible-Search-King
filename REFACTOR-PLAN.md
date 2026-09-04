# Search King 全面重构计划（提高获取能力）

日期：2026-08-29 ｜ 依据：全引擎实测报告 + 反爬调研 + 架构摸底（2221 行，无类，run() 巨函数）

## 现状诊断（一句话版）

获取能力弱不是因为缺引擎，而是**四层都欠账**：架构上 run() 巨函数 + 选择器内联 JS 无 schema；通路上每引擎只有一条路，死了就死；指纹上裸 Playwright 被 TLS/CDP 识别（百度全 CAPTCHA 的根因）；调度上无节流/退避/会话复用。重构按"先止血、再正骨、后强肌、再造血"四阶段推进，每阶段独立可交付、CLI 参数面保持兼容。

## 阶段 0：止血（bug 修复，~1 天，先行派单）

全部有精确代码位置，低风险：

- [ ] 并发收网 cancel 后未 await：`scraper.py:829-830` + `wait_for_user_input:427-428`，cancel 后补 `await asyncio.gather(*tasks, return_exceptions=True)` 收敛
- [ ] cloak --read 5s 超时：根因是 `:1500` 把 `--limit`（结果数）误传为 timeout 参数——改为独立 `--timeout`，`--limit` 回归单语义
- [ ] ddg-web 端点：`TEXT_ENGINES:306-324` 改用 `html.duckduckgo.com/html/` + `result__a`/`result__snippet`（与实测可用的 lite 端点对齐）
- [ ] 非交互环境跳过手动兜底：stdin 非 tty 直接跳过并提示，不白等
- [ ] 图片尺寸 `[?x?]`：引擎 extract JS 补返 w/h，或引擎图走通用 `extract_images` 路径补尺寸
- 验收：原 todo 阶段一 ①③ 项全消；中/英文各查一次全链无 ERR_ABORTED

## 阶段 1：正骨（结构重构，~2-3 天）

目录化拆包，CLI 参数面 100% 兼容（SKILL.md / AGENTS.md 调用方式不变）：

```
search_king/
  engines/       # 引擎定义：配置与选择器搬出内联 JS → dataclass + 声明式 schema
    text.py     # TEXT_ENGINES（ddg/baidu/sogou/bing/google/brave）
    image.py    # ENGINES 12 图引擎 + FALLBACK_CHAIN
  routes/        # 通路层（重构核心）
    http_route.py    # lite：urllib/httpx 直连（现 ddg_lite_search 泛化）
    browser_route.py # playwright/patchright：统一浏览器生命周期
    cloak_route.py   # CloakBrowser（现 cloak_* 迁入，去重）
    api_route.py     # 阶段3：serper/brave/searxng/tinyfish
  session.py     # 节流/退避/Cookie 池/UA 池（现在 4 处重复 UA 全收编）
  read.py        # 四条 --read 路径统一适配器，输出统一 dict 契约
  cli.py         # argparse + 分发（现 :1375-1560 if-elif 链）
  scraper.py     # 兼容入口薄壳，import 转发
```

关键动作：
- **拆 run()（:679-974）**：浏览器生命周期归 `session.py` 独占（谁拥有浏览器从此明确）；三种模式拆成独立入口函数
- **健康度注册表**：每引擎×每通路记录最近成功率/延迟，持久化到 `~/.search_king/health.json`；选引擎时自动降级到健康通路（淘汰手写死默认链的维护负担）
- 验收：`python -m search_king` 与旧 `python scraper.py` 行为一致；`ddg_lite_search/cloak_read_pages` 等库函数签名不变

## 阶段 2：强肌（指纹与调度，~2 天，获取能力的核心提升）

- [ ] **Patchright 替换 Playwright**（调研确认 drop-in，改动最小）：`browser_route.py` 单点替换 + 保留 `--backend` 原语义；实测验证百度 CAPTCHA 是否缓解
- [ ] 节流：同域请求随机 2-5s 间隔、全局并发上限（lite 3 / browser 4）
- [ ] 退避：CAPTCHA/429 后该引擎指数退避（1→2→4→8min）并写入健康度注册表，本轮内不再撞
- [ ] 会话复用：Cookie/localStorage 持久化 per 引擎（`~/.search_king/sessions/`），复用通过态
- [ ] 默认链语言自适应：中文 `[baidu, sogou, ddg]` / 英文 `[ddg, brave_api, sogou]`，但以健康度注册表动态排序为准
- 验收：连续 20 轮混合查询，引擎全挂率 <10%，无 IP 封锁导致的整轮失败

## 阶段 3：造血（新通路，全部开源免费、零 key，各 ~0.5-1 天，可并行派单）

**原则（用户定）：不搞 API key / 付费额度 / 账号注册，全部开源免费。** ~~Serper/Brave API 砍除~~；TinyFish 实测确认免费可用，保留（见下）。

- [ ] **SearXNG 自托管聚合源**：本机起 SearXNG（Docker 或 `pip install searxng`），`public_instance:false` + limiter 关闭 + 启用 Mojeek/Startpage/Wikipedia 等小引擎（Google 引擎指望不上，调研 issue#2515）；Search King 侧 `api_route.py` 调本地 `http://127.0.0.1:8888/search?format=json`，JSON 直接解析，`-e searxng` 手动指定，健康时自动补位
- [ ] **免费小引擎直连扩充**：TEXT_ENGINES 增加 Mojeek（`mojeek.com/search?q=`，无 JS 纯 HTML，对自动化最宽容）、Startpage lite、Wikipedia API（`action=opensearch`，官方开放无 key）——都是纯 HTTP 免费通路，进 lite 链
- [ ] **TinyFish 免费通路**（2026-08-29 实测确认）：Search（30 次/分）和 Fetch（150 URL/分）官方免费、无需信用卡，付费的 Web Agent/Browser 不用。认证走 OAuth PKCE（授权服务器 clerk.tinyfish.ai，端点 `https://agent.tinyfish.ai/mcp` 返回标准 OAuth 资源元数据）——首次连接弹浏览器授权一次，token 持久化到 `~/.search_king/`，之后无感刷新；不存任何静态 key。实现：MCP Streamable-HTTP 客户端连 `agent.tinyfish.ai/mcp`，tools/list 里选免费的 search/fetch 工具（跳过付费的 run_web_automation），包成 `-e tinyfish` 通路。云端出口不走本机 VPN，是 IP 被封时的救生艇
- [ ] **Exa 免费搜索 + Jina Reader 免费读页**（调研自 agent-reach 项目，均零 key）：Exa 走 MCP 免费接入补搜索源；Jina Reader（`https://r.jina.ai/<url>` 免费无 key 返回干净 Markdown）作为 `--read` 的免费兜底通路
- [ ] **顺手修**：scraper_fetch 的 shell 拼接 opencli 命令（`:37-38` JS 含引号即断）改参数数组传参
- 验收：英文查询在 DDG 被临时限流时，SearXNG/Mojeek 通路仍能出结果；全程无任何 key/账号依赖

## 里程碑与派单

| 批次 | 内容 | 派单方式 |
|---|---|---|
| M1 | 阶段 0 全部 bug 修复 | 1 个后台子 Agent |
| M2 | 阶段 1 拆包重构 | 1 个后台子 Agent（M1 验收后） |
| M3 | 阶段 2 Patchright+调度 | 1 个后台子 Agent（M2 后） |
| M4 | 阶段 3 各新通路 | 可并行多个子 Agent |

每批完成跑同一套验收脚本（中/英文查询 × 全通路 × 记录成功率/耗时），与 2026-08-29 基线对比。

## 风险与约束

- `--limit` 双语义修复可能影响依赖旧行为的脚本（AGENTS.md/SKILL.md 只用 `--search/--read/位置参数`，已核对安全）
- 四条 --read 路径的输出 dict 结构（url/title/content/blocked/error）是隐性契约，read.py 重构时先写契约测试再动
- Patchright 需验证 Windows 下 edge channel 可用性；不可用则退回原 Playwright + cloak 承担重活
- 全程不提交不推送，每阶段完成后由用户验收
