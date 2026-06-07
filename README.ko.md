<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>에이전트를 위한 터미널. 당신은 키를 잡고 — 에이전트가 실행한다.</em></p>

  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon%20%2B%20Intel-lightgrey?style=flat-square" alt="macOS">
  </p>
</div>

<div align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <b>한국어</b> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

대부분의 터미널은 한 사람, 하나의 세션을 전제로 합니다. **Helm은 당신이 에이전트 함대를 지휘한다고 전제합니다** — 그들이 일을 하고, 당신이 필요한 것을 올려 보내며, 당신의 부름을 기다립니다.

### 제로 마찰

터미널을 돌볼 필요는 없습니다. 어느 창이 입력을 기다리는지 찾아 헤맬 일도, 도구 사이에서 흐름을 놓칠 일도, 시작하기 전 설정할 일도 없습니다. 설치하고 열면, 이미 에이전트와 대화하고 있습니다. **결정은 당신이 내리고, 그 사이의 모든 것은 그들이 합니다.**

### 당신의 일등 항해사

에이전트를 열 개 돌려도 결국 열 개의 창을 지켜봐야 합니다. Helm의 **Brain**은 그 마지막 마찰을 없앱니다. N개의 에이전트를 저글링하는 대신, 당신은 **하나**와 대화합니다.

Brain은 Sonnet 오케스트레이터입니다. 당신을 대신해 모든 세션을 지켜봅니다 — 누가 일하고, 누가 기다리며, 각자 비용이 얼마인지를 — 정말로 당신이 필요할 때만 보고하고, 당신의 지시를 알맞은 에이전트에게 전달합니다. 그리고 무엇이든 실행되기 전에 항상 먼저 확인을 구합니다.

> **N개의 에이전트 → 하나의 대화.** 줄지어 늘어선 터미널을 훑어보는 대신, 모든 선원을 꿰고 있는 항해사를 통해 키를 잡기 시작합니다.

### 세 가지 화면, 각각 한 번의 키

**Brain** — 일등 항해사와 대화합니다.
**Workspace** — 당신과 에이전트가 함께 일하는 곳.
**Monitor** — 모든 세션을 한눈에: 상태, 실행 시간, 비용.

그 사이를 즉시 오갑니다. 필요할 때 Helm이 키를 올려 보여줍니다 — 외울 것은 없습니다.

---

## 설치

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Helm을 열면 빠른 설정을 안내한 뒤, 곧장 Brain으로 데려다줍니다. 무엇을 할지 알려주세요.

<details>
<summary>소스에서 빌드</summary>

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
