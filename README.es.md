<div align="center">
  <img src="assets/helm-logo.png" width="120" alt="Helm" />
  <h1>Helm</h1>
  <p><em>La terminal nativa para agentes. Tú llevas el timón — los agentes ejecutan.</em></p>

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
  <b>Español</b> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pt-BR.md">Português</a>
</div>

---

La mayoría de las terminales asumen un humano y una sesión. **Helm asume que estás dirigiendo una flota de agentes**: ellos hacen el trabajo, te muestran lo que requiere tu atención y esperan tu orden.

### Cero fricción

No deberías tener que vigilar una terminal. Sin buscar qué panel espera tu entrada, sin perder el hilo entre herramientas, sin configurar nada antes de empezar. Instala, abre y ya estás hablando con tus agentes. **Tú tomas las decisiones; ellos hacen todo lo demás.**

### Conoce a tu segundo de a bordo

Aunque ejecutes diez agentes, sigues teniendo que vigilar diez paneles. El **Brain** de Helm elimina esa última fricción: en lugar de hacer malabares con N agentes, hablas con **uno**.

El Brain es un orquestador basado en Sonnet. Vigila cada sesión por ti —quién trabaja, quién espera, cuánto cuesta cada uno—, te avisa solo cuando algo realmente te necesita y transmite tus órdenes al agente correcto, pidiéndote siempre confirmación antes de que algo se ejecute.

> **N agentes → una conversación.** Dejas de recorrer un muro de terminales y empiezas a llevar el timón a través de un segundo que conoce a toda la tripulación.

### Tres vistas, una tecla cada una

**Brain** — habla con tu segundo de a bordo.
**Workspace** — donde tú y tus agentes trabajáis.
**Monitor** — cada sesión de un vistazo: estado, tiempo de ejecución y coste.

Cambia entre ellas al instante. Helm te muestra las teclas cuando las necesitas; no hay nada que memorizar.

---

## Instalación

```bash
curl -fsSL https://raw.githubusercontent.com/interesting-vibe-coding/helm/main/install.sh | bash
```

Abre Helm y te guiará por una configuración rápida para dejarte directamente en el Brain. Dile en qué quieres que trabaje.

<details>
<summary>Compilar desde el código fuente</summary>

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
