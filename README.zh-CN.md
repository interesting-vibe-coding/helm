<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>为 agent 而生的终端。你掌舵 —— agent 执行。</em></p>

  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon%20%2B%20Intel-lightgrey?style=flat-square" alt="macOS">
  </p>
</div>

<div align="center">
  <a href="README.md">English</a> ·
  <b>简体中文</b> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

大多数终端默认只有一个人、一个会话。**Helm 默认你正在指挥一支 agent 舰队** —— 它们干活、把需要你的事呈上来，然后等你发话。

### 零摩擦

你不该围着终端打转。不用再找哪个窗格在等输入，不会在工具之间丢失上下文，开始之前也无需任何配置。装好、打开，你就已经在和你的 agent 对话了。**你做决策；中间的一切交给它们。**

### 认识你的大副

哪怕跑十个 agent，也还是得盯着十个窗格。Helm 的 **Brain** 抹掉了最后这点摩擦：你不再周旋于 N 个 agent 之间，而是只和**一个**对话。

Brain 是一个 Sonnet 调度者。它替你盯着每一个会话 —— 谁在工作、谁在等待、各自花了多少 —— 只在真正需要你时才汇报，并把你的指令转达给对的 agent，且在任何动作落地前都会先征求你的同意。

> **N 个 agent → 一场对话。** 你不必再扫视一整面终端墙，而是通过一位熟悉全员的大副来掌舵。

### 三个视图，各一个快捷键

**Brain** —— 与你的大副对话。
**Workspace** —— 你和 agent 一起干活的地方。
**Monitor** —— 一眼看尽每个会话：状态、运行时长、花费。

随手在它们之间切换。需要时 Helm 会把按键提示呈上来 —— 什么都不用记。

---

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

打开 Helm，它会带你走完一段快速设置，然后径直把你送进 Brain。告诉它要做什么就好。

<details>
<summary>从源码构建</summary>

```bash
git clone https://github.com/interesting-vibe-coding/helm
cd helm
PROFILE=debug ./scripts/build.sh --app-only
open dist/Helm.app
```
</details>

---

<div align="center">
  <sub>A focused fork of <a href="https://github.com/tw93/Kaku">Kaku</a> · built on <a href="https://wezfurlong.org/wezterm/">WezTerm</a> · MIT</sub><br/>
  <sub>Part of <a href="https://github.com/interesting-vibe-coding">interesting-vibe-coding</a></sub>
</div>
