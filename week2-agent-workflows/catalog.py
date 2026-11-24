"""Every workflow the UI can show: title, example input and diagram.

A diagram node lights up when the function in `fn` runs. Extra keys narrow the
match to one call: {"fn": "handle", "category": "billing"} only matches
handle("billing", ...), and {"fn": "Agent.run", "agent": "writer"} only matches
the agent named "writer". "chat" matches the LLM call itself.

Positions are grid units (x to the right, y down). Edges are
(from, to, decided_by, label); decided_by is "code" or "model".
"""

MODULES = [
    ("Non-agent workflows", ["prompt_chaining", "routing", "parallelization"]),
    ("Single-agent systems", ["react", "plan_and_execute", "reflection", "codeact"]),
    ("Multi-agent systems", ["sequential_agents", "parallel_agents", "supervisor",
                             "dispatcher", "evaluator_optimizer", "peer_to_peer"]),
]


def llm(id, label, x, y, fn=None, **match):
    return {"id": id, "label": label, "kind": "llm", "x": x, "y": y, "match": {"fn": fn or id, **match}}


def agent(name, label, x, y):
    return {"id": name, "label": label, "kind": "agent", "x": x, "y": y,
            "match": {"fn": "Agent.run", "agent": name}}


def tool(id, x, y, label=None):
    return {"id": id, "label": label or f"{id}()", "kind": "tool", "x": x, "y": y, "match": {"fn": id}}


def code(id, label, x, y):
    return {"id": id, "label": label, "kind": "code", "x": x, "y": y, "match": {"fn": id}}


def io(x_in, y_in, x_out, y_out):
    return [{"id": "input", "label": "Input", "kind": "io", "x": x_in, "y": y_in},
            {"id": "output", "label": "Output", "kind": "io", "x": x_out, "y": y_out}]


WORKFLOWS = {
    "prompt_chaining": {
        "title": "Prompt chaining",
        "decides": "code",
        "summary": "A fixed sequence of LLM calls. Each output feeds the next step.",
        "example": "Saffron: a note-taking app that turns voice memos into to-do lists, "
                   "works offline and syncs across devices.",
        "nodes": io(0, 1, 5.4, 1) + [
            llm("extract_features", "Extract features", 1.1, 1),
            llm("write_announcement", "Write announcement", 2.2, 1),
            code("is_short_enough", "Short enough?", 3.3, 1),
            llm("shorten", "Shorten", 3.3, 2.3),
            llm("translate", "Translate to Persian", 4.4, 1),
        ],
        "edges": [
            ("input", "extract_features", "code", ""),
            ("extract_features", "write_announcement", "code", ""),
            ("write_announcement", "is_short_enough", "code", ""),
            ("is_short_enough", "translate", "code", "yes"),
            ("is_short_enough", "shorten", "code", "no"),
            ("shorten", "translate", "code", ""),
            ("translate", "output", "code", ""),
        ],
    },
    "routing": {
        "title": "Routing",
        "decides": "model picks one path",
        "summary": "Classify the input once, then hand it to the right specialist.",
        "example": "I was charged twice for my subscription this month.",
        "nodes": io(0, 1.5, 4.2, 1.5) + [
            llm("classify", "Classify", 1.2, 1.5),
            llm("billing", "Billing specialist", 2.7, 0, fn="handle", category="billing"),
            llm("technical", "Technical specialist", 2.7, 1, fn="handle", category="technical"),
            llm("account", "Account specialist", 2.7, 2, fn="handle", category="account"),
            code("escalate_to_human", "Human (fallback)", 2.7, 3),
        ],
        "edges": [
            ("input", "classify", "code", ""),
            ("classify", "billing", "model", ""),
            ("classify", "technical", "model", ""),
            ("classify", "account", "model", ""),
            ("classify", "escalate_to_human", "model", "other"),
            ("billing", "output", "code", ""),
            ("technical", "output", "code", ""),
            ("account", "output", "code", ""),
            ("escalate_to_human", "output", "code", ""),
        ],
    },
    "parallelization": {
        "title": "Parallelization",
        "decides": "code",
        "summary": "Independent LLM calls at the same time, then one call merges them.",
        "example": 'def get_user(name):\n    rows = db.execute("SELECT * FROM users WHERE name = \'" + name + "\'")\n'
                   '    for r in rows:\n        if r.name == name: return r',
        "nodes": io(0, 1, 4.2, 1) + [
            llm("security", "Security review", 1.5, 0, fn="review", aspect="security"),
            llm("performance", "Performance review", 1.5, 1, fn="review", aspect="performance"),
            llm("readability", "Readability review", 1.5, 2, fn="review", aspect="readability"),
            llm("merge", "Merge", 3, 1),
        ],
        "edges": [
            ("input", "security", "code", ""),
            ("input", "performance", "code", ""),
            ("input", "readability", "code", ""),
            ("security", "merge", "code", ""),
            ("performance", "merge", "code", ""),
            ("readability", "merge", "code", ""),
            ("merge", "output", "code", ""),
        ],
    },
    "react": {
        "title": "ReAct",
        "decides": "model, every step",
        "summary": "Reason, act with a tool, observe the result. Repeat until done.",
        "example": "How old was the engineer behind the Eiffel Tower when it opened?",
        "nodes": io(0, 1, 3.4, 1) + [
            llm("chat", "LLM: reason", 1.7, 1),
            tool("search", 1.0, 2.4),
            tool("calculate", 2.4, 2.4),
        ],
        "edges": [
            ("input", "chat", "code", ""),
            ("chat", "search", "model", "act"),
            ("search", "chat", "code", "observe"),
            ("chat", "calculate", "model", "act"),
            ("calculate", "chat", "code", "observe"),
            ("chat", "output", "model", "answer"),
        ],
    },
    "plan_and_execute": {
        "title": "Plan and execute",
        "decides": "model plans once, code follows",
        "summary": "Write the whole plan first, then execute it step by step.",
        "example": "Compare Milad Tower and the Eiffel Tower: how much taller is one, "
                   "and how many years apart did they open?",
        "nodes": io(0, 1, 4.8, 1) + [
            llm("make_plan", "Planner", 1.2, 1),
            {"id": "execute", "label": "Executor (each step)", "kind": "code", "x": 2.5, "y": 1,
             "match": {"fn": "execute"}},
            llm("chat", "ReAct agent: LLM", 2.5, 2.2),
            tool("search", 1.8, 3.3),
            tool("calculate", 3.2, 3.3),
            llm("summarize", "Summarize", 3.8, 1),
        ],
        "edges": [
            ("input", "make_plan", "code", ""),
            ("make_plan", "execute", "model", "plan"),
            ("execute", "execute", "code", "next step"),
            ("execute", "chat", "code", ""),
            ("chat", "search", "model", ""),
            ("search", "chat", "code", ""),
            ("chat", "calculate", "model", ""),
            ("calculate", "chat", "code", ""),
            ("chat", "execute", "model", "result"),
            ("execute", "summarize", "code", ""),
            ("summarize", "output", "code", ""),
        ],
    },
    "reflection": {
        "title": "Reflection",
        "decides": "model decides when it's good",
        "summary": "The model critiques its own draft and revises it.",
        "example": "Explain what an AI agent is to a high-school student, in 3 sentences.",
        "nodes": io(0, 1, 3.8, 1) + [
            llm("draft", "Draft", 1.2, 1),
            llm("critique", "Critique (self)", 2.5, 1),
            llm("revise", "Revise", 2.5, 2.3),
        ],
        "edges": [
            ("input", "draft", "code", ""),
            ("draft", "critique", "code", ""),
            ("critique", "revise", "model", "problems"),
            ("revise", "critique", "code", "again"),
            ("critique", "output", "model", "LGTM"),
            ("revise", "output", "code", "max rounds"),
        ],
    },
    "codeact": {
        "title": "CodeAct",
        "decides": "model, with full code power",
        "summary": "The agent acts by writing Python. We run it and show it the output.",
        "example": "How many prime numbers are there below 10,000, and what is their sum?",
        "nodes": io(0, 1, 3.2, 1) + [
            llm("chat", "LLM: write code", 1.6, 1),
            tool("run_python", 1.6, 2.3, "run_python() sandbox"),
        ],
        "edges": [
            ("input", "chat", "code", ""),
            ("chat", "run_python", "model", "code"),
            ("run_python", "chat", "code", "output"),
            ("chat", "output", "model", "ANSWER"),
        ],
    },
    "sequential_agents": {
        "title": "Sequential agents",
        "decides": "code sets the order",
        "summary": "An assembly line: each agent does its job and passes the result on.",
        "example": "Milad Tower vs the Eiffel Tower",
        "nodes": io(0, 1, 4.6, 1) + [
            agent("researcher", "Researcher", 1.2, 1),
            agent("writer", "Writer", 2.4, 1),
            agent("editor", "Editor", 3.6, 1),
            tool("search", 1.2, 2.2),
        ],
        "edges": [
            ("input", "researcher", "code", ""),
            ("researcher", "search", "model", ""),
            ("search", "researcher", "code", ""),
            ("researcher", "writer", "code", "facts"),
            ("writer", "editor", "code", "draft"),
            ("editor", "output", "code", ""),
        ],
    },
    "parallel_agents": {
        "title": "Multi-agent parallelization",
        "decides": "code runs all agents",
        "summary": "Agents with different tools work at the same time; a planner combines them.",
        "example": "Plan a budget weekend in Isfahan for two people, leaving from Tehran.",
        "nodes": io(0, 1.5, 4.4, 1.5) + [
            agent("transport", "Transport agent", 1.6, 0),
            agent("hotels", "Hotels agent", 1.6, 1.5),
            agent("food", "Food agent", 1.6, 3),
            tool("search_flights", 2.6, 0.75),
            tool("search_hotels", 2.6, 2.25),
            tool("find_restaurants", 2.6, 3.75),
            llm("combine", "Combine plan", 3.4, 1.5),
        ],
        "edges": [
            ("input", "transport", "code", ""),
            ("input", "hotels", "code", ""),
            ("input", "food", "code", ""),
            ("transport", "search_flights", "model", ""),
            ("search_flights", "transport", "code", ""),
            ("hotels", "search_hotels", "model", ""),
            ("search_hotels", "hotels", "code", ""),
            ("food", "find_restaurants", "model", ""),
            ("find_restaurants", "food", "code", ""),
            ("transport", "combine", "code", ""),
            ("hotels", "combine", "code", ""),
            ("food", "combine", "code", ""),
            ("combine", "output", "code", ""),
        ],
    },
    "supervisor": {
        "title": "Supervisor",
        "decides": "supervisor model, after every result",
        "summary": "A manager agent delegates to workers, reads results, decides who's next.",
        "example": "How many times bigger is Istanbul than Tehran by population?",
        "nodes": io(0, 1.5, 1.6, 3.1) + [
            agent("supervisor", "Supervisor", 1.6, 1.5),
            agent("researcher", "Researcher", 3.3, 0.3),
            agent("analyst", "Analyst", 3.3, 1.5),
            agent("writer", "Writer", 3.3, 2.7),
            tool("search", 4.7, 0.3),
            tool("calculate", 4.7, 1.5),
        ],
        "edges": [
            ("input", "supervisor", "code", ""),
            ("supervisor", "researcher", "model", ""),
            ("researcher", "supervisor", "code", ""),
            ("supervisor", "analyst", "model", ""),
            ("analyst", "supervisor", "code", ""),
            ("supervisor", "writer", "model", ""),
            ("writer", "supervisor", "code", ""),
            ("researcher", "search", "model", ""),
            ("search", "researcher", "code", ""),
            ("analyst", "calculate", "model", ""),
            ("calculate", "analyst", "code", ""),
            ("supervisor", "output", "model", "done"),
        ],
    },
    "dispatcher": {
        "title": "Dispatcher",
        "decides": "model, once, up front",
        "summary": "Split the request into tasks and send each to a specialist. No review.",
        "example": "Customer 4521: we were charged twice in September, and our API has returned 403 since Oct 1.",
        "nodes": io(0, 1.5, 4.4, 1.5) + [
            llm("dispatch", "Dispatcher", 1.3, 1.5),
            agent("billing", "Billing agent", 2.9, 0.7),
            agent("technical", "Technical agent", 2.9, 2.3),
            tool("lookup_invoice", 2.2, -0.4),
            tool("issue_refund", 3.6, -0.4),
            tool("check_api_logs", 2.9, 3.4),
        ],
        "edges": [
            ("input", "dispatch", "code", ""),
            ("dispatch", "billing", "model", "task"),
            ("dispatch", "technical", "model", "task"),
            ("billing", "lookup_invoice", "model", ""),
            ("lookup_invoice", "billing", "code", ""),
            ("billing", "issue_refund", "model", ""),
            ("issue_refund", "billing", "code", ""),
            ("technical", "check_api_logs", "model", ""),
            ("check_api_logs", "technical", "code", ""),
            ("billing", "output", "code", ""),
            ("technical", "output", "code", ""),
        ],
    },
    "evaluator_optimizer": {
        "title": "Evaluator-optimizer",
        "decides": "evaluator's score",
        "summary": "A writer agent produces, a separate judge scores it, repeat until it passes.",
        "example": "A tagline for a family tea shop in Tehran that now sells online.",
        "nodes": io(0, 1, 4.2, 1) + [
            agent("writer", "Writer agent", 1.4, 1),
            llm("evaluate", "Evaluator (judge)", 2.9, 1),
        ],
        "edges": [
            ("input", "writer", "code", ""),
            ("writer", "evaluate", "code", ""),
            ("evaluate", "writer", "model", "score < 8"),
            ("evaluate", "output", "model", "pass"),
            ("writer", "output", "code", "max rounds"),
        ],
    },
    "peer_to_peer": {
        "title": "Peer-to-peer",
        "decides": "whichever agent holds the case",
        "summary": "No manager. Agents hand the case directly to each other.",
        "example": "I'm customer 4521. Our API stopped working right after our subscription renewed.",
        "nodes": io(0, 1.5, 4.5, 1.5) + [
            agent("triage", "Triage agent", 1.3, 1.5),
            agent("technical", "Technical agent", 3, 0.5),
            agent("billing", "Billing agent", 3, 2.5),
            tool("check_api_logs", 4.5, 0.5),
            tool("lookup_invoice", 4.5, 2.5),
        ],
        "edges": [
            ("input", "triage", "code", ""),
            ("triage", "technical", "model", "handoff"),
            ("triage", "billing", "model", "handoff"),
            ("technical", "billing", "model", "handoff"),
            ("billing", "technical", "model", "handoff"),
            ("technical", "check_api_logs", "model", ""),
            ("check_api_logs", "technical", "code", ""),
            ("billing", "lookup_invoice", "model", ""),
            ("lookup_invoice", "billing", "code", ""),
            ("technical", "output", "model", "answer"),
            ("billing", "output", "model", "answer"),
        ],
    },
}
