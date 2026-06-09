# Moved → `helm-first-mate` skill

The Kaji First Mate persona now lives in the cross-harness **`helm-first-mate`**
skill (single source of truth):

- In the repo: `assets/skills/helm-first-mate/SKILL.md`
- Bundled in the app: `Helm.app/Contents/Resources/skills/helm-first-mate/`
- Symlinked for harnesses by `first_run.sh`: `~/.kiro/skills/helm-first-mate`

`launch-brain.sh` activates it with a short message instead of injecting a
multi-KB system prompt.
