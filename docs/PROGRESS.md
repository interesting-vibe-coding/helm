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

**Next（当前队列）**: ① cockpit 交互循环 + mobile/desktop UI 设计打磨（主战场: 轻量·交互·可视化, 管多 harness 必须比终端切换方便得多）② 统一额度 scraper ③ relay 加 QR 配对 + E2E 加密（launch 前安全叙事）④ demo（最后录）。
