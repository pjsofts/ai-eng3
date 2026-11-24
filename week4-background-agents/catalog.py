"""Every step the page can show: title, example input, diagram, world buttons.

A diagram node lights up when its match happens:
  {"fn": "goal_met"}   that function is called
  {"step": "observe"}  a step whose id starts with "observe-" runs (or is replayed)

Positions are grid units (x to the right, y down). Edges are
(from, to, decided_by, label); decided_by is "code" or "model".

`world` lists the buttons in the World panel for that step:
kill, fix_gateway, fix_quietly, deploy.
"""

MODULES = [
    ("Make it work", ["step1_goal_loop"]),
    ("Make it durable", ["step2_durable_steps", "step3_wait_for_event"]),
    ("Make it safe", ["step4_human_approval", "step5_safe_retries", "step6_ask_for_help"]),
]

# The input box is the scenario: which way checkout is broken.
FAULTS = ["feature", "release", "dependency"]


def node(id, label, kind, x, y, tag=None, **match):
    return {"id": id, "label": label, "kind": kind, "x": x, "y": y, "tag": tag, "match": match or {"step": id}}


def io(x_out):
    return [{"id": "input", "label": "Alert", "kind": "io", "x": 0, "y": 1, "tag": "checkout/alert", "match": {}},
            {"id": "output", "label": "Result", "kind": "io", "x": x_out, "y": 1, "tag": None, "match": {}}]


# ---- the pieces of the durable loop (steps 2 to 6) ----------------------------
OBSERVE = node("observe", "Look at checkout", "step", 1.4, 1, "step.run · observe-N")
GOAL = node("goal_met", "Goal met?", "code", 2.8, 1, "code", fn="goal_met")
DECIDE = node("decide", "LLM: pick one action", "llm", 2.8, 2.4, "step.run · decide-N")
ACT = node("act", "Run the tool", "tool", 1.4, 2.4, "step.run · act-N")
SETTLE = node("settle", "Sleep 10 s", "sleep", 0, 2.4, "step.sleep · settle-N")
WAIT = node("wait", "Wait: recovered", "wait", 4.4, 2.4, "step.wait_for_event")
ASK = node("ask", "Ask a person", "human", 3.9, 3.8, "step.run · ask-N")
ANSWER = node("answer", "Wait: answered", "wait", 2.6, 3.8, "step.wait_for_event")
RECHECK = node("recheck", "Look again", "step", 1.3, 3.8, "step.run · recheck-N")

LOOP = [
    ("input", "observe", "code", ""),
    ("observe", "goal_met", "code", ""),
    ("goal_met", "output", "code", "yes"),
    ("goal_met", "decide", "code", "no"),
    ("decide", "act", "model", "read / write"),
    ("act", "observe", "code", "next cycle"),
    ("act", "settle", "code", "after a change"),
    ("settle", "observe", "code", ""),
    ("decide", "output", "model", "can't do it"),
]
WAITING = [
    ("decide", "wait", "model", "wait"),
    ("wait", "observe", "code", "event or timeout"),
]
APPROVAL = [
    ("decide", "ask", "model", "needs a person"),
    ("ask", "answer", "code", ""),
    ("answer", "recheck", "code", "yes"),
    ("answer", "output", "code", "no / silence"),
    ("recheck", "act", "code", "same version"),
    ("recheck", "observe", "code", "changed"),
]

STEPS = {
    "step1_goal_loop": {
        "title": "1 · A goal and a loop",
        "decides": "code checks the goal",
        "summary": "Look at checkout, let the model pick ONE action, run it, look again. "
                   "The code decides when the goal is met, not the model.",
        "example": "feature",
        "hint": "Try: release (needs a person, so it stops) · dependency · press K mid-run: it starts over",
        "nodes": io(4.4) + [
            node("read_state", "Look at checkout", "code", 1.4, 1, "code", fn="read_state"),
            node("goal_met", "Goal met?", "code", 2.8, 1, "code", fn="goal_met"),
            node("decide", "LLM: pick one action", "llm", 2.8, 2.4, "LLM", fn="decide"),
            node("run_tool", "Run the tool", "tool", 1.4, 2.4, "tool", fn="run_tool"),
        ],
        "edges": [
            ("input", "read_state", "code", ""),
            ("read_state", "goal_met", "code", ""),
            ("goal_met", "output", "code", "yes"),
            ("goal_met", "decide", "code", "no"),
            ("decide", "run_tool", "model", "action"),
            ("run_tool", "read_state", "code", "next cycle"),
            ("decide", "output", "model", "can't do it"),
        ],
        "world": ["kill"],
    },
    "step2_durable_steps": {
        "title": "2 · Durable steps",
        "decides": "every step is saved",
        "summary": "Each piece of work is a named step. Kill the process: Inngest runs the function "
                   "again from the top, and finished steps return their saved result.",
        "example": "feature",
        "hint": "Press K (💥) while it sleeps · Try: feature lose-reply (the change runs twice, see step 5)",
        "nodes": io(4.4) + [OBSERVE, GOAL, DECIDE, ACT, SETTLE],
        "edges": LOOP,
        "world": ["kill"],
    },
    "step3_wait_for_event": {
        "title": "3 · Wait for the world",
        "decides": "an event wakes it up",
        "summary": "The gateway belongs to another team, so the agent waits for checkout/recovered "
                   "without holding a process. Then it looks again: the event is a doorbell, not the truth.",
        "example": "dependency",
        "hint": "While it waits: 🔧 fix the gateway (sends the event) or 🤫 fix it quietly (no event: the timeout catches it)",
        "nodes": io(4.4) + [OBSERVE, GOAL, DECIDE, ACT, SETTLE, WAIT],
        "edges": LOOP + WAITING,
        "world": ["kill", "fix_gateway", "fix_quietly"],
    },
    "step4_human_approval": {
        "title": "4 · A person approves",
        "decides": "a person says yes",
        "summary": "A rollback needs a yes. The agent writes to the inbox and sleeps until the answer "
                   "event. If checkout changed while it waited, the yes no longer counts.",
        "example": "release",
        "hint": "Approve, deny or ignore it · press 🚀 before you approve: the yes goes stale",
        "nodes": io(4.4) + [OBSERVE, GOAL, DECIDE, ACT, SETTLE, WAIT, ASK, ANSWER, RECHECK],
        "edges": LOOP + WAITING + APPROVAL,
        "world": ["kill", "deploy"],
    },
    "step5_safe_retries": {
        "title": "5 · Safe retries",
        "decides": "same intent, same id",
        "summary": "Checkout makes the change, then the reply is lost and Inngest retries the step. "
                   "The same action_id lets checkout answer \"already done\" instead of doing it twice.",
        "example": "feature lose-reply",
        "hint": "Compare: the same input on step 2 changes checkout twice · Try: release lose-reply",
        "nodes": io(4.4) + [OBSERVE, GOAL, DECIDE, ACT, SETTLE, WAIT, ASK, ANSWER, RECHECK],
        "edges": LOOP + WAITING + APPROVAL,
        "world": ["kill", "deploy"],
    },
    "step6_ask_for_help": {
        "title": "6 · Ask for help",
        "decides": "an answer is not permission",
        "summary": "When the cause is outside our service the agent asks a person. The answer is "
                   "information: nothing runs because of it. The agent looks again and decides again.",
        "example": "dependency",
        "hint": "Answer the question: it looks again and is still broken · then 🔧 fix the gateway",
        "nodes": io(4.4) + [OBSERVE, GOAL, DECIDE, ACT, SETTLE, WAIT, ASK, ANSWER, RECHECK],
        "edges": LOOP + WAITING + APPROVAL + [("answer", "observe", "code", "info, not a yes")],
        "world": ["kill", "fix_gateway", "fix_quietly", "deploy"],
    },
}
