<div align="center">
  <img src="assets/kaji-logo.png" width="110" alt="Kaji" />
  <h1>Kaji</h1>
  <p><em>AI 编码代理的舰队指挥台 — 在终端里，也在你口袋里。</em></p>
  <p><a href="README.md">English</a></p>
</div>

---

Kaji 让一支编码代理舰队 — Claude Code、Kiro、opencode、Codex — 并排干活，给你一个安静的台面统一操舵：所有 worker 一眼可见、额度一目了然、手机网页随处可控。你握舵（舵, *kaji*），代理划桨。

> 前额叶是有限的。
> 别再把它花在代理之间切换上下文上。`(ᴗ‿ᴗ)`

![Kaji mission control](assets/screenshot.png)

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/kaji/main/install.sh | bash
```

打开 Kaji，Mission Control 迎接你。说出要造什么。

## 你会得到什么

**说一句，别管理。** Mission Control 打开就是舵线 — 输入一句话（*"开个
codex 去 wu 修一下 newsletter 路由"*），小模型把它翻成计划，方向键确认
（或 `Tab` 切到 auto 模式直接放行），worker 就划起来了。没有表单，没有参数。

**两个视图，一个键。** `Cmd+/` 在 **Mission Control**（舰队、额度、舵线）和
**Work**（你刚在操的 worker）之间翻转 — 这就是全部导航。`Cmd+Shift+K` 启动
任意 harness；worker 自动并排平铺 — claude 挨着 codex 挨着 kiro。

**一眼读懂的舰队。** Kaji Sun 日夜双色：唯一的柿橙只有一个意思 — *有 worker
需要你*。干活是墨色，干完淡成灰。每个 session 都显示上下文窗口占用
（`ctx 18%`）— 在它忘掉你的上午之前。

**额度信得过。** 5 小时窗与周窗的真实用量，直取官方端点（Claude OAuth usage
API、Codex app-server）— 驾驶舱、状态栏、手机上都看得到。烧掉一晚上预算之前
先知道。

**手机操舵。** `kaji-brain serve` + 内置 relay 把同一个驾驶舱 — 含舵线 —
放进手机浏览器，纯 HTTPS。Mac 不开入站端口，手机不占 VPN 槽，挂代理也能用。
见 [docs/remote.md](docs/remote.md)。

**引擎无关。** Brain 是事件底座之上的一层薄服务（CLI + HTTP + MCP），不是一个
模型。任何 harness 都可以当 worker；任何客户端（终端驾驶舱、手机、脚本，想要
的话也可以是一个 LLM）都可以握舵。

## 为什么是这个形状

"远程遥控你的代理"已是红海 — 但每一家都把你锁在单一厂商的代理上。Kaji 反着押
注：难的不是和一个代理说话，而是*同时跑一支异构舰队*还不撕碎你的注意力。所以
主干是 harness 无关的舰队控制 + 共享记忆 — 而承载它的终端，正是为此而造。

---

站在 [Kaku](https://github.com/tw93/Kaku)、
[WezTerm](https://wezfurlong.org/wezterm/) 的肩膀上，也感谢
[Ghostty](https://ghostty.org) 推动终端前进。MIT 协议 — 见 [LICENSE.md](LICENSE.md)。
