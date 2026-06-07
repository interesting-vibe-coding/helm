<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>エージェントのためのターミナル。あなたは舵を取り、エージェントが実行する。</em></p>

  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon%20%2B%20Intel-lightgrey?style=flat-square" alt="macOS">
  </p>
</div>

<div align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <b>日本語</b> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

たいていのターミナルは、一人の人間と一つのセッションを前提にしています。**Helm は、あなたがエージェントの艦隊を指揮していることを前提にします** —— 彼らが作業を進め、あなたの判断が要るものを差し出し、指示を待ちます。

### ゼロフリクション

ターミナルのお守りをする必要はありません。どのペインが入力待ちかを探す手間も、ツール間で作業の流れを見失うことも、始める前のセットアップもありません。インストールして開けば、もうエージェントと話し始めています。**判断はあなたが下し、その間のすべては彼らがこなします。**

### あなたの一等航海士

エージェントを十体動かしても、結局は十のペインを見張ることになります。Helm の **Brain** は、その最後のひと摩擦を取り除きます。N 体のエージェントを操る代わりに、あなたは**一人**と話すのです。

Brain は Sonnet によるオーケストレーターです。すべてのセッションをあなたの代わりに見守り —— 誰が働き、誰が待ち、それぞれいくらかかっているか —— 本当にあなたの判断が必要なときだけ報告し、あなたの指示を適切なエージェントへ伝えます。しかも何かが実行される前には必ず確認を取ります。

> **N 体のエージェント → 一つの会話。** ずらりと並んだターミナルを見渡すのをやめ、乗組員全員を把握した航海士を通じて舵を取り始めます。

### 三つのビュー、それぞれワンキー

**Brain** —— 一等航海士と話す。
**Workspace** —— あなたとエージェントが作業する場所。
**Monitor** —— すべてのセッションを一目で：状態、稼働時間、コスト。

その間を瞬時に切り替えられます。必要なときに Helm がキーを差し出してくれる —— 覚えることは何もありません。

---

## インストール

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Helm を開くと手早いセットアップを案内し、そのまま Brain へと送り出します。何に取り組むかを伝えてください。

<details>
<summary>ソースからビルド</summary>

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
