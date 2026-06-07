<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>Le terminal pensé pour les agents. Vous tenez la barre — les agents exécutent.</em></p>

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
  <b>Français</b> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

La plupart des terminaux supposent un humain, une session. **Helm part du principe que vous orchestrez une flotte d'agents** : ils font le travail, font remonter ce qui requiert votre attention et attendent vos ordres.

### Zéro friction

Vous ne devriez pas avoir à surveiller un terminal. Plus besoin de chercher quel panneau attend une saisie, de perdre le fil entre les outils, ni de configurer quoi que ce soit avant de commencer. Installez, ouvrez, et vous parlez déjà à vos agents. **Vous décidez ; ils font tout le reste.**

### Faites connaissance avec votre second

Même en lançant dix agents, vous finissez par surveiller dix panneaux. Le **Brain** de Helm supprime cette dernière friction : au lieu de jongler avec N agents, vous parlez à **un seul**.

Le Brain est un orchestrateur Sonnet. Il surveille chaque session à votre place — qui travaille, qui attend, ce que chacun coûte —, ne vous signale que ce qui requiert vraiment votre attention et transmet vos ordres au bon agent, en demandant toujours votre accord avant que quoi que ce soit ne soit lancé.

> **N agents → une seule conversation.** Vous cessez de balayer un mur de terminaux pour tenir la barre à travers un second qui connaît tout l'équipage.

### Trois vues, une touche chacune

**Brain** — parlez à votre second.
**Workspace** — là où vous et vos agents travaillez.
**Monitor** — toutes les sessions d'un coup d'œil : état, durée d'exécution, coût.

Passez de l'une à l'autre instantanément. Helm fait apparaître les touches quand vous en avez besoin — rien à mémoriser.

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Ouvrez Helm : il vous guide à travers une configuration rapide, puis vous dépose directement dans le Brain. Dites-lui sur quoi travailler.

<details>
<summary>Compiler depuis les sources</summary>

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
