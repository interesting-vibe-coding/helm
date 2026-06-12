# vhs tape for assets/demo.gif — the conversational helm, live.
# Run from repo root: vhs assets/demo.tape
# Needs: Kaji running with a worker or two, OPENROUTER_API_KEY in env,
# and a sacrificial pane (kaji-brain spawn claude /tmp/kaji-demo) so the
# send in the script bothers nobody real.
Output assets/demo.gif

Set Shell bash
Set FontSize 15
Set Width 880
Set Height 560
Set Padding 16
Set Theme { "background": "#1a1612", "foreground": "#ece4d6", "cursor": "#f25c05" }

Type@15ms "KAJI_ENGINE_BACKEND=oauth python3 tools/brain-cockpit/cockpit.py"
Sleep 300ms
Enter
Sleep 4s

# let the first quota collection finish — it shares the proxy with the engine
Sleep 8s
Type@70ms "what is codex working on right now?"
Sleep 800ms
Enter
Sleep 12s

Type@70ms "tell the kaji-demo ship to list what's in its directory"
Sleep 800ms
Enter
Sleep 18s
# the mate proposes send_to_worker → the arrow selector appears → run
Enter
Sleep 12s
# end on the cockpit, conversation resolved — no quit in frame
