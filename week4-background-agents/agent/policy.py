# policy.py — what the agent may do, and who has to agree.
#
# The model PROPOSES an action. This table, not the prompt, decides what
# happens to that proposal. Changing a word in the prompt can't change it.
POLICY = {
    "read_logs":        "read",       # just looking: always fine
    "read_changes":     "read",
    "disable_feature":  "write",      # changes checkout, easy to undo: allowed
    "rollback_release": "approval",   # changes checkout, risky: a person must say yes
    "ask_human":        "help",       # a question; the answer is information, not permission
    "wait":             "wait",       # nothing safe to do: sleep until the world changes
}
