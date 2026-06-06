# Helm User Study Protocol

## Overview

Within-subjects study comparing Helm against a standard terminal baseline for AI-agent-assisted development tasks. N=16 developers, counterbalanced order, three 15-minute tasks per condition.

---

## 1. Participants

- **N = 16** professional developers
- **Screening criteria**: active daily use of at least one AI coding agent (Claude Code or Kiro) for ≥ 4 weeks
- **Recruitment**: developer communities (Discord, Reddit r/ClaudeAI, Kiro waitlist), snowball via researcher network
- **Compensation**: $60 Amazon gift card (90 min total)
- **Exclusion**: participants who have previously used Helm or contributed to the codebase

---

## 2. Study Design

**Type**: Within-subjects, 2 conditions, counterbalanced (Latin square for task × condition order)

| Condition | Setup |
|-----------|-------|
| **Baseline** | iTerm2 + tmux, same AI CLIs (Claude Code / Kiro / opencode) installed |
| **Helm** | Helm.app, same AI CLIs, default Helm configuration |

Both conditions use identical agent credentials and model access. Participants are given 5 minutes of orientation per condition before tasks begin.

---

## 3. Tasks

Each task is ~15 minutes. A moderator observes; screen + audio recorded with consent.

### Task A — Parallel Feature Implementation
> "You have 3 independent features to implement in this codebase. Use 3 separate agent sessions simultaneously. When all three are done, show me the results."

- 3 pre-scoped features of similar complexity (~30 min single-agent work each)
- Participant must manage agent coordination themselves
- Ends when all 3 features pass provided unit tests

### Task B — Review Cycle
> "Each of these 5 files has been modified by an agent. Review each change, approve or reject it, and leave a comment explaining your decision."

- 5 files, each with one AI-generated diff
- Participant must switch contexts between each review
- Ends when all 5 decisions are logged in the provided review sheet

### Task C — Context Handoff
> "You started this feature in Kiro yesterday. Continue it now using Claude Code, picking up exactly where Kiro left off."

- Provides a realistic Kiro session with partial work and a memory file
- Participant must transfer context to Claude Code and continue
- Ends when the feature is demonstrably continued (new code committed)

---

## 4. Metrics

### Primary
| Metric | Measurement |
|--------|-------------|
| **HiL latency** | Time from agent reaching a waiting/blocked state to human response (logged via observer + screen recording timestamp) |

### Secondary
| Metric | Measurement |
|--------|-------------|
| **Agent utilization rate** | % wall-clock time agents are actively computing vs. idle/waiting (derived from session logs) |
| **Manual context switch count** | Observer-logged count of user-initiated pane/tab/window changes |

### Subjective (post-condition questionnaires)
- **NASA-TLX** (6 subscales, 20-pt each): mental demand, temporal demand, effort, performance, frustration, physical demand
- **SUS** (10-item Likert): overall usability score (0–100)
- **Open-ended**: "What was most frustrating?" / "What would you change?"

---

## 5. Hypotheses

| ID | Hypothesis | Operationalization |
|----|------------|--------------------|
| **H1** | Helm reduces HiL latency by ≥ 30% | Notification + auto-surface brings agents to foreground without polling |
| **H2** | Helm increases agent utilization by ≥ 20% | LRU scheduler keeps all background agents running; reduces idle gaps |
| **H3** | Context handoff time ≤ 50% of baseline | Shared `AGENTS.md` eliminates manual copy-paste context transfer |

---

## 6. Analysis Plan

- **Primary comparison**: paired t-test (parametric) or Wilcoxon signed-rank test (non-parametric, if normality rejected via Shapiro-Wilk at α = 0.05)
- **Effect size**: Cohen's *d* for t-tests; rank-biserial correlation for Wilcoxon
- **Significance threshold**: α = 0.05; Bonferroni correction applied for multiple comparisons across H1–H3 (adjusted α = 0.017)
- **NASA-TLX / SUS**: paired Wilcoxon; report median and IQR
- **Qualitative**: thematic analysis of open-ended responses (two independent coders, Cohen's κ ≥ 0.70 required)

---

## 7. Procedure Timeline

| Time | Activity |
|------|----------|
| 0–5 min | Consent, demographics, screening confirmation |
| 5–10 min | Condition A orientation + practice pane |
| 10–55 min | Condition A: Tasks A, B, C (15 min each) |
| 55–65 min | Post-condition questionnaire (NASA-TLX + SUS) |
| 65–70 min | Condition B orientation + practice pane |
| 70–115 min | Condition B: Tasks A, B, C (15 min each) |
| 115–125 min | Post-condition questionnaire + debrief interview |

---

## 8. Ethics & Limitations

- IRB approval required before recruitment
- Screen recordings stored encrypted, deleted after analysis
- Limitation: lab setting may underestimate real-world HiL latency gains; ecological validity to be discussed
