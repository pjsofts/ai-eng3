"""Every step the page can show: title, example input, diagram and data views.

A diagram node lights up when the function in `fn` runs. Two extra rules
pick between nodes for the same function:
    "in":     the function that called it directly   ({"fn": "add_elements", "in": "run_tool"})
    "within": a function anywhere above it           ({"fn": "find_overlaps", "within": "task"})

Positions are grid units (x to the right, y down). Edges are
(from, to, decided_by, label); decided_by is "code" or "model".

`views` maps a function name to how its result is drawn in the Data panel:
canvas, row (one eval case), results, scores or scored.
`baseline` is the experiment a step compares itself with.
"""

MODULES = [
    ("Build it", ["step0_first_agent"]),
    ("Measure it", ["step1_eval_harness", "step2_scorers"]),
    ("Improve it", ["step3_context", "step4_tools"]),
    ("Trust the eval?", ["step5_lying_eval", "step6_honest_eval", "step7_overlaps"]),
]

FLOW = "Draw a flow from User to API to Database"


def node(id, label, kind, x, y, fn=None, **match):
    return {"id": id, "label": label, "kind": kind, "x": x, "y": y, "match": {"fn": fn or id, **match}}


def code(id, label, x, y, **kw):
    return node(id, label, "code", x, y, **kw)


def agent(id, label, x, y, **kw):
    return node(id, label, "agent", x, y, **kw)


def llm(id, label, x, y, **kw):
    return node(id, label, "llm", x, y, fn="chat", **kw)


def tool(fn, x, y, id=None, **kw):
    return node(id or fn, f"{fn}()", "tool", x, y, fn=fn, **kw)


def io(x_in, y_in, x_out, y_out):
    return [{"id": "input", "label": "Input", "kind": "io", "x": x_in, "y": y_in},
            {"id": "output", "label": "Output", "kind": "io", "x": x_out, "y": y_out}]


def tool_row(llm_id, names, y, x0, gap=1.25):
    """A row of tools under an LLM node: the model asks, the code runs and answers."""
    nodes, edges = [], []
    for i, name in enumerate(names):
        nodes.append(tool(name, x0 + i * gap, y, **{"in": "run_tool"}))
        edges += [(llm_id, name, "model", "act" if i == 0 else ""), (name, llm_id, "code", "observe" if i == 0 else "")]
    return nodes, edges


BIG = ["generate_diagram", "modify_diagram"]
SMALL = ["query_canvas", "add_elements", "update_elements", "remove_elements"]


def eval_step(scorers, tools, last, last_label, extra_nodes=(), extra_edges=()):
    """The shape every eval step shares: the dataset, one case at a time,
    the agent inside task(), the scorers beside it, then a summary."""
    tool_nodes, tool_edges = tool_row("chat", tools, 3.75, -0.1 if len(tools) > 2 else 0.4)
    scorer_nodes = [code(name, f"{name}()", 3.85 + 1.15 * (i // 4), 0.95 + 0.62 * (i % 4))
                    for i, name in enumerate(scorers)]
    nodes = io(0, 0, 5.0, 0) + [
        code("load_dataset", "Load the dataset", 1.2, 0),
        code("run_eval", "run_eval()", 2.45, 0),
        code("run_case", "Run one case", 2.45, 1.3),
        agent("task", "task(): the agent", 1.0, 1.3),
        llm("chat", "LLM", 1.0, 2.55),
        code(last, last_label, 3.75, 0),
    ] + tool_nodes + scorer_nodes + list(extra_nodes)
    edges = [
        ("input", "load_dataset", "code", ""),
        ("load_dataset", "run_eval", "code", "cases"),
        ("run_eval", "run_case", "code", "each case"),
        ("run_case", "task", "code", "1. run"),
        ("task", "chat", "code", ""),
        ("task", "run_case", "code", "output"),
        ("run_eval", last, "code", "experiment"),
        (last, "output", "code", ""),
    ] + [("run_case", name, "code", "2. score" if i == 0 else "") for i, name in enumerate(scorers)] \
      + tool_edges + list(extra_edges)
    return nodes, edges


STEP2 = ["schema", "structure", "preservation", "label_keywords"]
STEP3 = STEP2 + ["bound_arrows", "connectivity"]
STEP4 = ["schema", "structure", "tool_choice", "label_keywords", "bound_arrows", "connectivity", "bound_labels"]
STEP7 = STEP4 + ["no_overlaps"]

S0_TOOLS, S0_EDGES = tool_row("chat", BIG, 2.35, 2.0)
S5_TOOLS, S5_EDGES = tool_row("chat", SMALL, 2.35, 0.75)

S2_NODES, S2_EDGES = eval_step(STEP2, BIG, "report", "Print the scores")
S3_NODES, S3_EDGES = eval_step(STEP3, BIG, "compare", "Compare: step 2")
S4_NODES, S4_EDGES = eval_step(STEP4, SMALL, "compare", "Compare: step 3")
S6_NODES, S6_EDGES = eval_step(STEP4, SMALL, "compare", "Compare: step 4")
S7_NODES, S7_EDGES = eval_step(
    STEP7, SMALL, "compare", "Compare: step 6",
    extra_nodes=[code("find_overlaps", "find_overlaps()", 1.15, 4.85, within="task")],
    extra_edges=[("add_elements", "find_overlaps", "code", "after every add"),
                 ("find_overlaps", "add_elements", "code", "")])

STEPS = {
    "step0_first_agent": {
        "title": "0 · The first diagram agent",
        "decides": "model, unmeasured",
        "summary": "The week 1 loop, one big tool (generate_diagram) and a short, friendly prompt. "
                   "It says \"Done!\". Then draw() shows what Excalidraw really puts on the canvas.",
        "example": FLOW,
        "hint": "Read the agent's answer, then look at the canvas in the Data panel.",
        "nodes": io(0, 1, 5.3, -0.3) + [
            agent("run_agent", "Agent loop", 1.25, 1),
            llm("chat", "LLM: think", 2.6, 1),
            code("draw", "Excalidraw draws it", 3.95, -0.3),
        ] + S0_TOOLS,
        "edges": [
            ("input", "run_agent", "code", ""),
            ("run_agent", "chat", "code", "messages"),
            ("run_agent", "draw", "code", "“Done!”"),
            ("draw", "output", "code", "what the user sees"),
        ] + S0_EDGES,
        "views": {"draw": "canvas"},
    },
    "step1_eval_harness": {
        "title": "1 · An eval harness, by hand",
        "decides": "a person, 1 to 5",
        "summary": "Run every case of the golden dataset, save what came back to a JSON file. "
                   "Then a person scores each one from 1 to 5. It works. It does not scale.",
        "example": "golden.json",
        "hint": "Look at each diagram in the table, and score it in your head. Do you agree with your neighbour?",
        "evals": True,
        "nodes": io(0, 0, 5.0, 0) + [
            code("load_dataset", "Load the dataset", 1.2, 0),
            code("run_case", "Run one case", 2.45, 0),
            agent("run_agent", "Agent loop", 2.45, 1.3),
            llm("chat", "LLM", 2.45, 2.55),
            code("save", "Save results/….json", 3.75, 0),
        ] + tool_row("chat", BIG, 3.75, 1.85)[0],
        "edges": [
            ("input", "load_dataset", "code", ""),
            ("load_dataset", "run_case", "code", "each case"),
            ("run_case", "run_agent", "code", ""),
            ("run_agent", "chat", "code", ""),
            ("run_case", "run_case", "code", "next case"),
            ("run_case", "save", "code", "all results"),
            ("save", "output", "code", "now score them"),
        ] + tool_row("chat", BIG, 3.75, 1.85)[1],
        "views": {"run_case": "row", "save": "results"},
    },
    "step2_scorers": {
        "title": "2 · Automated scorers",
        "decides": "code, every run",
        "summary": "A scorer is a small function: one case and its output in, a score from 0 to 1 out. "
                   "run_eval runs the dataset, scores every case and saves the experiment: the baseline.",
        "example": "golden.json",
        "hint": "Preservation: 0%. The modify cases redraw the whole diagram with new ids.",
        "evals": True,
        "nodes": S2_NODES, "edges": S2_EDGES,
        "views": {"run_case": "row", "run_eval": "scores"},
    },
    "step3_context": {
        "title": "3 · Context engineering",
        "decides": "what the model reads",
        "summary": "A real system prompt (rules, a layout grid, patterns, \"do NOT\" lines, an example) "
                   "and the canvas, summarized as text, in the prompt. Then compare with step 2.",
        "example": "golden.json",
        "baseline": "step2_baseline",
        "hint": "Watch the comparison at the end: which scorers moved, and by how much?",
        "evals": True,
        "nodes": S3_NODES, "edges": S3_EDGES,
        "views": {"run_case": "row", "run_eval": "scores"},
    },
    "step4_tools": {
        "title": "4 · Small tools",
        "decides": "four small tools",
        "summary": "generate_diagram becomes query_canvas, add_elements, update_elements and remove_elements. "
                   "The schema descriptions teach containerId and startBinding. tool_choice: look before you change.",
        "example": "golden.json",
        "baseline": "step3_context",
        "hint": "bound_labels and bound_arrows look great. Remember them for step 5.",
        "evals": True,
        "nodes": S4_NODES, "edges": S4_EDGES,
        "views": {"run_case": "row", "run_eval": "scores"},
    },
    "step5_lying_eval": {
        "title": "5 · Is the eval lying?",
        "decides": "what the user sees",
        "summary": "Run step 4's agent once. Score the elements it sent (what the eval scored), "
                   "then the elements Excalidraw draws from them (what the user sees).",
        "example": FLOW,
        "hint": "Two canvases, two sets of scores, one run. Which one is the product?",
        "nodes": io(0, 1, 5.3, -0.3) + [
            agent("run_agent", "Agent loop", 1.25, 1),
            llm("chat", "LLM: think", 2.6, 1),
            code("draw", "Excalidraw draws it", 2.6, -0.3),
            code("score", "Score it", 3.95, -0.3),
        ] + S5_TOOLS,
        "edges": [
            ("input", "run_agent", "code", ""),
            ("run_agent", "chat", "code", ""),
            ("run_agent", "draw", "code", "what it sent"),
            ("draw", "score", "code", "both canvases"),
            ("score", "output", "code", ""),
        ] + S5_EDGES,
        "views": {"score": "scored"},
    },
    "step6_honest_eval": {
        "title": "6 · Make the eval honest",
        "decides": "the same draw() as the app",
        "summary": "The schema now uses the names Excalidraw reads (label, start, end), and the eval's "
                   "add_elements runs draw() like the app. The scorers read what the user sees.",
        "example": "golden.json",
        "baseline": "step4_tools",
        "hint": "The same numbers as step 4. Look at the canvases: now they are true. Why is bound_labels not 100%?",
        "evals": True,
        "nodes": S6_NODES, "edges": S6_EDGES,
        "views": {"run_case": "row", "run_eval": "scores"},
    },
    "step7_overlaps": {
        "title": "7 · Overlaps, and an honest dataset",
        "decides": "one check, two uses",
        "summary": "find_overlaps() feeds the agent (in every add_elements result) and the eval (no_overlaps). "
                   "golden_2.json fixes the modify seeds and adds layout stress cases.",
        "example": "golden_2.json",
        "baseline": "step6_honest",
        "hint": "create-long-labels: add_elements, then update_elements. Open its conversation in the Trace.",
        "evals": True,
        "nodes": S7_NODES, "edges": S7_EDGES,
        "views": {"run_case": "row", "run_eval": "scores"},
    },
}
