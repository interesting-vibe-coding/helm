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

打开 Kaji，Brain 向你问好。告诉它要造什么。

## 你会得到什么

**一个终端，所有代理。** Worker 在一个 Work 视图（`Cmd+2`）里自动平铺 —
claude 挨着 codex 挨着 kiro，不用翻标签页。每个 harness 启动即载入你的共享
memory 和 skills。

**一眼读懂的舰队。** 驾驶舱（`Cmd+1`）按"最被冷落优先"排序：琥珀色 = worker
在等你，青色 = 正在干活。选中一个 worker，按 ⏎，输入 — 指令直达它的 pane。

**额度看得见。** 每个 harness 今日 token 消耗；harness 暴露真实配额时直接显示
剩余百分比 — 别在错误的模型上烧掉一晚上的预算。

**手机操舵。** `kaji-brain serve` + 内置 relay 把同一个驾驶舱放进手机浏览器 —
看状态、看额度、发指令、开 worker — 纯 HTTPS。Mac 不开入站端口，手机不占
VPN 槽，挂代理也能用。见 [docs/remote.md](docs/remote.md)。

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
