"""Replay mode: answers decide() without a model or a network.

The scripted choices are what a sensible model does with the same inputs:
look first, then fix what the logs point at, ask for approval for the
rollback, and ask or wait when the cause is outside our service. They only
read what the real model would see (the notes), plus which step is running,
so an older step never picks an action it doesn't support yet.
"""


def decide(goal, state, notes, step):
    logs = next((note for note in notes if note.startswith("read_logs")), "")

    if not logs:
        return choice("read_logs", "I need to see what is failing before I change anything.")

    if "express_checkout" in logs:
        return choice("disable_feature", "The logs show the express checkout feature crashing. "
                                         "Turning it off is safe and easy to undo.")

    if "deploy" in logs:
        if not any(note.startswith("read_changes") for note in notes):
            return choice("read_changes", "The errors started at a deploy. I need to see what changed.")
        return choice("rollback_release", "Release v2 went out at 14:02, exactly when payments started failing.")

    if "gateway" in logs:
        asked = any(note.startswith("ask_human") for note in notes)
        if step >= 6 and not asked:
            return choice("ask_human", "The payment gateway belongs to another team, so I can't fix it.",
                          "The payment gateway is timing out and it isn't ours. "
                          "Do the payments team know, and is there an ETA?")
        return choice("wait", "The gateway is run by another team and nothing I can change will fix it. "
                              "I'll wait until it recovers.")

    return choice("wait", "Nothing I can safely change. Waiting for the service to change.")


def choice(action, reason, question=""):
    return {"action": action, "reason": reason, "question": question}
