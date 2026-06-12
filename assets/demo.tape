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

Type@15ms "python3 tools/brain-cockpit/cockpit.py"
Sleep 300ms
Enter
Sleep 4s

Sleep 1.5s
Type@110ms "codex 现在在干嘛？"
Sleep 800ms
Enter
Sleep 14s

Type@110ms "让 kaji-demo 那条船列一下自己目录里有什么"
Sleep 800ms
Enter
Sleep 16s
# the mate proposes send_to_worker → the arrow selector appears → 执行
Enter
Sleep 6s

Sleep 3s
Ctrl+C
Sleep 500ms
