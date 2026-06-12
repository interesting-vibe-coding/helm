# Kaji Sun / Ember — the product's own visual language (v2)

Kaji 从 Kaku 迁移而来，视觉已自立门户。**Persimmon-led**：柿橙 `#f25c05` 全产品
唯一主角色，唯一含义 = **needs you / where you act**。其余全部退成安静的暖墨，
橙色才有意义。两副面孔，一个太阳：

- **Kaji Sun (day)** — paper 底 + warm ink
- **Kaji Ember (night)** — ember 暖黑 + candle-lit cream，永不纯黑、永不冷黑

v1 草案 token（#ff7a1f ember / amber / teal 三色状态）已废弃；v2 = 实际落地值，
终端壳 (kaku.lua) / cockpit / 手机页三处共用。

## Tokens（shipped, 单一真源）

| token | night (Ember) | day (Sun) | 用途 |
|-------|---------------|-----------|------|
| `bg` | `#16100b` | `#fbf8f2` | 底色：ember black / paper |
| `surface` | `#211810` | `#ffffff` (card) | 浮起面板 |
| `surface-high` | `#2a2016` | `#e8e2d6` | active / hover / split |
| `ink` | `#ece4d6` | `#211c15` | 正文，永不 #fff / #000 |
| `mute` | `#9c9283` | `#8a8174` | 次要文字 |
| `ash` | `#665e53` | `#b5ab9c` | 静默 / inactive / hints |
| **`sun`** | **`#f25c05`** | **同** | **唯一主角：needs you / 输入处 / 品牌** |
| `err` | `#e05a48` | `#c03a2b` | 错误（不与 sun 抢戏） |

状态语言（fleet 行）：waiting = sun 点 + sun 文字；working = ink 点；idle/done = ash。
没有第三种状态色 — amber/teal 已废。

终端 ANSI 16 色 = 同族暖移（见 kaku.lua `kaji_ember` / `kaji_sun`）；
scheme 注册名暂留 `'Kaku Dark'/'Kaku Light'`（kaku_theme.rs 从配置文本 parse
这两个字面量），`'Kaji Ember'/'Kaji Sun'` 为别名，Rust 正名轮一起改。

字体：serif display（Georgia/Cormorant，仅字标）+ mono（一切数据与正文）。
Glow 全局最多两处（waiting 脉冲 + helm line 投影），多则廉价。

## Brand marks — 一符一义

| 符号 | 义 | 出现处 | 不出现处 |
|------|----|--------|----------|
| `KAJI` 字标 (KA ink + JI sun, serif) | 产品名 | 各 surface 头部，一处 | 正文 / 按钮 / 提示 |
| `◉` 轮标 | 产品的声音（大副回话） | 头部字标左侧；transcript 回话行首 | 输入行 |
| `舵` | 你手中的舵（输入） | helm line prompt（cockpit + 手机输入框），仅此 | 说话人标签 / 头部 / 文案 |

规则：**每个符号只有一个含义；同一含义只有一个符号。** transcript 的说话人
是 `you` / `◉`（你与船）；舵 只标记你打字的地方。除 舵 外 UI 零 CJK
（#174 英文化决议）；"kaji" 小写出现时一律指 project 名，不指产品。

## 高级 + 方便（设计原则）

- 高级 = 克制：一个主角色、serif 仅点睛、留白、发丝线。绝不堆色。
- 方便 = 零寻找：最该管的永远在最上、键提示长在行内、helm line 永远一击可达。
- 同温：终端壳 = cockpit = 手机，Cmd+/ 切换无温差（v0.6.5 后已达成）。

## 实施状态

1. ✅ cockpit.py Sun Day/Night 调色（KAJI_THEME 跟随窗口主题）
2. ✅ 手机页 light/dark（prefers-color-scheme，#185）
3. ✅ 终端壳 Kaji Ember / Kaji Sun（kaku.lua scheme + 窗框 + tab bar + compass，#192）
4. ✅ 品牌符号一符一义（本轮）
5. 远期：Rust 正名轮（scheme 注册名 / helm-* 二进制 / ~/.config/helm 路径）；
   自绘 GUI overlay 复用 token
