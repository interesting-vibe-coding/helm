# Kaji — project progress (单一进展文档)

> 原 hub `docs/projects/kaji.md` 迁移至此（hub 新规则: 项目进展住项目自己的 repo）。
> 每个 milestone 更新本文件; caveman 风格。


**Identity**: Kaji (舵 = rudder; you steer, agents execute). Lineage: Kaku → Pack →
Desk → Helm → **Kaji**. Repo `interesting-vibe-coding/kaji` (public), installed
`/Applications/Kaji.app` (`dev.kaji.app`, wabi-sabi `>_` logo on deep ink).
Build: `PROFILE=release ./scripts/build.sh --app-only`.

**Vision**: workbench built for AI agents — unified multi-harness intake (Claude
Code/Kiro/opencode/Codex), auto window-switch + auto-layout on task completion,
cross-agent shared memory+skills out of the box, mobile remote control. "You sit at
Kaji, agents hand you finished work, you only decide."

**Strategic redirect (key)**: killer feature = 手机管全 harness（状态+额度+操舵）. 倒推出
**主干 = helm-brain 服务化 + relay + auth，引擎是叶子**. 手机远程已红海（Anthropic Remote
Control / Omnara / Nimbalyst / Forge）但都锁单厂商 → Kaji wedge = **harness-agnostic 统一
fleet + 共享 memory/skills**.

**Agent loop E2E (2026-06-09)**: 启动进 Brain → spawn(平铺 Work、不跳转) → worker waiting 时 Brain 实时单条通知(cooldown 去重) → 重进 y/n 恢复. 闭环验证通.

**定位决议 (2026-06-10)**: trending 主角 = **brain（fleet mission control，手机管全 harness）**，终端是 vessel。叙事第一屏 = 手机同时操舵多 harness 的 demo，Kaji.app = "最佳体验" 第二屏。工程纪律：brain 代码尽量不依赖 Kaji 持有 pane；pane 注入（quota scrape/spawn）隔离成 adapter 层，将来可加 tmux adapter 独立发布。风险：窗口期（厂商 remote control 开放即关窗）→ 快比完美重要；launch 前必须解决签名公证。

**Next（2026-06-11 二次刷新, 产品决议）**: 核心价值 = **用 Kaji 管多 harness 必须比终端里切换方便得多**; 三关键词 = 轻量 · 交互 · 可视化设计。demo 后放(体验好了再录)。队列: ① launchd 常驻(基础稳定) ② cockpit 交互循环 + mobile/desktop UI 设计打磨(主战场) ③ 统一额度 scraper(fleet 卡片数据燃料) ④ 自建薄 relay(连接终态, Happy 架构, QR+E2E) ⑤ demo。

**Funnel 实测结论（2026-06-11）**: 直连(不走代理)通; **走 Clash/梯子代理出口 → TLS 握手被掐, 连不上 ts.net Funnel 入口**。绕法 = 每设备加 `DOMAIN-SUFFIX,ts.net,DIRECT` 规则, 摩擦大 → 中间方案天花板已到, **自建 relay 必要性再+1**(relay 域名要选国内直连+代理出口都可达的)。

**旧 Next 存档**: ① ~~tool 改名 `helm-brain` → `kaji-brain`~~（✅ #121 已合, 2026-06-10）② relay+auth — **进行中**：Tailscale CLI userspace 模式跑通（无 root/系统扩展，`tailscaled --tun=userspace-networking`，socket `~/.local/share/tailscaled/sock`，Mac=`kaji-mac` 100.67.104.108），`kaji-brain serve` 绑 loopback + token（token 在 `~/.config/helm/brain-token`），401/200 验证通；待手机装 Tailscale app 打 `/healthz` 证全链 ③ mobile web cockpit（serve 出一个手机浏览器页：token 存 localStorage、看 state/发 send）④ 统一额度 scraper ⑤ cockpit 交互循环.

**Mobile 策略（决议 2026-06-10）**: 先用现成 app（Tailscale 官方客户端 + 手机浏览器打 serve 的 web 页），**自研手机 App = 远期规划**（web cockpit 验证完需求形状后再做原生）。TODO: tailscaled + serve 目前 nohup 裸跑，要 launchd 常驻。

**✅ 手机操舵 E2E 闭环（2026-06-10 晚）**: iPhone Safari `http://kaji-mac/` → mobile cockpit → Send → 文字注入 Kaji worker pane → claude 回话。全链: 手机 → tailnet(Apple ID 账号, `taild66623.ts.net`) → `tailscale serve :80` → `kaji-brain serve` 127.0.0.1:8787 → CLI → pane。**这就是 killer feature 的第一次完整跑通, demo 素材可录**。
最终配置: tailscaled userspace (`NO_PROXY=127.0.0.1` 防 Clash 截胡) + `tailscale serve --bg --http=80 8787`(手机免端口、Go 代理规范化 HTTP, 治好 iOS 下载怪癖) + token 在 `~/.config/helm/brain-token`。
**最终确认（当晚）**: Kaji.app 未启动时手机页显示 26h 幽灵会话 → send 无反应(根因即 #125); `open -a Kaji` + `/api/spawn` 拉起真 worker 后, 手机 hello → worker 收到并回话, 截图留档。`/api/spawn` 远程拉起 worker 也验证通。
**Next(2026-06-11 起)**: ① 修 #125(幽灵会话 = demo 杀手, 优先) ② launchd 常驻 tailscaled+serve(现 nohup 裸跑) ③ 录 demo(手机同时操舵多 harness) ④ 额度 scraper ⑤ cockpit 交互循环。

**发现 bug → kaji#125**: Kaji.app 没跑时 sessions 返回幽灵会话(26h 缓存)、send 连死 socket、mobile UI 不显示 send 失败。

**实测痛点（2026-06-10 手机 dogfood）**: ① iOS 单 VPN 槽，Tailscale 顶掉常驻代理 → 国内用户看 fleet 要切 VPN，体验差 → **自建 relay（纯 HTTPS 出站，不占 VPN 槽）从远期提升为正经 roadmap 项**，对国内场景是刚需不是锦上添花。② 手机/Mac 登不同账号（Apple ID vs Google）= 不同 tailnet 互相不可见，onboarding 文档要强调同账号。③ mobile cockpit 页已上线（serve `/` 路由，PR #124）：token 存 localStorage、fleet 卡片、per-worker send、4s 轮询。

**✅ #125 已修（2026-06-11, PR #126 已合）**: ① `_live_gui_sock()` 真实 unix-socket connect 测活(最新活 socket 优先, 死残留忽略) ② `_cli_run()` 所有 mux cli 调用钉死 `WEZTERM_UNIX_SOCKET`, 无活 socket 快速报错 ③ `list_panes()` mux 不可达返回 None → `collect_sessions()` 返回空 fleet(不再回退 runtime.json 缓存 → 幽灵会话根除) ④ mobile `api()` 对非 2xx 抛错 → send 失败手机端弹错误条。13 新测试 `test_fleet_liveness.py`, 全 56 绿。实测: Kaji 不跑时 `sessions` 输出 `[]`。

**✅ Funnel 公网通（2026-06-11）**: `tailscale funnel --bg 8787` → `https://kaji-mac.taild66623.ts.net/`。手机**免装 Tailscale、不占 VPN 槽、梯子照开**。实测: healthz ✓ / 无 token 401 ✓ / 带 token 200 ✓。安全模型变化: token 成唯一防线(48 hex)。不用时 `tailscale funnel off`。本机 curl 测试要绕 Clash fake-IP DNS(见 pitfalls)。

**竞品调研（2026-06-11, 详见 kaji repo `docs/remote.md` Prior art 节）**: 业界全员同构 = **出站 relay, 零入站端口, 无人用 VPN**。Anthropic RC(`claude rc`, 轮询 API, 仅 Claude Code) / Omnara(闭源 SaaS relay) / **Happy(slopus/happy, 开源, relay 仅 1.3k 行 TS, AES-256-GCM + QR 配对, 自托管)= 最佳参考实现** / ⚠️ **happier fork 已做多 harness E2E, 与我们 wedge 撞车要盯**。结论: 自建薄 relay 是终态(Mac 出站 WS + 手机 HTTPS + QR/E2E), Funnel 是零代码垫脚石。差异化护城河 = fleet mission control + 共享 memory/skills。

**双线决议（2026-06-11）**: 手机 = killer demo 钩子, **电脑 = 主工位**, 两线并进。电脑线 = launchd 常驻(tailscaled+serve 今天又全死一遍, 紧迫) + cockpit 交互循环。

## Architecture facts

- Origin: forked from Kaku (WezTerm-based, **Rust + GPU rendering** — NOT Tauri).
- Why Kaku/WezTerm path: Lua programmability is decisive; Ghostty renders faster but no Lua.
- First Mate = 无状态 dispatcher（NL→spawn/send，confirm-gated，无规划）→ 重引擎理由基本不成立. helm-brain 暴露为 **MCP server** 让引擎可换.
- CI split = path-filtered Cargo Check + always-on Lint/brand-guard; main branch-protected, self-merge OK. rename 回归 guard（grep 残留 Helm 品牌字 + plist bundle id 断言）.
- Theme: Kaku Light + Auto (warm cream by day, dark at night); settings TUI = `helm config` (separate process, parses config file text — does NOT eval lua).
- Config: `~/.config/helm/kaku.lua` (dev-link symlink → repo `assets/macos/Helm.app/Contents/Resources/kaku.lua`). Isolated from Kaku (own mux socket `~/.local/share/helm/`).
- Memory sharing: Claude Code reads `~/.claude/CLAUDE.md` (symlinked to AGENTS.md); other harnesses get `PACK_MEMORY_FILE` env var.
- Tool binaries still named `helm-*` (rename → `kaji-*` 决议 2026-06-10, in progress).
- Repo hygiene (2026-06-10): `delete_branch_on_merge` enabled on `interesting-vibe-coding/kaji`; 20 stale local branches purged; obsolete PR #113 closed (content already on main as 7a41888).

## Backbone landed (helm-brain serve)

`helm-brain serve` (HTTP+SSE, stdlib) — REST `/api/{state,sessions,quota,timeline,send,spawn,notify}` + SSE `/api/events`. reads 进程内 / writes shell out CLI (thin adapter, MCP 哲学). **安全**: 默认绑 127.0.0.1, 非 loopback 必须 token 否则拒启. cockpit 加 `--server URL` 成 HTTP client, client/server 分离端到端验证通 (手机=同一 client 换设备).

## Pitfalls (踩坑)

- **TCC 反复弹"访问其他 App 数据"**: ad-hoc 签名 → 授权无法持久化 + responsible 归因到 `fun.tw93.kaku`; 只有 Developer ID 签名+公证能根治 (release blocker, 记在 `docs/release-checklist.md`). `--strip-mcp-config` 是错误假设, 无效.
- **设置页浅色系统下纯黑**: 设置 TUI 是独立进程 `helm config`, 只解析配置文件文本、不求值 lua, 故 `config.color_scheme=None` → 落默认黑. 解: `builtin_kaku_theme` 在 None 时读配置文件文本主题意图 + 系统外观选 light/dark.
- **标签栏冒 "Users/Users/Users/"**: `format-tab-title` 偶发返回 None 时引擎回退到 pane cwd basename. 正解在引擎层: `compute_tab_title_from_precomputed` 的 None 分支直接渲染空白(不回退 cwd).
- **`cargo test -p procinfo` 报 "multiple lua features"**: 用 `cargo test -p procinfo --no-default-features --lib`.
- **改名后 symlink 断**: 改名后 `~/.claude/skills/helm-first-mate` symlink 仍指向已删的 `/Applications/Helm.app` → skill 加载失败. 改名涉及 app 路径时记得重链 symlink (CI guard 抓不到运行时 symlink 状态).
- **dev-link**: `~/.config/helm/kaku.lua` 是指向 repo 文件的符号链接; 设置 TUI 的 Save&Exit 会经此写回 repo, 改前确认 git diff.
- We actively port worthwhile upstream Kaku fixes (verbatim, with tests) — methodology + ported commits logged in `KIRO_MEMORY.md`.

### 从上游 Kaku 移植 fix 流程
1. `curl -fsSL https://github.com/tw93/Kaku/commit/<sha>.patch` 取 diff (GitHub API 无 token 会 403, 直接抓 .patch / expanded_assets 页更稳).
2. 逐文件 grep Helm 对应符号, 确认「已有 / 缺失 / 1:1」再动手.
3. 逐字应用 → `cargo test`/`cargo check -p <crate>` → `./scripts/build.sh --app-only` → 重装冷启动验证.
4. 独立分支 1 PR; PR body 用 `--body-file /tmp/x.md` (heredoc 直传 gh 会卡住). 等 Cargo Check 绿 → `gh pr merge --squash --delete-branch`.

## 2026-06-09 云端 session — Brain 定稿 + 发版/MCP

合并 #114(v0.4.0 发版: release.yml + CHANGELOG)、#115(events.jsonl substrate).

**Brain 定稿(本质)**: events.jsonl substrate → dispatcher 每次重读 fleet 状态 → 近无状态 → 不需要 auto-compaction/重引擎 → **Crush 反超 Goose**(Go 单二进制、MCP 原生、OpenRouter 免费模型). 形状: cockpit(纯可视化) ⟂ dispatcher(最清淡 harness) 中夹 helm-brain-as-MCP(harness 无关). 手机端 = relay,与引擎选型解耦.

**可复用(Kaji 相关):**
- **云端发 macOS release**: Linux 编不了 .app → `release.yml` tag `v*` 触发 macos runner 跑 `build.sh --app-only`; ad-hoc 签名无需密钥; `--app-only` 跳过 DMG 的 AppleScript layout(headless 会挂); 打 `Kaji.app.zip` → 建 **draft** release,人工冒烟后 Publish.
- **substrate 模式**: append-only JSONL; 写 best-effort 永不抛(别让日志搞崩主命令); 读跳坏行; 路径走 env 可注入 → 纯 stdlib 单测.
- **手搓极简 MCP server**: stdio = 换行分隔 JSON-RPC 2.0(**不是** Content-Length); initialize(回显 client protocolVersion)/tools/list/tools/call/ping; 通知不回; I/O 可注入 → fake 单测.

**Kaji 发版 footgun**: `kaku/Cargo.toml`=**0.12.0**(上游血统,塞 Info.plist),产品版本只走 **git tag**. 发版别动 Cargo.toml(改 0.4.0 反而 <0.12.0,搞坏 plist/auto-update 比较).

**留 mac**: `git tag v0.4.0 && git push` 发版→冒烟 zip→Publish; cockpit 接交互层(curses 要 tty)+ `Cmd+1`; MCP server 拿真 client live 握手 + 跑 write 工具.

> 跨项目坑(未授权 GitHub API 403、云端 git proxy 禁删分支)已上浮 `docs/pitfalls.md`,此处不再列。

**✅ 自建 relay 上线（2026-06-11, PR #128）**: `tools/kaji-relay/` = CF Worker + Durable Object 长轮询中继(Anthropic RC/Happy 同构, Mac 零入站端口)。手机 `https://relay.doabit.dev/c/<rid>/` → DO 队列 → Mac connector 出站长轮询 → 本地 serve → 回包。**国内直连 + 开梯子双通实测 200**(硬约束达成)。鉴权: `/agent/*` 走 X-Relay-Key worker secret; bearer token 端到端(relay 只转发不校验)。密钥: `~/.config/helm/relay-{id,key}`。坑: ① workers.dev 直连被 SNI 墙 → 必须自定义域(同 CF edge 即可) ② CF bot 防护 403 掉 Python-urllib 默认 UA → connector 自定义 UA ③ TOML 文件尾追加 key 会落进最后一个 [[table]] 块 ④ CF 账号缺 workers.dev 子域时 API `PUT /accounts/<id>/workers/subdomain` 一发注册。

**✅ launchd 常驻（2026-06-11）**: `dev.kaji.{tailscaled,brain-serve,relay-connector}` 三个 LaunchAgents（`~/Library/LaunchAgents/`）, KeepAlive + RunAtLoad, 挂了自动拉、重启自愈。nohup 时代结束。

**✅ 主战场一轮完成（2026-06-11 下午, PR #130/#131/#132 全合）**:
- **mobile cockpit v2（#130）**: 深奢视觉(espresso/cream/bronze/terracotta + 衬线 + 铜发丝线)、手机 spawn worker(harness chips + cwd 记忆 + 首任务)、卡片展开显时间线尾 5 条、桌面双列 grid、esc() 防 XSS。
- **codex 真额度（#131）**: quota.py codex() — 今日 UTC 目录、每文件取 LAST token_count(累积值, 求和会虚高!)、rate_limits used_percent/resets_at/plan 取全局最新 session。brain load_quota_raw() 20s memo; /api/state 加 limits; cockpit chip 显 "codex 1.2M · 62% left (plus)"。kaku.lua 状态栏向后兼容(additive key)。
- **cockpit 交互循环（#132）**: TUI 全屏循环(termios+select, 2s tick), ↑↓/jk 选, ⏎ 发指令, s spawn, r 刷, q 退; 写操作走 kaji-brain CLI 或 --server POST, cockpit 仍只是 spine 的客户端; parse_key 纯函数有测试。
- **必须项(用户钉死)**: Claude Code 额度剩余必须可见。路径: ~/.claude OAuth token + Anthropic usage API 探路, 退路网页抓取。排队列。

**远期已定（2026-06-11）**: 自有手机 App — 扫码即连（QR 配对换密钥, Happy 模式）, 界面 = Kaji Sun 设计语言。先 web cockpit 养形状, App 收割。

**Dogfood 实测（2026-06-11 晚, v0.5.0）**:
- ✅ Brain(Sonnet+MCP) 全链通: 人话 → 计划 → spawn_worker/send_to_worker → worker 收到执行 → waiting 事件回报。
- ✅ 原生确认上线(PR #138): Brain 去 skip-permissions, spawn/send 走 Claude Code 原生上下键确认; 只读工具白名单免弹。
- ⚠️ 用户体验结论: **借壳 claude code 的交互天花板已现**(确认框样式/对话流不可控) → 不影响当前推进, 但**自研轻引擎+自绘对话 UI = 既定终态**, MCP 工具协议届时原样平移。
- 🐛 #139 waiting 误报 → 修(PR #140): BUSY_MARKERS — 尾部画面含 'esc to interrupt' 等忙碌标记时, 指纹再稳也不判 waiting。
- 坑: `open -a Kaji` 可能被 LaunchServices 解析到 repo 里 dist/Kaji.app(dev build) — 验证装机版要 `open /Applications/Kaji.app` 绝对路径。

**坑（2026-06-11 补）**:
- relay 自维持故障循环: connector 掉线期间手机每 4s 排 job 进 DO 队列, pending 30s 过期但 job 滞留; connector 回归后逐个回放全 404, 还把 404 当致命错误 backoff → 永动失联。修: connector 跳过 404(stale job), worker 队列 stamp+过滤+cap 20。
- CI lint 挪 ubuntu 后 `plutil` 步骤永挂(macOS-only) → 换 python plistlib。
- Claude Code 1M 模型 auto-compact override 失效(官方 bug #53801, 阈值按硬编码 200k 算) → 1M session 只能手动 /compact。
- wrangler OAuth 过期 → 用 about-me 的 CF API token 走 env(CLOUDFLARE_API_TOKEN+ACCOUNT_ID)。

**舵 NL 派活过渡方案（2026-06-11）**: `kaji-brain plan "<order>"` — 一句人话 → claude -p sonnet → {send|spawn|none} JSON；cockpit `i`/`/` 唤舵输入 → 计划回显 → y/N → 执行。~9s 延迟。自研引擎前的过渡面。
**踩坑**: ⌘/ 在本机被豆包输入法全局快捷键抢占（弹它的设置面板, 按键到不了 Kaji）→ 用户需在豆包设置改掉; Kaji 侧 ⌘⇧⏎ 同款 toggle 兜底。

**v0.6.0 已发布（2026-06-11 晚）**: Kaji Sun 全家桶 — 日/夜双套色、⌘/ 两视图、Brain=自家 TUI、舵 NL 派活（直接打字+方向键确认+auto 模式）、双窗口权威配额、ctx%、新 logo、relay 修复、codex 检测/发送修复。发版法: 无 Rust 变更 → 基于上版 zip 覆盖 Resources + ad-hoc 重签 + gh release create。
**Chat 后端现状**: `claude -p --model sonnet` 单发无状态（每次带舰队快照, ~9s）。终态自研常驻引擎。

**过夜冲刺（2026-06-11 深夜, 自治）**:
- 手机舵线（#157）: POST /api/plan + planbar 卡片（执行/取消/改一改 chips）。
- planner 9s→~2.5s（#158）: 直连 /v1/messages（CC OAuth token + haiku）, CLI 兜底; prompt 加硬: 闲聊→none, send text 必须祈使句。
- focus_pane 真聚焦（#159）: tab:activate 不切 pane → compass/键盘留在 Brain 的根因; p:activate() 补上。
- README v0.6 对齐（#160）: 舵线头条、⌘/ 双视图、Sun 色语、双窗额度; 中英同步。
- QR 配对: `kaji-brain qr [--rotate] [out.png]` — token 走 URL #fragment（不经 relay 服务器）, 手机端自动收存; --rotate 换 token + 重启 serve。segno 已 vendor。

**过夜冲刺 II（2026-06-11 深夜）**:
- demo GIF（#162）: vhs 无头录 cockpit --demo（Sun Night + 舵线打字）→ assets/demo.gif, README 双语嵌入。
- Landing（#163）: kaji.doabit.dev — docs/index.html 单文件 Sun 风（hero + 一键复制安装 + gif + 五特性）; GitHub Pages(main /docs) + CF CNAME, HTTP 已通, HTTPS 证书签发中(waiter 挂着)。repo About homepage/description 已设。
- doctor 重写（#164)）: v0.6 现实体检（app/harness/token/serve/relay/quota）, 每个 ✗ 带修复命令; `kaji-brain doctor`。
- mobile timeline（#165）: 选中行二次 tap → inline 最近 5 事件。
- 额度纪律: 5h 窗 92% 时停手写状态; 哨兵(3min 轮询)报 STOP/RESUME。

**自研引擎（2026-06-12, PR #169）**:
- `tools/brain-cockpit/engine.py` ✅: 多轮 tool-use 循环, stdlib only; 工具 list_sessions/fleet_timeline(只读自动跑) + spawn/send(yield 给 cockpit 确认门); 生成器协程协议 turn()/feed(); 中文大副 persona 纯文本。
- **传输 free-first** ✅: 默认 OpenRouter `qwen/qwen3-next-80b-a3b-instruct:free`($0, 中文强, tool use 稳, 262K ctx, key 在 fish env), 失败 sticky 回退 CC OAuth haiku。共享 `_post`: 只走系统代理(铁律), 429/垃圾400/5xx/SSL-EOF 同路径重试。内部史保持 Anthropic blocks, OpenAI 格式 per-call 适配。
- cockpit 接线 ✅: ⏎ → engine.turn(); say→transcript 渲染; act→confirm 模式 _choose(执行/取消/改一改)/auto 直执; eng 懒加载; 引擎加载失败回退 nl_plan。
- 实测 ✅: 免费模型自查舰队中文汇报; 多步链 观察→send(祈使句)→收尾; OAuth haiku 链同通。smoke 默认 dry-run(--live 才真执行)。
- 测试: test_engine.py 7 个离线(adapters+协程协议), CI discover 自动收。
- **约束(实测)**: OAuth /v1/messages 上 **sonnet 必 429**(Max 留给 CC 客户端); OpenRouter free 池限 ~200 req/day/模型(账户充$10 后 1000/day); 偶发 RemoteDisconnected/400 = 代理抖动, 重试即过。
- 免费模型调研存档: Cerebras(Llama3.3-70B, 1M tok/day)和 Groq(14400 req/day)更快更宽, 但需新开账号——以后用户自己注册可切, env `KAJI_ENGINE_BACKEND`/`KAJI_ENGINE_OR_MODEL` 已留口。
- 今晨修复(#168 已合): spawn 时登记 runtime.json(codex node 壳连 wezterm 都报不出进程名→检测改注册制), lua adopt 5s, ESC/Ctrl-U 清舵线。
- 杂记: 顶栏 "Users/" 泄漏(新 tab title)待查(需可视复现); status bar compass 切换延迟已修(#159)。

**Next（当前队列）**: ① cockpit 交互循环 + mobile/desktop UI 设计打磨（主战场: 轻量·交互·可视化, 管多 harness 必须比终端切换方便得多）② 统一额度 scraper ③ relay 加 QR 配对 + E2E 加密（launch 前安全叙事）④ demo（最后录）。
