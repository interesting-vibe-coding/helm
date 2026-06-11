# Kaji Ember — the terminal's own visual language (v1)

Kaji 从 Kaku 迁移而来，但视觉自立门户。**Orange-led**：ember 橙 = 能量、决断、
船长的颜色（Hermès / Veuve 一脉的奢侈品橙）。全局只有这一个主角色，其余全部
退成安静的暖墨 — 橙色才有意义。

Mockup: `mission-control-mockup.html`（浏览器直接开）。

## Tokens

| token | hex | 用途 |
|-------|-----|------|
| `bg` | `#16100b` | ember black — 暖黑，永不纯黑 |
| `surface` | `#211810` | 浮起面板 |
| `line` | `#38291a` | 发丝线 |
| `ink` | `#f0e7d8` | 正文 cream，永不 #fff |
| `dim` | `#9b8c77` | 次要文字 |
| **`ember`** | **`#ff7a1f`** | **主角：品牌 / 选中 / 船长动作** |
| `ember-deep` | `#c25a10` | 按下 / 深橙 |
| `amber` | `#e8b339` | waiting（需要你）— 呼吸脉冲 |
| `teal` | `#4fc8a8` | working（别打扰） |
| `ash` | `#6b5f50` | idle / done（安静） |

字体：serif display（Cormorant/Georgia，品牌字）+ mono（数据）。
Glow 全局最多两处（waiting 脉冲 + helm line 投影），多则廉价。

## 结构决议

**两个视图，一个键**：`⌘/` 在 Mission Control ⇄ Work 之间切换。废除 ⌘1/2/3/4。

Mission Control（取代旧 Brain+Monitor 两视图）四层，自上而下：
1. **Fuel gauges** — 每 harness 一张燃料卡：今日 tokens / 剩余 %（有真配额时）+ 进度条
2. **Fleet board** — most-neglected first；每行：状态点 · harness·project · 最后事件摘要 · 状态+runtime · 行内键提示（选中行 ember 描边 + 左侧 ember 条）
3. **River** — 事件时间线（船长动作 ember 标记，worker 事件暖墨）
4. **Helm line**（底部固定）— 即 Brain 对话入口：打一句指令，dispatcher（MCP 任意引擎）规划执行；上方 fleet/river 就是同一底座的可视化

键位：`↑↓` 选 · `⏎` 回复/发指令 · `s` spawn · `o` 跳到该 worker pane · `⌘/` 切视图。

## 高级 + 方便（设计原则）

- 高级 = 克制：一个主角色、serif 点睛、留白、发丝线。绝不堆色。
- 方便 = 零寻找：最该管的永远在最上、键提示长在行内、helm line 永远一击可达。
- TUI 与未来 GUI overlay 共用此 token 表（cockpit.py 调色已对齐方向，逐步收敛）。

## 实施路径

1. cockpit.py 换 Ember 调色 + fuel gauges + river + helm line（TUI 先行）
2. kaku.lua：两视图重构 + `⌘/` 切换（Mission Control = cockpit pane + Brain pane 同屏或同 pane 切换）
3. 远期：自绘 GUI overlay 复用 token，弃 claude code 壳
