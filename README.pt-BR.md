<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>O terminal nativo para agentes. Você guia o leme — os agentes executam.</em></p>

  <p>
    <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon%20%2B%20Intel-lightgrey?style=flat-square" alt="macOS">
  </p>
</div>

<div align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <b>Português</b>
</div>

---

A maioria dos terminais pressupõe um humano, uma sessão. **O Helm pressupõe que você está comandando uma frota de agentes** — eles fazem o trabalho, trazem à tona o que precisa de você e aguardam o seu comando.

### Zero fricção

Você não deveria ter que cuidar de um terminal. Sem caçar qual painel espera entrada, sem perder o fio da meada entre ferramentas, sem configurar nada antes de começar. Instale, abra e você já está conversando com os seus agentes. **Você toma as decisões; eles fazem todo o resto.**

### Conheça o seu imediato

Mesmo rodando dez agentes, você ainda acaba vigiando dez painéis. O **Brain** do Helm remove essa última fricção: em vez de fazer malabarismos com N agentes, você fala com **um**.

O Brain é um orquestrador baseado no Sonnet. Ele vigia cada sessão por você — quem está trabalhando, quem está esperando, quanto cada um está custando —, avisa apenas quando algo realmente precisa de você e repassa as suas ordens ao agente certo, sempre pedindo confirmação antes que qualquer coisa seja executada.

> **N agentes → uma conversa.** Você deixa de varrer uma parede de terminais e passa a guiar o leme por meio de um imediato que conhece toda a tripulação.

### Três visões, uma tecla cada

**Brain** — fale com o seu imediato.
**Workspace** — onde você e os seus agentes trabalham.
**Monitor** — cada sessão num relance: estado, tempo de execução, custo.

Alterne entre elas num instante. O Helm mostra as teclas quando você precisa — nada para memorizar.

---

## Instalação

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Abra o Helm: ele conduz você por uma configuração rápida e o leva direto ao Brain. Diga a ele no que trabalhar.

<details>
<summary>Compilar a partir do código-fonte</summary>

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
