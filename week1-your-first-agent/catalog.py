"""Every step the page can show: title, example input, diagram and data views.

A diagram node lights up when the function in `fn` runs. The model calls in
llm.py light up the nodes named after them: ask, ask_json, chat, search_web.

Positions are grid units (x to the right, y down). Edges are
(from, to, decided_by, label); decided_by is "code" or "model".

`views` maps a function name to how its return value is drawn in the Data
panel: eval (a row of the eval table), tokens (a gauge), summary (compaction).
The conversation sent to the model is drawn on every chat call anyway.
"""

MODULES = [
    ("The basics", ["step1_just_an_llm", "step2_one_tool_call", "step3_single_turn_evals"]),
    ("The agent", ["step4_agent_loop", "step5_multi_turn_evals"]),
    ("Real tools", ["step6_file_tools", "step7_web_search", "step8_context", "step9_shell_and_code"]),
    ("Safety", ["step10_human_approval"]),
]


def node(id, label, kind, x, y, fn=None):
    return {"id": id, "label": label, "kind": kind, "x": x, "y": y, "match": {"fn": fn or id}}


def llm(id, label, x, y, fn=None):
    return node(id, label, "llm", x, y, fn)


def tool(id, x, y):
    return node(id, f"{id}()", "tool", x, y)


def code(id, label, x, y, fn=None):
    return node(id, label, "code", x, y, fn)


def io(x_in, y_in, x_out, y_out):
    return [{"id": "input", "label": "Input", "kind": "io", "x": x_in, "y": y_in},
            {"id": "output", "label": "Output", "kind": "io", "x": x_out, "y": y_out}]


def loop_with_tools(tools, y=2.4, x0=0.9, gap=1.25):
    """The agent loop: run_agent calls the model; the model asks for tools."""
    nodes = [node("run_agent", "Agent loop", "agent", 1.2, 1), llm("chat", "LLM: think", 2.6, 1)]
    edges = [("input", "run_agent", "code", ""), ("run_agent", "chat", "code", "messages"),
             ("run_agent", "output", "code", "answer")]
    for i, name in enumerate(tools):
        nodes.append(tool(name, x0 + i * gap, y))
        edges += [("chat", name, "model", "act" if i == 0 else ""), (name, "chat", "code", "observe" if i == 0 else "")]
    return nodes, edges


FILE_NODES, FILE_EDGES = loop_with_tools(["list_files", "read_file", "write_file", "delete_file"], x0=0.7)
WEB_NODES, WEB_EDGES = loop_with_tools(["web_search", "get_current_time"], x0=1.9)
SHELL_NODES, SHELL_EDGES = loop_with_tools(["list_files", "read_file", "run_command", "execute_code"], x0=0.7)

STEPS = {
    "step1_just_an_llm": {
        "title": "1 · Just an LLM",
        "decides": "nothing: one answer",
        "summary": "One question in, one answer out. No tools, no loop, no memory. "
                   "Ask something it can only know by looking, and it can't.",
        "example": "What time is it right now, and what files are in my folder?",
        "hint": "It has no clock and no hands. Steps 2 and 6 fix that.",
        "nodes": io(0, 1, 2.6, 1) + [llm("ask", "LLM: answer", 1.3, 1)],
        "edges": [("input", "ask", "code", "prompt"), ("ask", "output", "code", "text")],
    },
    "step2_one_tool_call": {
        "title": "2 · One tool call",
        "decides": "model asks, code runs",
        "summary": "The model can't run a tool. It replies with a request: \"please call get_current_time\". "
                   "We run it, add the result, and ask again.",
        "example": "What time is it right now?",
        "hint": "Try: What is the capital of France? (no tool needed, so one LLM call)",
        "nodes": io(0, 1, 2.8, 1) + [llm("chat", "LLM", 1.4, 1), tool("get_current_time", 1.4, 2.4)],
        "edges": [
            ("input", "chat", "code", ""),
            ("chat", "get_current_time", "model", "asks for it"),
            ("get_current_time", "chat", "code", "we run it"),
            ("chat", "output", "model", "answer"),
        ],
    },
    "step3_single_turn_evals": {
        "title": "3 · Single-turn evals",
        "decides": "a score, not a feeling",
        "summary": "For each test prompt: one LLM call, no tools run. Did it pick the right tool? "
                   "Golden, secondary and negative cases, each with its scorer.",
        "example": "Remove the old todo.txt -> delete_file",
        "hint": "The input adds one case: prompt -> tool. Try: Save my notes to notes.txt -> write_file",
        "nodes": io(0, 1, 4.1, 1) + [
            code("score_case", "Score one case", 1.35, 1),
            llm("chat", "LLM: pick a tool", 2.7, 1),
            code("tools_selected", "tools_selected", 1.6, 2.4),
            code("selection_score", "selection_score", 2.85, 2.4),
            code("tools_avoided", "tools_avoided", 4.1, 2.4),
        ],
        "edges": [
            ("input", "score_case", "code", "each case"),
            ("score_case", "chat", "code", "prompt"),
            ("chat", "tools_selected", "code", "golden"),
            ("chat", "selection_score", "code", "secondary"),
            ("chat", "tools_avoided", "code", "negative"),
            ("score_case", "output", "code", "report"),
        ],
        "views": {"score_case": "eval"},
    },
    "step4_agent_loop": {
        "title": "4 · The agent loop",
        "decides": "model, every step",
        "summary": "Ask, run the tools it asked for, add the results, ask again. "
                   "The model ends the loop by asking for no tools.",
        "example": "List the files in the workspace, then read the todo list and tell me what is most urgent.",
        "hint": "Watch the LLM node count go up: one call per step of the loop",
        "nodes": io(0, 1, 4.2, 1) + [
            llm("chat", "LLM: think", 2.1, 1),
            tool("get_current_time", 0.85, 2.4),
            tool("list_files", 2.1, 2.4),
            tool("read_file", 3.35, 2.4),
        ],
        "edges": [
            ("input", "chat", "code", ""),
            ("chat", "get_current_time", "model", ""),
            ("get_current_time", "chat", "code", ""),
            ("chat", "list_files", "model", "act"),
            ("list_files", "chat", "code", "observe"),
            ("chat", "read_file", "model", ""),
            ("read_file", "chat", "code", ""),
            ("chat", "output", "model", "no tools: answer"),
        ],
    },
    "step5_multi_turn_evals": {
        "title": "5 · Multi-turn evals",
        "decides": "judge the whole run",
        "summary": "Run the full agent on mocked tools, then score the run: tools in the right order, "
                   "no forbidden tools, and an LLM judge for the final answer.",
        "example": "all",
        "hint": "Try one case: fresh task · mid-conversation · no tools",
        "nodes": io(0, 1, 5.2, 1) + [
            code("run_case", "Run one case", 1.25, 1),
            node("run_agent", "Agent loop", "agent", 2.5, 1),
            llm("chat", "LLM: think", 2.5, 2.4),
            node("mock_tool", "mock tool", "tool", 1.25, 2.4, fn="mocked.<locals>.mock_tool"),
            code("tool_order_correct", "Order right?", 3.9, 0),
            code("tools_avoided", "Avoided bad tools?", 3.9, 1),
            llm("llm_judge", "LLM judge", 3.9, 2.1),
        ],
        "edges": [
            ("input", "run_case", "code", "each case"),
            ("run_case", "run_agent", "code", ""),
            ("run_agent", "chat", "code", ""),
            ("chat", "mock_tool", "model", "act"),
            ("mock_tool", "chat", "code", "fixed result"),
            ("run_agent", "tool_order_correct", "code", "score"),
            ("tool_order_correct", "tools_avoided", "code", ""),
            ("tools_avoided", "llm_judge", "code", ""),
            ("run_case", "output", "code", "report"),
        ],
        "views": {"run_case": "eval"},
    },
    "step6_file_tools": {
        "title": "6 · File system tools",
        "decides": "errors are data",
        "summary": "Read, write, list, delete: all inside the workspace folder. "
                   "A failed tool returns the error as text, and the model recovers.",
        "example": "Change the port in config.json to 3000, then add 'deploy on Friday' to todo.txt.",
        "hint": "Try: read secrets.txt (doesn't exist) · read ../tools.py (outside the workspace)",
        "nodes": io(0, 1, 4.2, 1) + FILE_NODES,
        "edges": FILE_EDGES,
    },
    "step7_web_search": {
        "title": "7 · Web search",
        "decides": "search only when needed",
        "summary": "The model's knowledge stops at its training date. web_search is one more tool, "
                   "and its docstring says when NOT to use it.",
        "example": "What is the weather in Tehran today?",
        "hint": "Try: What is the capital of France? (it should answer without searching)",
        "nodes": io(0, 1, 4.2, 1) + WEB_NODES + [llm("search_web", "Search model", 1.9, 3.6)],
        "edges": WEB_EDGES + [("web_search", "search_web", "code", "query")],
    },
    "step8_context": {
        "title": "8 · Context management",
        "decides": "summarize at 80%",
        "summary": "Every call sends the whole conversation. Before the turn, estimate the tokens; "
                   "over 80% of the window, replace the history with a summary.",
        "example": "Remind me: which database did we choose, and which port does the app use?",
        "hint": "The conversation is ~1,080 tokens; the window here is only 1,000. Watch the Data panel.",
        "nodes": io(0, 1, 5.4, 1) + [
            code("estimate_tokens", "Count tokens", 1.25, 1),
            code("compact", "Compact", 2.6, 2.3),
            llm("ask", "LLM: summarize", 1.25, 2.3),
            node("run_agent", "Agent loop", "agent", 4.0, 1),
            llm("chat", "LLM: think", 4.0, 2.3),
            tool("read_file", 5.3, 2.3),
        ],
        "edges": [
            ("input", "estimate_tokens", "code", ""),
            ("estimate_tokens", "compact", "code", "over 80%"),
            ("estimate_tokens", "run_agent", "code", "fits"),
            ("compact", "ask", "code", "old messages"),
            ("compact", "run_agent", "code", "2 messages"),
            ("run_agent", "chat", "code", ""),
            ("chat", "read_file", "model", ""),
            ("read_file", "chat", "code", ""),
            ("run_agent", "output", "code", "answer"),
        ],
        "views": {"estimate_tokens": "tokens", "compact": "summary"},
    },
    "step9_shell_and_code": {
        "title": "9 · Shell and code",
        "decides": "code does the maths",
        "summary": "run_command runs one shell command; execute_code writes a program, runs it and cleans up. "
                   "Both run on this machine, with your permissions.",
        "example": "Which Python version is installed? And what is the total of the amount column in data/sales.csv?",
        "hint": "Try: How many lines does each file in notes/ have?",
        "nodes": io(0, 1, 4.2, 1) + SHELL_NODES,
        "edges": SHELL_EDGES,
    },
    "step10_human_approval": {
        "title": "10 · A human approves",
        "decides": "you say yes or no",
        "summary": "Reading is safe. Before write, delete, shell or code, the loop stops and asks you. "
                   "A \"no\" goes back to the model as a tool result.",
        "example": "Delete todo.txt, then tell me which files are left.",
        "hint": "Answer No first: the model is told, and reports it. Then run again and say Yes.",
        "nodes": io(0, 1, 4.6, 1) + [
            llm("chat", "LLM: think", 1.5, 1),
            tool("list_files", 0.3, 2.4),
            tool("read_file", 1.5, 2.4),
            node("approved", "You: allow?", "human", 3.1, 2.0),
            tool("write_file", 2.1, 3.5),
            tool("delete_file", 3.3, 3.5),
            tool("run_command", 4.5, 3.5),
        ],
        "edges": [
            ("input", "chat", "code", ""),
            ("chat", "list_files", "model", "safe"),
            ("list_files", "chat", "code", ""),
            ("chat", "read_file", "model", ""),
            ("read_file", "chat", "code", ""),
            ("chat", "approved", "model", "risky"),
            ("approved", "write_file", "code", ""),
            ("approved", "delete_file", "code", "yes"),
            ("approved", "run_command", "code", ""),
            ("approved", "chat", "code", "no"),
            ("write_file", "chat", "code", ""),
            ("delete_file", "chat", "code", ""),
            ("run_command", "chat", "code", ""),
            ("chat", "output", "model", "answer"),
        ],
    },
}
