import re
from pathlib import Path

msg_file = Path(__import__("sys").argv[1])
msg = msg_file.read_text().strip()

if not re.match(r"^(feat|fix|docs|refactor|chore):", msg, re.I):
    lower = msg.lower()

    if lower.startswith(("add ", "create ", "implement ")):
        msg = "feat: " + re.sub(r"^(add|create|implement)\s+", "", msg, flags=re.I)
    elif lower.startswith(("fix ", "repair ")):
        msg = "fix: " + re.sub(r"^(fix|repair)\s+", "", msg, flags=re.I)
    else:
        msg = "chore: " + msg

msg_file.write_text(msg + "\n")
