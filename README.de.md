<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>Das Terminal für Agenten. Du steuerst — die Agenten führen aus.</em></p>

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
  <b>Deutsch</b> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

Die meisten Terminals gehen von einem Menschen und einer Sitzung aus. **Helm geht davon aus, dass du eine Flotte von Agenten dirigierst** — sie erledigen die Arbeit, legen dir vor, was deine Entscheidung braucht, und warten auf dein Kommando.

### Null Reibung

Du solltest kein Terminal bemuttern müssen. Kein Suchen, welches Fenster eine Eingabe erwartet, kein Verlieren des Fadens zwischen den Werkzeugen, kein Einrichten, bevor du loslegen kannst. Installieren, öffnen — und schon sprichst du mit deinen Agenten. **Du triffst die Entscheidungen; alles dazwischen erledigen sie.**

### Lerne deinen Steuermann kennen

Selbst mit zehn Agenten musst du am Ende zehn Fenster im Blick behalten. Helms **Brain** beseitigt diese letzte Reibung: Statt N Agenten zu jonglieren, sprichst du mit **einem**.

Das Brain ist ein Sonnet-Orchestrator. Es behält jede Sitzung für dich im Auge — wer arbeitet, wer wartet, was sie kosten —, meldet sich nur, wenn dich wirklich etwas braucht, und leitet deine Befehle an den richtigen Agenten weiter, immer mit Rückfrage, bevor etwas ausgeführt wird.

> **N Agenten → ein Gespräch.** Du musst keine Wand aus Terminals mehr absuchen, sondern steuerst durch einen Steuermann, der die ganze Mannschaft kennt.

### Drei Ansichten, je ein Tastendruck

**Brain** — sprich mit deinem Steuermann.
**Workspace** — wo du und deine Agenten arbeiten.
**Monitor** — jede Sitzung auf einen Blick: Zustand, Laufzeit, Kosten.

Wechsle blitzschnell zwischen ihnen. Helm blendet die Tasten ein, wenn du sie brauchst — nichts zum Auswendiglernen.

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Öffne Helm: Es führt dich durch eine kurze Einrichtung und setzt dich dann direkt ins Brain. Sag ihm, woran es arbeiten soll.

<details>
<summary>Aus dem Quellcode bauen</summary>

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
