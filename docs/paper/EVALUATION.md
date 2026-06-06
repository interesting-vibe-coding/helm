# Evaluation and Discussion

## 5. Evaluation

### 5.1 Study Design

We plan a controlled within-subjects study with experienced AI-agent users (n ≥ 16).
Participants complete a multi-agent programming task under two conditions:
(A) baseline — standard terminal multiplexer with no agent-aware scheduling;
(B) Helm — with Session Scheduler, LRU promotion, and shared AGENTS.md context.
Dependent variables: Human-in-the-Loop (HiL) latency, agent idle time, and context
handoff duration. Participants complete a brief exit survey covering cognitive load and
perceived workflow friction.

### 5.2 Expected Results

We anticipate three primary effects:

**HiL latency reduction (35–45%).** When an agent reaches a decision point requiring
human input, Helm surfaces the relevant pane automatically and fires a system
notification. We anticipate this eliminates the polling overhead users currently incur
by manually cycling through panes, reducing HiL latency by 35–45% relative to
baseline.

**Agent utilization improvement (25–35%).** The LRU scheduler keeps agents queued
and ready rather than sitting idle while the user context-switches. We anticipate
overall agent utilization — the fraction of wall-clock time agents spend on productive
work rather than waiting for human acknowledgment — improves by 25–35%.

**Context handoff time savings (60%).** Under baseline conditions, users switching
between agents must re-paste project context, coding conventions, and task framing
into each new session. Helm's shared `AGENTS.md`, automatically injected at session
start across all harnesses, eliminates this step. We anticipate context handoff time
drops by approximately 60%.

---

## 6. Limitations

**Platform dependency.** Helm is currently macOS-only. The scheduling layer
(`kaku.lua`) is tightly coupled to WezTerm's Lua plugin API, which has no equivalent
on Windows Terminal or the Linux VTE stack. Porting would require rewriting the
scheduling layer for each platform.

**Study population.** Our intended participants are developers who already use AI
coding agents regularly. The results may not generalize to programmers who have not
yet integrated agents into their daily workflow; adoption friction and trust calibration
differ substantially for novice users.

**Polling granularity.** The Lua event loop in `kaku.lua` polls agent status at 1-second
intervals. Sub-second state transitions — a brief tool call completing inside one
second — may be missed or reported with up to one second of lag, introducing noise
into fine-grained latency measurements.

---

## 7. Discussion: The Attention Routing Problem

A recurring framing in AI-assisted programming research positions agent *speed* as the
primary bottleneck. Faster inference, better code generation, fewer tool-call round
trips — these are the dominant optimization targets. Helm suggests a reframe.

**The bottleneck is human attention distribution, not agent speed.** In our
observations, agents frequently reach decision points and idle for 30–120 seconds
while the developer is focused elsewhere. The agent is not slow; the human's attention
is simply routed to a different pane. Speeding up the agent does nothing to close this
gap.

Helm is a proof-of-concept that terminal-level scheduling can address the attention
routing problem directly. By treating the terminal multiplexer as an attention
allocation layer — surfacing the highest-priority agent, suppressing low-signal noise,
and maintaining a queue of ready work — Helm shifts the cognitive bottleneck from
"where is my agent stuck?" to "what should I decide next?"

This framing opens several directions for future work. A **mobile companion app**
could route HiL notifications to the developer's phone, enabling asynchronous agent
oversight during meetings or away-from-desk time. **Voice notifications** could
announce completion events without requiring the developer to shift visual focus at
all. Most ambitiously, **ML-based scheduling** could learn each developer's attention
patterns — when they context-switch, how long they dwell per pane, which agents they
tend to defer — and proactively surface work at optimal moments, turning agent
orchestration from a manual discipline into an ambient, adaptive layer of the
development environment.
